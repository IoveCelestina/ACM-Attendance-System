import xlwings
from Modulo import Constant


# 写入类, 写入所有到输出表格
# 原输出表格必须原有一定格式, 不能为空, 格式通过包 Constant 中的系列常量定义
class Writer:
    """
    写入类实现 self.data 与 excel 文件的同步, 其中参数 fp 表示需要同步的 excel 文件, 但同步需要手动同步
    __init__ 初始化类并将 excel 文件内容同步到 self.data, 使用 xlwings 进行 excel 读写
    self.data 公有, 并且保证为矩阵. 直接操作即可
    rewrite 将 self.data 全部同步到 excel 文件, 再次提醒同步需要手动提交
    rewrite_range 将 self.data 中的部分同步到 excel 文件, 通常表格中只有部分区间需要同步, 这样减少读写量

    另外在代码实现中需要特别注意的点有:
    * xlwings 写入时自动识别数据类型, 但是似乎这个地方问题很大, 需要通过系列操作规避自动识别 (别问我就是这么答辩)
    * xlwings 中所有索引使用 1-index, 而 Python 内置数据类型均采用 0-index (别问我源作者怎么想的). 在我的代码习惯中, 该类所有对外接口均为 0-index
    * xlwings 异常退出, 即未调用 app.quit() 时, 将残留僵尸进程 (具体由本地 Excel 编辑器决定), 同时可能导致文件无法二次打开. 请注意异常处理, 遇到时清理后台进程
    """

    # 先从原表格读取原信息
    def __init__(self, fp):
        self.__app = xlwings.App(visible=False)
        try:
            self.__book = self.__app.books.open(fp)
            self.__sheet = self.__book.sheets[0]
            self.data = []
            _len = 1
            while self.__sheet.range(Constant.ROW_START - 1, _len).value or \
                    self.__sheet.range(Constant.ROW_START, _len).value:
                _len += 1
            _len -= 1
            _i = 0  # 从第0行开始读取，xlwings会自动转换为1基索引
            while True:
                _item = self.__format_data(self.__sheet.range((_i + 1, 1), (_i + 1, _len)).value)
                _yep = False
                for _cell in _item:
                    if _cell:
                        _yep = True
                        break
                if not _yep:
                    break
                self.data.append(_item)
                _i += 1
        except Exception:
            self.__app.quit()
            raise

    # 将任意类型转换为 str
    @staticmethod
    def __any2str(x) -> str:
        if x is None:
            return ""
        # if isinstance(x, str):
        #     return "'{}".format(x)
        if isinstance(x, float):
            return str(int(x * 100) / 100)
        return str(x)

    # 格式化列表为全部 str, 避免触发 xlwings 的 BUG
    @staticmethod
    def __format_data(ls: list) -> list:
        return [Writer.__format_data(__) if isinstance(__, list) else Writer.__any2str(__) for __ in ls]

    # 刷新表格的限定区间, 以减少读写量
    def rewrite_range(self, st: tuple, ed: tuple):
        self.__sheet.range(
            st[0] + 1, st[1] + 1
        ).expand().value = [
            __[st[1]:ed[1]] for __ in self.__format_data(self.data)[st[0]:ed[0]]
        ]

    # 刷新表格全部区间
    def rewrite(self):
        self.__sheet.range("A1").expand().value = self.__format_data(self.data)

    # 合并单元格
    def merge_range(self, st: tuple, ed: tuple):
        self.__sheet.range((st[0] + 1, st[1] + 1), ed).api.Merge()

    # 获取 Excel 风格索引, 如 (0, 0) -> A1
    def excel_index(self, r, c):
        _tmp = str(self.__sheet.range(r + 1, c + 1)).split('$')
        return _tmp[1] + _tmp[2][:-1]

    # 保存并关闭
    def close(self):
        self.__book.save()
        self.__book.close()
        self.__app.quit()
