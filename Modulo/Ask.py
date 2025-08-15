import re
import time
import tkinter
from tkinter import filedialog

_app = tkinter.Tk()
_app.withdraw()


def __try_int(x: str, base: int = 10):
    try:
        _x = int(x.strip(), base)
        return _x
    except ValueError:
        return None


def __parser_date(x: str) -> tuple | None:
    _date = [__try_int(__) for __ in re.split("[-/]", x)]
    if len(_date) != 3:
        return None
    for _item in _date:
        if _item is None:
            return None
    if _date[0] < 100:
        _date[0] += time.localtime().tm_year // 100 * 100
    if _date[0] < 1970:
        return None
    return tuple(_date)


def __parser_time(x: str) -> tuple | None:
    _time = [__try_int(__) for __ in x.split(":")]
    if len(_time) != 3:
        return None
    for _item in _time:
        if _item is None:
            return None
    return tuple(_time)


def ask_datetime(hint: str, upper: bool = False) -> float:
    if hint:
        print(hint)
    print("请输入日期时间格式: 合法格式有 2023-10-27 19:30:00 | 2023-10-27 | 19:30:00")

    _ret = 0.0
    while True:
        _s = input("> ").strip()
        _tmp = _s.split()
        if len(_tmp) == 1:
            _tmp = _tmp[0]
            if "-" in _tmp or "/" in _tmp:
                _date = __parser_date(_tmp)
                if _date is not None:
                    _ret = time.mktime(_date + ((23, 59, 59) if upper else (0, 0, 0)) + (0,) * 3)
                    break
                print("无法识别的日期格式")
            elif ":" in _tmp:
                _time = __parser_time(_tmp)
                if _time is not None:
                    _ret = time.time() // 86400 * 86400 + _time[0] * 3600 + _time[1] * 60 + _time[2]
                    break
                print("无法识别的时间格式")
            else:
                print("无法识别的日期时间格式")
        elif len(_tmp) == 2:
            _date = __parser_date(_tmp[0])
            _time = __parser_time(_tmp[1])
            if _date is not None and _time is not None:
                _ret = time.mktime(_date + _time + (0,) * 3)
                break
            print("无法识别的日期时间格式")
        else:
            print("无法识别的日期时间格式")

    print(time.strftime("已选择时间: %Y-%m-%d %H:%M:%S", time.localtime(_ret)))
    return _ret


def ask_choose_from_tuple(hint: str, tuple_: tuple) -> int:
    if hint:
        print(hint)

    _width, _x = 0, len(tuple_)
    while _x:
        _width += 1
        _x //= 10
    if _width == 0:
        print("没有可选择的条目")
        return 0
    _format = "{{:{}d}} {{}}".format(_width)

    for _i, _item in enumerate(tuple_):
        print(_format.format(_i + 1, _item))

    while True:
        _s = input("> ").strip()
        _x = __try_int(_s)
        if _x is None:
            for _i, _item in enumerate(tuple_):
                if _s == _item.strip():
                    print("已选中条目: {}".format(_item))
                    return _i
            print("未找到相关选项, 请重新输入")
        else:
            if 1 <= _x <= len(tuple_):
                print("已选中条目: {}".format(tuple_[_x - 1]))
                return _x - 1
            else:
                print("未找到相关编号, 请重新输入")


def ask_openfilename(hint=None, callback=None, **kwargs) -> str:
    """
    终端询问文件名称
    :param hint: 提供用户提示
    :param callback: 如果返回为空将调用回调函数, 传入 None 表示直接返回
    :param kwargs: filedialog.askopenfilename 参数
    :return: 询问文件的名称
    """
    if hint is not None:
        print(hint)
    print("> ", end="")
    _openfilename = filedialog.askopenfilename(**kwargs)
    if _openfilename == "" and callback is not None:
        return callback()
    print(_openfilename)
    return _openfilename
