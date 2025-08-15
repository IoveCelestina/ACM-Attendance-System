#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复端口冲突的认证信息获取脚本
专门用于获取add请求中的Authorization和Member_id
"""

import time
import json
import os
import sys
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def setup_driver():
    """设置Chrome浏览器驱动，避免端口冲突"""
    try:
        print("正在配置Chrome浏览器...")
        
        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # 修复端口冲突
        chrome_options.add_argument("--remote-debugging-port=0")  # 使用随机端口
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        
        # 添加唯一的用户数据目录，避免冲突
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="chrome_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        print(f"使用临时用户数据目录: {temp_dir}")
        
        # 启用网络日志记录
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        # 使用项目中的ChromeDriver
        chromedriver_path = "./chromedriver-win64/chromedriver.exe"
        
        if not os.path.exists(chromedriver_path):
            print(f"ChromeDriver不存在: {chromedriver_path}")
            return None
        
        print(f"使用ChromeDriver: {chromedriver_path}")
        
        try:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome浏览器启动成功")
            return driver
        except Exception as e:
            print(f"启动Chrome浏览器失败: {e}")
            return None
        
    except Exception as e:
        print(f"启动Chrome浏览器失败: {e}")
        return None

def get_auth_from_add_requests():
    """直接获取add请求中的认证信息"""
    driver = None
    # 初始化变量
    auth_code = None
    member_id = None
    
    try:
        print("启动浏览器...")
        driver = setup_driver()
        
        if not driver:
            return None, None
        
        print("正在打开得力e+登录页面...")
        driver.get("https://v2-web.delicloud.com/login")
        
        # 等待页面加载
        time.sleep(5)
        print("登录页面加载完成")
        print("请在页面上扫码登录...")
        print("等待登录完成...")
        
        # 等待登录完成
        start_time = time.time()
        while time.time() - start_time < 300:  # 5分钟超时
            try:
                current_url = driver.current_url
                if "login" not in current_url:
                    print("检测到登录成功")
                    break
                time.sleep(2)
            except:
                time.sleep(2)
        else:
            print("登录超时")
            return None, None
        
        print("正在访问打卡记录页面...")
        
        # 直接访问打卡记录页面，这里通常会有add请求
        driver.get("https://v2-eapp.delicloud.com/checkin2/web/checkIn/record")
        
        # 等待页面完全加载
        print("等待页面加载...")
        time.sleep(20)
        print("页面加载完成")
        
        # 等待一段时间让页面发送所有请求
        print("等待网络请求...")
        time.sleep(30)
        
        # 获取网络日志
        print("分析网络请求...")
        try:
            logs = driver.get_log('performance')
            print(f"捕获到 {len(logs)} 条网络请求记录")
            
            # 专门寻找add请求
            add_requests = []
            
            for i, log in enumerate(logs):
                try:
                    message = json.loads(log['message'])
                    if 'message' in message and message['message']['method'] == 'Network.requestWillBeSent':
                        request = message['message']['params']['request']
                        url = request.get('url', '')
                        headers = request.get('headers', {})
                        
                        # 寻找add请求
                        if 'add' in url.lower() and 'tracking' in url.lower():
                            print(f"发现add请求 [{i+1}]: {url}")
                            print(f"  请求头: {list(headers.keys())}")
                            
                            add_requests.append({
                                'index': i+1,
                                'url': url,
                                'headers': headers
                            })
                            
                            # 检查认证头
                            if 'authorization' in headers:
                                auth_code = headers['authorization']
                                print(f"✅ 获取到Authorization: {auth_code}")
                            
                            if 'member_id' in headers:
                                member_id = headers['member_id']
                                print(f"✅ 获取到Member_id: {member_id}")
                            
                            if 'Member_id' in headers:
                                member_id = headers['Member_id']
                                print(f"✅ 获取到Member_id: {member_id}")
                            
                            if auth_code and member_id:
                                print("🎉 成功获取到完整认证信息！")
                                return auth_code, member_id
                        
                        # 每处理100条记录显示进度
                        if (i + 1) % 100 == 0:
                            print(f"已处理 {i + 1}/{len(logs)} 条记录...")
                            
                except:
                    continue
            
            # 如果没有找到add请求，显示所有API请求
            if not add_requests:
                print("未找到add请求，检查所有API请求...")
                api_requests = []
                for i, log in enumerate(logs):
                    try:
                        message = json.loads(log['message'])
                        if 'message' in message and message['message']['method'] == 'Network.requestWillBeSent':
                            request = message['message']['params']['request']
                            url = request.get('url', '')
                            if '/api/' in url:
                                api_requests.append({
                                    'index': i+1,
                                    'url': url,
                                    'method': request.get('method', 'GET')
                                })
                    except:
                        continue
                
                if api_requests:
                    print(f"发现 {len(api_requests)} 个API请求:")
                    for req in api_requests[:20]:  # 显示前20个
                        print(f"  [{req['index']}] {req['method']} {req['url']}")
                        
        except Exception as e:
            print(f"获取网络日志失败: {e}")
        
        # 如果还是没有获取到，使用默认值
        print("使用默认值...")
        if not member_id:
            member_id = "46"  # 默认member_id
            print(f"使用默认member_id: {member_id}")
        
        return auth_code, member_id
        
    finally:
        if driver:
            print("正在关闭浏览器...")
            try:
                driver.quit()
            except:
                pass

def update_config_file(auth_code, member_id, org_id=None):
    """更新配置文件"""
    if not auth_code or not member_id:
        print("认证信息不完整，无法更新配置文件")
        return False
    
    try:
        # 读取配置文件
        with open("Constant.ini", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换认证信息
        import re
        
        # 替换AUTH_CODE
        content = re.sub(
            r"AUTH_CODE\s*=\s*'[^']*'",
            f"AUTH_CODE = '{auth_code}'",
            content
        )
        
        # 替换AUTH_ID
        content = re.sub(
            r"AUTH_ID\s*=\s*'[^']*'",
            f"AUTH_ID = '{member_id}'",
            content
        )
        
        # 如果获取到了组织ID，也更新ORG_ID
        if org_id:
            content = re.sub(
                r"ORG_ID\s*=\s*'[^']*'",
                f"ORG_ID = '{org_id}'",
                content
            )
            print(f"   ORG_ID: {org_id}")
        
        # 写回文件
        with open("Constant.ini", 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 配置文件 Constant.ini 更新成功")
        print(f"   AUTH_CODE: {auth_code}")
        print(f"   AUTH_ID: {member_id}")
        return True
        
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("修复端口冲突的认证信息获取脚本")
    print("=" * 60)
    
    # 检查必要的文件
    if not os.path.exists("Constant.ini"):
        print("❌ 错误: 未找到 Constant.ini 配置文件")
        print("请确保脚本在正确的项目目录中运行")
        input("按Enter键退出...")
        return
    
    if not os.path.exists("chromedriver-win64/chromedriver.exe"):
        print("❌ 错误: 未找到 ChromeDriver")
        print("请确保 chromedriver-win64 文件夹在项目目录中")
        input("按Enter键退出...")
        return
    
    # 获取认证信息
    print("\n开始获取认证信息...")
    auth_code, member_id = get_auth_from_add_requests()
    
    if not auth_code or not member_id:
        print("❌ 获取认证信息失败！")
        print("请检查网络连接和登录状态")
        input("按Enter键退出...")
        return
    
    print(f"\n✅ 获取到认证信息:")
    print(f"   AUTH_CODE: {auth_code}")
    print(f"   AUTH_ID: {member_id}")
    
    # 更新配置文件
    print("\n正在更新配置文件...")
    if update_config_file(auth_code, member_id):
        print("\n🎉 认证信息获取和配置文件更新完成！")
        print("现在可以运行考勤统计功能了")
    else:
        print("\n❌ 配置文件更新失败！")
    
    input("按Enter键退出...")

if __name__ == "__main__":
    main()

