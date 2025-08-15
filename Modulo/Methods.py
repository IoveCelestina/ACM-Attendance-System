import time
from Modulo import Constant


# 集训队管理办法 - 基类
class MethodBase:
    def __init__(self, basic_info: list, count_in_list: list):
        """
        集训队管理办法
        :param basic_info: 人员基本信息, 包括工号等, 由 Modulo.Constant 定义其字段含义
        :param count_in_list: 人员打卡记录, [(开始时间, 结束时间), ...], 中间的每对表示成对的签到签退时间, 一天可以多次签到签退, 时间为 Unix 时间
        """
        self.id = basic_info[Constant.COL_ID]
        self._info = basic_info
        self._data = count_in_list
        self.__seconds = None
        self.__flex_count = None
        self.__regular_count = None
        self.__violation_count = None

    # 必须实现的接口: 计算打卡时长
    def _calc_seconds(self) -> str:
        raise NotImplementedError("function must be implemented.")

    # 必须实现的接口: 计算灵活次数
    def _calc_flex_count(self) -> int:
        raise NotImplementedError("function must be implemented.")

    # 必须实现的接口: 计算固定次数
    def _calc_regular_count(self) -> int:
        raise NotImplementedError("function must be implemented.")

    # 必须实现的接口: 计算违规次数
    def _calc_violation_count(self) -> int:
        raise NotImplementedError("function must be implemented.")

    # 带有记忆化的对外接口簇
    def seconds(self) -> str:
        if self.__seconds is None:
            self.__seconds = self._calc_seconds()
        return self.__seconds

    def flex_count(self) -> int:
        if self.__flex_count is None:
            self.__flex_count = self._calc_flex_count()
        return self.__flex_count

    def regular_count(self) -> int:
        if self.__regular_count is None:
            self.__regular_count = self._calc_regular_count()
        return self.__regular_count

    def violation_count(self) -> int:
        if self.__violation_count is None:
            self.__violation_count = self._calc_violation_count()
        return self.__violation_count


# 集训队日常管理办法
class MethodRegular(MethodBase):
    FLEX_STANDARD = {  # 灵活时长标准
        "正式队员": 14,
        "参赛队员": 16,
    }
    FLEX_STANDARD_DEFAULT = 14  # 默认灵活时长标准, 如果成员类型不属于上表

    REGULAR_WDAY = 5  # 固定打卡为周六
    REGULAR_START = 12 * 3600  # 固定打卡开始时间, 表达为一天中的第几秒
    REGULAR_END = 17 * 3600  # 固定打卡结束时间, 表达为一天中的第几秒

    def _calc_seconds(self) -> str:
        # 累计时间: 具体为统计所有签到签退区间, 格式化为 HH:MM
        _seconds = 0.0
        for _st, _ed in self._data:
            _seconds += _ed - _st
        # 开头没有 ' 概率触发 xlwings 的又一个 BUG
        return "'{:02d}:{:02d}".format(int(_seconds) // 3600, int(_seconds) % 3600 // 60)

    def _calc_flex_count(self) -> int:
        # 灵活次数: 累计小时数
        _seconds = 0.0
        for _st, _ed in self._data:
            _seconds += _ed - _st
        # 超过 50 min 向上取整
        return (int(_seconds) + 600) // 3600

    def _calc_regular_count(self) -> int:
        # for _st, _ed in self._data:
        #     _mk_st, _mk_ed = time.localtime(_st), time.localtime(_ed)
        #     _wday = _mk_st.tm_wday
        #     _dsec_st = _mk_st.tm_hour * 3600 + _mk_st.tm_min * 60 + _mk_st.tm_sec
        #     _dsec_ed = _mk_ed.tm_hour * 3600 + _mk_ed.tm_min * 60 + _mk_ed.tm_sec
        #     if _wday == self.REGULAR_WDAY and _dsec_st <= self.REGULAR_START and _dsec_ed <= self.REGULAR_END:
        #         return 1
        # return 0

        # 放宽条件, 允许迟到早退但求和不得超过 10 min, 具体实现为在固定时间内的打卡时长不少于(固定时长 - 10 min)
        _seconds = 0.0
        for _st, _ed in self._data:
            _mk_st, _mk_ed = time.localtime(_st), time.localtime(_ed)
            _wday = _mk_st.tm_wday
            _dsec_st = _mk_st.tm_hour * 3600 + _mk_st.tm_min * 60 + _mk_st.tm_sec
            _dsec_ed = _mk_ed.tm_hour * 3600 + _mk_ed.tm_min * 60 + _mk_ed.tm_sec
            if _wday == self.REGULAR_WDAY:
                _seconds += max(min(_dsec_ed, self.REGULAR_END) - max(_dsec_st, self.REGULAR_START), 0)
        return int(_seconds + 600 >= self.REGULAR_END - self.REGULAR_START)

    def _calc_violation_count(self) -> int:
        _cnt = 0
        if self.flex_count() < self.FLEX_STANDARD.get(
                self._info[Constant.COL_TYPE].strip(),
                self.FLEX_STANDARD_DEFAULT
        ):
            _cnt += 1
        if self.regular_count() == 0:
            _cnt += 1
        return _cnt


# 集训队假期管理办法
class MethodVacation(MethodBase):
    TRAIN_DAYS = []
    TRAIN_START = 0
    TRAIN_END = 0

    def _calc_seconds(self) -> str:
        # 累计时间: 具体为统计所有签到签退区间, 格式化为 HH:MM
        _seconds = 0.0
        for _st, _ed in self._data:
            _seconds += _ed - _st
        # 开头没有 ' 概率触发 xlwings 的又一个 BUG
        return "'{:02d}:{:02d}".format(int(_seconds) // 3600, int(_seconds) % 3600 // 60)

    def _calc_flex_count(self) -> int:
        return 0

    def _calc_regular_count(self) -> int:
        _cnt = 0
        _days_seconds = dict(zip(self.TRAIN_DAYS, [0] * len(self.TRAIN_DAYS)))  # 存储每天对应打卡时间
        for _st, _ed in self._data:
            _mk_st, _mk_ed = time.localtime(_st), time.localtime(_ed)
            _dsec_st = _mk_st.tm_hour * 3600 + _mk_st.tm_min * 60 + _mk_st.tm_sec
            _dsec_ed = _mk_ed.tm_hour * 3600 + _mk_ed.tm_min * 60 + _mk_ed.tm_sec
            _sec_day = _st - _dsec_st
            if _sec_day in self.TRAIN_DAYS:
                _days_seconds[_sec_day] += max(min(_dsec_ed, self.TRAIN_END) - max(_dsec_st, self.TRAIN_START), 0)
        # 放宽条件, 允许迟到早退但求和不得超过 10 min, 具体实现为在固定时间内的打卡时长不少于(固定时长 - 10 min)
        for _train_day in _days_seconds:
            _cnt += int(_days_seconds[_train_day] + 600 >= self.TRAIN_END - self.TRAIN_START)
        return _cnt

    def _calc_violation_count(self) -> int:
        return int(self.regular_count() < len(self.TRAIN_DAYS))


# 集训队假期管理办法241001 10-01~10-04 9:00~17:00
class MethodVacation241001(MethodVacation):
    TRAIN_DAYS = [
        time.mktime((2024, 10, 1, 0, 0, 0, 0, 0, 0)),
        time.mktime((2024, 10, 2, 0, 0, 0, 0, 0, 0)),
        time.mktime((2024, 10, 3, 0, 0, 0, 0, 0, 0)),
        time.mktime((2024, 10, 4, 0, 0, 0, 0, 0, 0)),
    ]
    TRAIN_START = 9 * 3600
    TRAIN_END = 17 * 3600


class MethodVacation20240430(MethodRegular):
    FLEX_STANDARD = {  # 灵活时长标准
        "正式队员": 20,
        "参赛队员": 22,
    }
    FLEX_STANDARD_DEFAULT = 20  # 默认灵活时长标准, 如果成员类型不属于上表


class MethodVacation20240501(MethodVacation):
    TRAIN_DAYS = [
        time.mktime((2024, 5, 2, 0, 0, 0, 0, 0, 0)),
        time.mktime((2024, 5, 3, 0, 0, 0, 0, 0, 0)),
        time.mktime((2024, 5, 4, 0, 0, 0, 0, 0, 0)),
    ]
    TRAIN_START = 9 * 3600
    TRAIN_END = 17 * 3600


class MethodVacation20240506(MethodRegular):
    def _calc_violation_count(self) -> int:
        _cnt = 0
        if self.flex_count() < self.FLEX_STANDARD.get(
                self._info[Constant.COL_TYPE].strip(),
                self.FLEX_STANDARD_DEFAULT
        ):
            _cnt += 1
        return _cnt


# 不要为纯数字

all_methods = {
    "集训队日常管理办法": MethodRegular,
    "集训队假期管理方法241001 10-01~10-04 9:00~17:00": MethodVacation241001,
    "集训队假期管理方法240420 4-22~4-30": MethodVacation20240430,
    "集训队假期管理方法240501 05-02~05-03 9:00~17:00": MethodVacation20240501,
    "集训队假期管理方法240506 05-06~05-12": MethodVacation20240506,
}
