# 浙江理工大学 ACM 集训队考勤统计
# Jamhus Tao @ 2023
# Last: 2023 / 9 / 12
import sys
import time
import traceback

from Modulo import Ask
from Modulo import Spider
from Modulo import Writer
from Modulo import Constant
from Modulo import Methods

TIME_RANGE = (0.0, 0.0)
PATH_OUTPUT = ""  # xlsx 格式文件
METHOD_TODO = ""  # Modulo.Methods 集训队管理办法

"""
Usage:
如何使用:
有没有人读下代码, 补充一下此处注释.
"""


def _exit(code: int = 0):
    print()
    input("Exit> ")
    sys.exit(code)


# 询问参数, 只有当默认配置缺失时询问
def ask():
    global TIME_RANGE, PATH_OUTPUT, METHOD_TODO
    TIME_RANGE = (Ask.ask_datetime("统计开始时间:"), Ask.ask_datetime("统计结束时间:", upper=True))

    PATH_OUTPUT = Ask.ask_openfilename(
        hint="选择文件输出位置:",
        callback=_exit,
        initialdir='.',
        defaultextension=".xlsx",
        filetypes=(("Excel", (".xls", ".xlsx")),)
    )
    METHOD_TODO = tuple(Methods.all_methods.keys())[
        Ask.ask_choose_from_tuple(
            "选择执行方案, 执行方案是从数据计算得到相应指标的公式集:",
            tuple(Methods.all_methods.keys())
        )
    ]


def main():
    print("浙江理工大学 ACM 集训队考勤统计 - 得力e+版 Jamhus Tao @ 2023")
    print("继续维护详见源代码注释...")
    print()

    # 获取参数
    if not (TIME_RANGE[0] and TIME_RANGE[1] and PATH_OUTPUT and METHOD_TODO):
        ask()

    # 打开文件
    print("获取原始刷卡记录与训练情况历史...")
    spider = Spider.Spider(TIME_RANGE[0], TIME_RANGE[1])
    writer = Writer.Writer(PATH_OUTPUT)
    _new_col = len(writer.data[Constant.ROW_START - 1]) - Constant.COL_RECORDS_START + Constant.COL_RECORDS_LENGTH - 1
    _new_col = _new_col // Constant.COL_RECORDS_LENGTH * Constant.COL_RECORDS_LENGTH + Constant.COL_RECORDS_START

    try:
        print("计算与更新新增数据...")
        # 更新表格大小 (扩容)
        _extend = _new_col + Constant.COL_RECORDS_LENGTH - len(writer.data[Constant.ROW_START - 1])
        for _i in range(len(writer.data)):
            writer.data[_i].extend(
                [''] * _extend
            )

        # 更新新增表头
        writer.merge_range(
            (Constant.ROW_START - 2, _new_col),
            (Constant.ROW_START - 1, _new_col + Constant.COL_RECORDS_LENGTH),
        )
        _st, _ed = spider.TimeRange
        _mk_st = time.localtime(_st)
        _mk_ed = time.localtime(_ed)
        writer.data[Constant.ROW_START - 2][_new_col] = "{}-{}-{} ~ {}-{}-{}".format(
            _mk_st.tm_year, _mk_st.tm_mon, _mk_st.tm_mday,
            _mk_ed.tm_year, _mk_ed.tm_mon, _mk_ed.tm_mday,
        )
        writer.data[Constant.ROW_START - 1][_new_col + Constant.COL_RECORDS_SECONDS] \
            = Constant.COL_RECORDS_SECONDS_TITLE  # 打卡时长
        writer.data[Constant.ROW_START - 1][_new_col + Constant.COL_RECORDS_FLEX_COUNT] \
            = Constant.COL_RECORDS_FLEX_COUNT_TITLE  # 灵活次数
        writer.data[Constant.ROW_START - 1][_new_col + Constant.COL_RECORDS_REGULAR_COUNT] \
            = Constant.COL_RECORDS_REGULAR_COUNT_TITLE  # 固定次数
        writer.data[Constant.ROW_START - 1][_new_col + Constant.COL_RECORDS_VIOLATION_COUNT] \
            = Constant.COL_RECORDS_VIOLATION_COUNT_TITLE  # 新增违规
        writer.data[Constant.ROW_START - 1][_new_col + Constant.COL_RECORDS_REMARK] \
            = Constant.COL_RECORDS_REMARK_TITLE  # 备注

        # 更新新增信息
        for _i in range(Constant.ROW_START, len(writer.data)):
            _id = writer.data[_i][Constant.COL_ID].strip().upper()
            if not Constant.ID_TYPE_TEXT:
                _id = str(int(float(_id)))

            # 选择执行方案
            method = Methods.all_methods[METHOD_TODO](writer.data[_i], spider.MemberClockinRecords.get(_id, []))
            writer.data[_i][_new_col + Constant.COL_RECORDS_SECONDS] = method.seconds()  # 打卡时长
            writer.data[_i][_new_col + Constant.COL_RECORDS_FLEX_COUNT] = method.flex_count()  # 灵活次数
            writer.data[_i][_new_col + Constant.COL_RECORDS_REGULAR_COUNT] = method.regular_count()  # 固定次数
            writer.data[_i][_new_col + Constant.COL_RECORDS_VIOLATION_COUNT] = method.violation_count()  # 新增违规

        # 递交新增信息 (含新增表头)
        writer.rewrite_range(
            (Constant.ROW_START - 2, _new_col),
            (len(writer.data), _new_col + Constant.COL_RECORDS_LENGTH),
        )

        # 更新人员基本信息
        for _i in range(Constant.ROW_START, len(writer.data)):
            # 更新违规次数公式
            writer.data[_i][Constant.COL_VIOLATION_COUNT] = "={}".format(
                "+".join(
                    [writer.excel_index(_i, __) for __ in range(
                        Constant.COL_RECORDS_START + Constant.COL_RECORDS_VIOLATION_COUNT,
                        _new_col + Constant.COL_RECORDS_LENGTH,
                        Constant.COL_RECORDS_LENGTH
                    )]
                )
            )

        # 递交人员基本信息更新
        print("正在将结果写入文件...")
        writer.rewrite_range(
            (Constant.ROW_START, Constant.COL_VIOLATION_COUNT),
            (len(writer.data), Constant.COL_VIOLATION_COUNT + 1),
        )  # 仅更新了违规次数公式
    except Exception:
        traceback.print_exc(file=sys.stdout)
    finally:
        # 关闭文件
        writer.close()
        _exit()


if __name__ == '__main__':
    main()
