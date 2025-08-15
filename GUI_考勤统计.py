# 浙江理工大学 ACM 集训队考勤统计 - 图形化界面版

# Jamhus Tao @ 2023

# Last: 2023 / 9 / 12

# GUI Version: 2024

import sys

import time

import traceback

import tkinter as tk

from tkinter import ttk, filedialog, messagebox, simpledialog

from tkcalendar import DateEntry

from datetime import datetime, timedelta

import threading

import warnings
import os

# 过滤掉libpng的iCCP警告
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'
warnings.filterwarnings("ignore", category=UserWarning)


from Modulo import Ask

from Modulo import Spider

from Modulo import Writer

from Modulo import Constant

from Modulo import Methods





class ACMAttendanceGUI:

    def __init__(self, root):

        self.root = root

        self.root.title("浙江理工大学 ACM 集训队考勤统计系统")

        self.root.geometry("800x600")

        self.root.resizable(True, True)

        

        # 配置变量

        self.time_range = (0.0, 0.0)

        self.path_output = ""

        self.method_todo = ""

        self.selected_dates = []

        

        # 创建界面

        self.create_widgets()

        

        # 加载默认配置

        self.load_default_config()

    

    def create_widgets(self):

        # 创建主框架

        main_frame = ttk.Frame(self.root, padding="10")

        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        

        # 配置网格权重

        self.root.columnconfigure(0, weight=1)

        self.root.rowconfigure(0, weight=1)

        main_frame.columnconfigure(1, weight=1)

        

        # 标题

        title_label = ttk.Label(main_frame, text="ACM集训队考勤统计系统", 

                               font=("Arial", 16, "bold"))

        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        

        # 统计方式选择

        ttk.Label(main_frame, text="统计方式:").grid(row=1, column=0, sticky=tk.W, pady=5)

        self.stat_method = tk.StringVar(value="时间段")

        stat_frame = ttk.Frame(main_frame)

        stat_frame.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        

        ttk.Radiobutton(stat_frame, text="时间段统计", variable=self.stat_method, 

                       value="时间段", command=self.on_stat_method_change).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Radiobutton(stat_frame, text="指定日期统计", variable=self.stat_method, 

                       value="指定日期", command=self.on_stat_method_change).pack(side=tk.LEFT)

        

        # 时间段选择框架

        self.time_range_frame = ttk.LabelFrame(main_frame, text="时间段设置", padding="10")

        self.time_range_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        

        ttk.Label(self.time_range_frame, text="开始时间:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        self.start_date = DateEntry(self.time_range_frame, width=15, date_pattern='yyyy-mm-dd')

        self.start_date.grid(row=0, column=1, padx=(0, 20))

        

        ttk.Label(self.time_range_frame, text="结束时间:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))

        self.end_date = DateEntry(self.time_range_frame, width=15, date_pattern='yyyy-mm-dd')

        self.end_date.grid(row=0, column=3, padx=(0, 20))

        

        # 设置默认时间为当前日期

        today = datetime.now()

        self.start_date.set_date(today - timedelta(days=7))

        self.end_date.set_date(today)

        

        # 指定日期选择框架

        self.specific_dates_frame = ttk.LabelFrame(main_frame, text="指定日期设置", padding="10")

        self.specific_dates_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        
        # 日期输入框
        ttk.Label(self.specific_dates_frame, text="输入日期:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.date_entry = ttk.Entry(self.specific_dates_frame, width=15)
        self.date_entry.grid(row=0, column=1, padx=(0, 20))
        self.date_entry.insert(0, "2025-01-01")
        self.date_entry.bind('<Return>', self.add_date_from_entry)
        ttk.Label(self.specific_dates_frame, text="格式: YYYY-MM-DD，按Enter添加").grid(row=0, column=2, sticky=tk.W)
        

        dates_control_frame = ttk.Frame(self.specific_dates_frame)

        dates_control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        

        ttk.Button(dates_control_frame, text="添加日期", 

                  command=self.add_date).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(dates_control_frame, text="删除选中", 

                  command=self.remove_date).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(dates_control_frame, text="清空所有", 

                  command=self.clear_dates).pack(side=tk.LEFT)

        

        # 日期列表

        self.dates_listbox = tk.Listbox(self.specific_dates_frame, height=6)

        self.dates_listbox.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        

        # 滚动条

        dates_scrollbar = ttk.Scrollbar(self.specific_dates_frame, orient=tk.VERTICAL, 

                                       command=self.dates_listbox.yview)

        dates_scrollbar.grid(row=2, column=2, sticky=(tk.N, tk.S))
        self.dates_listbox.configure(yscrollcommand=dates_scrollbar.set)

        

        # 文件输出设置

        ttk.Label(main_frame, text="输出文件:").grid(row=4, column=0, sticky=tk.W, pady=10)

        self.file_frame = ttk.Frame(main_frame)

        self.file_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        

        self.file_path_var = tk.StringVar()

        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, state="readonly")

        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        ttk.Button(self.file_frame, text="选择文件", command=self.select_output_file).pack(side=tk.RIGHT)

        

        # 统计规则设置

        ttk.Label(main_frame, text="统计规则:").grid(row=5, column=0, sticky=tk.W, pady=10)

        self.method_combo = ttk.Combobox(main_frame, values=list(Methods.all_methods.keys()), 

                                        state="readonly", width=50)

        self.method_combo.grid(row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        self.method_combo.set("集训队日常管理办法")

        

        # 高级设置按钮

        ttk.Button(main_frame, text="高级设置", command=self.show_advanced_settings).grid(

            row=6, column=1, sticky=tk.W, pady=5)

        

        # 开始统计按钮

        self.start_button = ttk.Button(main_frame, text="开始统计", command=self.start_statistics,

                                      style="Accent.TButton")

        self.start_button.grid(row=7, column=0, columnspan=3, pady=20)

        

        # 进度条

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')

        self.progress.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        

        # 状态标签

        self.status_label = ttk.Label(main_frame, text="就绪", foreground="green")

        self.status_label.grid(row=9, column=0, columnspan=3, pady=5)

        

        # 初始化界面状态

        self.on_stat_method_change()

    

    def on_stat_method_change(self):

        """统计方式改变时的处理"""

        if self.stat_method.get() == "时间段":

            self.time_range_frame.grid()

            self.specific_dates_frame.grid_remove()

        else:

            self.time_range_frame.grid_remove()

            self.specific_dates_frame.grid()

    

    def add_date_from_entry(self, event=None):
        """从输入框添加日期"""
        try:
            date_str = self.date_entry.get().strip()
            if not date_str:
                return
            
            # 解析日期字符串
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            if selected_date not in self.selected_dates:
                self.selected_dates.append(selected_date)
                self.selected_dates.sort()
                self.update_dates_listbox()
                # 清空输入框
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, "2025-01-01")
            else:
                messagebox.showwarning("警告", "该日期已存在！")
        except ValueError:
            messagebox.showerror("错误", "日期格式错误！请使用 YYYY-MM-DD 格式")
    
    def add_date(self):

        """添加指定日期"""

        date_dialog = DateEntry(self.root, title="选择日期", date_pattern='yyyy-mm-dd')

        date_dialog.grid()

        

        def on_date_select():

            selected_date = date_dialog.get_date()

            if selected_date not in self.selected_dates:

                self.selected_dates.append(selected_date)

                self.selected_dates.sort()

                self.update_dates_listbox()

            date_dialog.destroy()

        

        date_dialog.bind("<<DateEntrySelected>>", lambda e: on_date_select())

    

    def remove_date(self):

        """删除选中的日期"""

        selection = self.dates_listbox.curselection()

        if selection:

            index = selection[0]

            del self.selected_dates[index]

            self.update_dates_listbox()

    

    def clear_dates(self):

        """清空所有日期"""

        self.selected_dates.clear()

        self.update_dates_listbox()

    

    def update_dates_listbox(self):

        """更新日期列表显示"""

        self.dates_listbox.delete(0, tk.END)

        for date in self.selected_dates:

            self.dates_listbox.insert(tk.END, date.strftime('%Y-%m-%d'))

    

    def select_output_file(self):

        """选择输出文件"""

        filename = filedialog.asksaveasfilename(

            title="选择输出文件",

            defaultextension=".xlsx",

            filetypes=[("Excel文件", "*.xlsx"), ("Excel文件", "*.xls"), ("所有文件", "*.*")]

        )

        if filename:

            # 更新变量
            self.file_path_var.set(filename)

            # 直接写入输入框（确保立刻可见）
            try:
                self.file_entry.config(state="normal")
                self.file_entry.delete(0, tk.END)
                self.file_entry.insert(0, filename)
                # 将视图滚动到末尾，便于看到文件名
                self.file_entry.xview_moveto(1.0)
            finally:
                self.file_entry.config(state="readonly")
    

    def show_advanced_settings(self):

        """显示高级设置对话框"""

        self.create_advanced_settings_dialog()

    

    def create_advanced_settings_dialog(self):

        """创建高级设置对话框"""

        dialog = tk.Toplevel(self.root)

        dialog.title("高级设置")

        dialog.geometry("600x500")

        dialog.transient(self.root)

        dialog.grab_set()

        

        # 创建选项卡

        notebook = ttk.Notebook(dialog)

        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        

        # 统计规则设置选项卡

        rules_frame = ttk.Frame(notebook)

        notebook.add(rules_frame, text="统计规则")

        

        # 显示当前可用的统计规则

        ttk.Label(rules_frame, text="可用的统计规则:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)

        
        # 添加说明标签
        help_label = ttk.Label(rules_frame, text="💡 提示：您可以编辑现有规则或添加新规则。格式：\n• 规则名称\n  灵活时长标准: 数字\n  固定打卡日期: 每天/周数字/无\n  训练时间: 开始日期-结束日期/间隔天数", 
                              font=("Arial", 9), foreground="blue")
        help_label.pack(anchor=tk.W, padx=10, pady=(0, 5))
        

        rules_text = tk.Text(rules_frame, height=15, width=70)

        rules_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        

        # 插入规则说明

        rules_info = "当前可用的统计规则:\n\n"

        for name, method_class in Methods.all_methods.items():

            rules_info += f"• {name}\n"

            if hasattr(method_class, 'FLEX_STANDARD'):

                rules_info += f"  灵活时长标准: {method_class.FLEX_STANDARD}\n"

            if hasattr(method_class, 'REGULAR_WDAY'):

                reg_wday = method_class.REGULAR_WDAY
                if reg_wday == 'daily':
                    rules_info += f"  固定打卡日期: 每天\n"
                elif reg_wday == 'none':
                    rules_info += f"  固定打卡日期: 无\n"
                else:
                    rules_info += f"  固定打卡日期: 周{reg_wday + 1}\n"
            if hasattr(method_class, 'TRAIN_DAYS') or hasattr(method_class, 'TRAIN_START_DATE'):
                if hasattr(method_class, 'TRAIN_MODE'):
                    if method_class.TRAIN_MODE == 'date_range':
                        start_date = method_class.TRAIN_START_DATE
                        end_date = method_class.TRAIN_END_DATE
                        rules_info += f"  训练时间: {start_date.strftime('%Y-%m-%d')}-{end_date.strftime('%Y-%m-%d')}\n"
                    elif method_class.TRAIN_MODE == 'interval':
                        if hasattr(method_class, 'TRAIN_INTERVAL'):
                            rules_info += f"  训练时间: 间隔{method_class.TRAIN_INTERVAL}天\n"
                        else:
                            rules_info += f"  训练时间: 间隔{len(method_class.TRAIN_DAYS)}天\n"
                    else:
                        rules_info += f"  训练天数: {len(method_class.TRAIN_DAYS)}天\n"
                else:
                    if hasattr(method_class, 'TRAIN_DAYS'):
                        rules_info += f"  训练天数: {len(method_class.TRAIN_DAYS)}天\n"

            rules_info += "\n"

        

        # 添加示例自定义规则
        rules_info += "示例自定义规则:\n"
        rules_info += "• 寒假训练规则\n"
        rules_info += "  灵活时长标准: 20\n"
        rules_info += "  固定打卡日期: 每天\n"
        rules_info += "  训练时间: 2025-01-20-2025-02-05\n\n"
        rules_info += "• 周末训练规则\n"
        rules_info += "  灵活时长标准: 16\n"
        rules_info += "  固定打卡日期: 周6\n"
        rules_info += "  训练时间: 间隔2天\n\n"
        rules_info += "• 无固定打卡规则\n"
        rules_info += "  灵活时长标准: 18\n"
        rules_info += "  固定打卡日期: 无\n"
        rules_info += "  训练时间: 2025-03-01-2025-03-15\n\n"
        
        rules_text.insert(tk.END, rules_info)

        # 允许用户编辑规则
        # rules_text.config(state=tk.DISABLED)  # 注释掉只读设置
        

        # 配置参数选项卡

        config_frame = ttk.Frame(notebook)

        notebook.add(config_frame, text="配置参数")

        

        # 显示当前配置

        ttk.Label(config_frame, text="当前配置参数:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=10)

        

        config_text = tk.Text(config_frame, height=15, width=70)

        config_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        

        # 插入配置信息

        config_info = f"""当前配置参数:



工号类型: {'文本' if Constant.ID_TYPE_TEXT else '数值'}

正文开始行号: {Constant.ROW_START}

频繁打卡过滤: {Constant.FREQUENCY_FILTER}秒

时差校正: {Constant.DELTA_TIME}秒



列配置:

- 工号列: {Constant.COL_ID}

- 姓名列: {Constant.COL_NAME}

- 性别列: {Constant.COL_GENDER}

- 类别列: {Constant.COL_TYPE}

- 违规次数列: {Constant.COL_VIOLATION_COUNT}

- 晋升正式队员列: {Constant.COL_ADVANCE_FORMAL}

- 晋升参赛队员列: {Constant.COL_ADVANCE_OUTING}

- 记录开始列: {Constant.COL_RECORDS_START}

- 记录长度: {Constant.COL_RECORDS_LENGTH}

"""

        

        config_text.insert(tk.END, config_info)

        # 允许用户编辑配置
        # config_text.config(state=tk.DISABLED)  # 注释掉只读设置
        
        # 添加保存和关闭按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="保存修改", command=lambda: self.save_advanced_settings(rules_text, config_text, dialog)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="关闭", command=dialog.destroy).pack(side=tk.LEFT)
    
    def save_advanced_settings(self, rules_text, config_text, dialog):
        """保存高级设置"""
        try:
            # 获取修改后的规则文本
            modified_rules = rules_text.get(1.0, tk.END).strip()
            modified_config = config_text.get(1.0, tk.END).strip()
            
            # 解析并保存自定义规则
            if self.parse_and_save_custom_rules(modified_rules):
                messagebox.showinfo("保存成功", "自定义统计规则已保存并添加到系统中！\n现在可以在统计规则下拉列表中选择使用。")
                
                # 更新统计规则下拉列表
                self.update_methods_combo()
                
                # 关闭对话框
                dialog.destroy()
            else:
                messagebox.showwarning("保存警告", "规则格式可能有问题，请检查后重试。")
                
        except Exception as e:
            messagebox.showerror("保存失败", f"保存设置时出现错误：\n{str(e)}")
    
    def parse_and_save_custom_rules(self, rules_text):
        """解析并保存自定义规则"""
        try:
            # 简单的规则解析逻辑
            lines = rules_text.split('\n')
            custom_rules = {}
            current_rule = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('• '):
                    # 新规则开始
                    rule_name = line[2:]  # 移除 "• " 前缀
                    current_rule = rule_name
                    custom_rules[current_rule] = {}
                elif line.startswith('  灵活时长标准: ') and current_rule:
                    # 解析灵活时长标准
                    value = line.replace('  灵活时长标准: ', '')
                    try:
                        custom_rules[current_rule]['FLEX_STANDARD'] = int(value)
                    except ValueError:
                        pass
                elif line.startswith('  固定打卡日期: ') and current_rule:
                    # 解析固定打卡日期
                    value = line.replace('  固定打卡日期: ', '')
                    if value == '每天':
                        custom_rules[current_rule]['REGULAR_WDAY'] = 'daily'
                    elif value == '无':
                        custom_rules[current_rule]['REGULAR_WDAY'] = 'none'
                    elif value.startswith('周'):
                        try:
                            day_num = int(value.replace('周', ''))
                            custom_rules[current_rule]['REGULAR_WDAY'] = day_num - 1  # 转换为0-based
                        except ValueError:
                            pass
                elif line.startswith('  训练时间: ') and current_rule:
                    # 解析训练时间
                    value = line.replace('  训练时间: ', '')
                    if '-' in value and value.count('-') == 4:  # 格式：2025-01-20-2025-02-05
                        try:
                            # 解析开始和结束日期
                            parts = value.split('-')
                            start_year, start_month, start_day = int(parts[0]), int(parts[1]), int(parts[2])
                            end_year, end_month, end_day = int(parts[3]), int(parts[4]), int(parts[5])
                            
                            start_date = datetime(start_year, start_month, start_day).date()
                            end_date = datetime(end_year, end_month, end_day).date()
                            
                            custom_rules[current_rule]['TRAIN_START_DATE'] = start_date
                            custom_rules[current_rule]['TRAIN_END_DATE'] = end_date
                            custom_rules[current_rule]['TRAIN_MODE'] = 'date_range'
                            
                            # 计算天数差
                            delta = end_date - start_date
                            custom_rules[current_rule]['TRAIN_DAYS'] = delta.days + 1
                            
                        except (ValueError, IndexError):
                            pass
                    elif value.startswith('间隔'):
                        try:
                            days = int(value.replace('间隔', '').replace('天', ''))
                            custom_rules[current_rule]['TRAIN_INTERVAL'] = days
                            custom_rules[current_rule]['TRAIN_MODE'] = 'interval'
                        except ValueError:
                            pass
                    elif value.isdigit():
                        # 纯数字，作为间隔天数处理
                        try:
                            days = int(value)
                            custom_rules[current_rule]['TRAIN_INTERVAL'] = days
                            custom_rules[current_rule]['TRAIN_MODE'] = 'interval'
                        except ValueError:
                            pass
            
            # 创建真正的统计方法类并添加到Methods.all_methods中
            for rule_name, rule_config in custom_rules.items():
                # 创建自定义方法类
                custom_method_class = self.create_custom_method_class(rule_name, rule_config)
                if custom_method_class:
                    # 添加到Methods.all_methods中
                    Methods.all_methods[rule_name] = custom_method_class
            
            # 保存到实例变量中，供后续使用
            if hasattr(self, 'custom_methods'):
                self.custom_methods.update(custom_rules)
            else:
                self.custom_methods = custom_rules
            
            return len(custom_rules) > 0
            
        except Exception as e:
            print(f"解析规则时出错: {e}")
            return False
    
    def create_custom_method_class(self, rule_name, rule_config):
        """创建自定义统计方法类"""
        try:
            # 导入必要的模块
            from Modulo.Methods import MethodBase
            
            # 创建自定义方法类
            class CustomMethod(MethodBase):
                def __init__(self, data, records):
                    super().__init__(data, records)
                    # 设置自定义参数
                    if 'FLEX_STANDARD' in rule_config:
                        self.FLEX_STANDARD = rule_config['FLEX_STANDARD']
                    else:
                        self.FLEX_STANDARD = 14  # 默认灵活时长标准
                    
                    if 'REGULAR_WDAY' in rule_config:
                        self.REGULAR_WDAY = rule_config['REGULAR_WDAY']
                    else:
                        self.REGULAR_WDAY = 5  # 默认周六
                    
                    if 'TRAIN_DAYS' in rule_config:
                        self.TRAIN_DAYS = rule_config['TRAIN_DAYS']
                    else:
                        self.TRAIN_DAYS = 7  # 默认7天
                    
                    if 'TRAIN_MODE' in rule_config:
                        self.TRAIN_MODE = rule_config['TRAIN_MODE']
                    else:
                        self.TRAIN_MODE = 'continuous'
                    
                    if 'TRAIN_START_DATE' in rule_config:
                        self.TRAIN_START_DATE = rule_config['TRAIN_START_DATE']
                    
                    if 'TRAIN_END_DATE' in rule_config:
                        self.TRAIN_END_DATE = rule_config['TRAIN_END_DATE']
                    
                    if 'TRAIN_INTERVAL' in rule_config:
                        self.TRAIN_INTERVAL = rule_config['TRAIN_INTERVAL']
                    else:
                        self.TRAIN_INTERVAL = 1
                
                def _calc_seconds(self) -> str:
                    """计算打卡时长"""
                    _seconds = 0.0
                    for _st, _ed in self._data:
                        _seconds += _ed - _st
                    return "'{:02d}:{:02d}".format(int(_seconds) // 3600, int(_seconds) % 3600 // 60)
                
                def _calc_flex_count(self) -> int:
                    """计算灵活次数"""
                    _seconds = 0.0
                    for _st, _ed in self._data:
                        _seconds += _ed - _st
                    # 超过 50 min 向上取整
                    return (int(_seconds) + 600) // 3600
                
                def _calc_regular_count(self) -> int:
                    """计算固定次数"""
                    if self.REGULAR_WDAY == 'daily':
                        # 每天都要打卡
                        return len(set(time.strftime('%Y-%m-%d', time.localtime(_st)) for _st, _ in self._data))
                    elif self.REGULAR_WDAY == 'none':
                        # 无固定打卡要求
                        return 0
                    else:
                        # 指定星期几打卡
                        count = 0
                        for _st, _ed in self._data:
                            _mk_st = time.localtime(_st)
                            if _mk_st.tm_wday == self.REGULAR_WDAY:
                                count += 1
                        return count
                
                def _calc_violation_count(self) -> int:
                    """计算违规次数"""
                    # 简单实现：如果灵活次数不足标准，则违规
                    flex_hours = self._calc_flex_count()
                    if flex_hours < self.FLEX_STANDARD:
                        return self.FLEX_STANDARD - flex_hours
                    return 0
            
            # 设置类名
            CustomMethod.__name__ = rule_name
            CustomMethod.__qualname__ = rule_name
            
            return CustomMethod
            
        except Exception as e:
            print(f"创建自定义方法类时出错: {e}")
            return None
    
    def update_methods_combo(self):
        """更新统计规则下拉列表"""
        try:
            # 获取所有可用的规则（包括自定义规则）
            all_methods = list(Methods.all_methods.keys())
            
            # 添加自定义规则
            if hasattr(self, 'custom_methods'):
                for rule_name in self.custom_methods.keys():
                    if rule_name not in all_methods:
                        all_methods.append(rule_name)
            
            # 更新下拉列表
            self.method_combo['values'] = all_methods
            
            # 如果当前选中的规则不在新列表中，重置为第一个
            if self.method_combo.get() not in all_methods:
                self.method_combo.set(all_methods[0] if all_methods else "")
                
        except Exception as e:
            print(f"更新规则列表时出错: {e}")
    

    def load_default_config(self):

        """加载默认配置"""

        # 设置默认输出文件

        default_file = f"ACM考勤统计_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        self.file_path_var.set(default_file)

    

    def validate_inputs(self):

        """验证输入参数"""

        if not self.file_path_var.get():

            messagebox.showerror("错误", "请选择输出文件")

            return False

        

        if self.stat_method.get() == "时间段":

            start_date = self.start_date.get_date()

            end_date = self.end_date.get_date()

            if start_date > end_date:

                messagebox.showerror("错误", "开始时间不能晚于结束时间")

                return False

            self.time_range = (

                time.mktime(start_date.timetuple()),

                time.mktime(end_date.timetuple())

            )

        else:

            if not self.selected_dates:

                messagebox.showerror("错误", "请至少选择一个日期")

                return False

            # 将选中的日期转换为时间戳范围

            dates_timestamps = []

            # 保存允许的具体日期集合，格式为 yyyy-mm-dd，供后续过滤使用
            self.allowed_dates = set()
            for date in self.selected_dates:

                start_ts = time.mktime(date.timetuple())

                end_ts = start_ts + 24 * 3600 - 1

                dates_timestamps.extend([start_ts, end_ts])

                self.allowed_dates.add(date.strftime('%Y-%m-%d'))
            

            if dates_timestamps:

                self.time_range = (min(dates_timestamps), max(dates_timestamps))

        

        if not self.method_combo.get():

            messagebox.showerror("错误", "请选择统计规则")

            return False

        

        self.method_todo = self.method_combo.get()

        return True

    

    def start_statistics(self):

        """开始统计"""

        if not self.validate_inputs():

            return

        

        # 在线程启动前获取所有必要的参数，避免线程安全问题
        self.path_output = self.file_path_var.get()
        self.stat_method_value = self.stat_method.get()  # 获取统计方式
        self.allowed_dates_value = getattr(self, 'allowed_dates', None)  # 获取允许的日期
        
        # 禁用开始按钮

        self.start_button.config(state="disabled")

        self.progress.start()

        self.status_label.config(text="正在统计...", foreground="blue")

        

        # 在新线程中执行统计

        thread = threading.Thread(target=self.run_statistics)

        thread.daemon = True

        thread.start()

    

    def run_statistics(self):

        """执行统计任务"""

        try:

            print("浙江理工大学 ACM 集训队考勤统计 - 得力e+版 Jamhus Tao @ 2023")

            print("继续维护详见源代码注释...")

            print()

            

            # 获取参数 - 在线程启动前获取，避免线程安全问题
            TIME_RANGE = self.time_range

            PATH_OUTPUT = self.path_output  # 使用实例变量而不是直接访问tkinter变量
            METHOD_TODO = self.method_todo

            

            # 打开文件

            print("获取原始刷卡记录与训练情况历史...")

            spider = Spider.Spider(TIME_RANGE[0], TIME_RANGE[1])

            # 如果是指定日期模式，则在取回数据后按所选日期进行过滤，仅保留这些日期的记录
            if self.stat_method_value == "指定日期" and self.allowed_dates_value:
                filtered_records = {}
                for _id, pairs in spider.MemberClockinRecords.items():
                    kept = []
                    for st_ts, ed_ts in pairs:
                        day_key = time.strftime('%Y-%m-%d', time.localtime(st_ts))
                        if day_key in self.allowed_dates_value:
                            kept.append((st_ts, ed_ts))
                    if kept:
                        filtered_records[_id] = kept
                member_records = filtered_records
            else:
                member_records = spider.MemberClockinRecords
            writer = Writer.Writer(PATH_OUTPUT)

            _new_col = len(writer.data[Constant.ROW_START - 1]) - Constant.COL_RECORDS_START + Constant.COL_RECORDS_LENGTH - 1

            _new_col = _new_col // Constant.COL_RECORDS_LENGTH * Constant.COL_RECORDS_LENGTH + Constant.COL_RECORDS_START

            

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
                method = Methods.all_methods[METHOD_TODO](writer.data[_i], member_records.get(_id, []))
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
            
            # 关闭文件
            writer.close()
            
            # 更新UI状态
            self.root.after(0, self.on_statistics_complete, True, "统计完成！")
            
        except Exception as e:
            error_msg = f"统计过程中出现错误:\n{str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.root.after(0, self.on_statistics_complete, False, error_msg)
    
    def on_statistics_complete(self, success, message):
        """统计完成后的处理"""
        self.progress.stop()
        self.start_button.config(state="normal")
        
        if success:
            self.status_label.config(text=message, foreground="green")
            messagebox.showinfo("完成", f"{message}\n文件已保存到: {self.file_path_var.get()}")
        else:
            self.status_label.config(text="统计失败", foreground="red")
            messagebox.showerror("错误", message)


def main():
    # 检查是否安装了tkcalendar
    try:
        import tkcalendar
    except ImportError:
        print("错误: 需要安装tkcalendar库")
        print("请运行: pip install tkcalendar")
        return
    
    root = tk.Tk()
    app = ACMAttendanceGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()


