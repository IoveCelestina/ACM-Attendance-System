#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Constant.ini文件的当前内容
"""

import os
import time

def check_constant_ini():
    """检查Constant.ini文件的内容"""
    ini_path = 'Constant.ini'
    
    if not os.path.exists(ini_path):
        print(f"❌ 文件不存在: {ini_path}")
        return
    
    # 获取文件信息
    stat = os.stat(ini_path)
    print(f"=== Constant.ini 文件信息 ===")
    print(f"文件路径: {os.path.abspath(ini_path)}")
    print(f"文件大小: {stat.st_size} 字节")
    print(f"最后修改: {time.ctime(stat.st_mtime)}")
    print(f"最后访问: {time.ctime(stat.st_atime)}")
    
    # 读取文件内容
    try:
        with open(ini_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"\n=== 文件内容 ===")
        print(content)
        
        # 查找关键配置项
        print(f"\n=== 关键配置项 ===")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if any(keyword in line for keyword in ['AUTH_CODE', 'AUTH_ID', 'ORG_ID', 'REMOTE_URL']):
                print(f"第{i+1:2d}行: {line}")
        
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("检查Constant.ini文件...")
    check_constant_ini()

if __name__ == '__main__':
    main()
