#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
得力e+系统认证信息获取脚本 - 工作版
使用项目中的ChromeDriver
"""

import time
import json
import configparser
import os

def setup_driver():
    """设置Chrome浏览器，使用项目中的ChromeDriver"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        print("🔧 正在配置Chrome浏览器...")
        
        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # 添加唯一的用户数据目录，避免冲突
        import tempfile
        import os
        temp_dir = tempfile.mkdtemp(prefix="chrome_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        print(f"📁 使用临时用户数据目录: {temp_dir}")
        
        # 启用网络日志记录
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        
        # 使用项目中的ChromeDriver
        chromedriver_path = "./chromedriver-win64/chromedriver.exe"
        
        if not os.path.exists(chromedriver_path):
            print(f"❌ ChromeDriver不存在: {chromedriver_path}")
            return None
        
        print(f"📁 使用ChromeDriver: {chromedriver_path}")
        
        try:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Chrome浏览器启动成功")
            return driver
        except Exception as e:
            print(f"❌ 启动Chrome浏览器失败: {e}")
            return None
        
    except ImportError as e:
        print(f"❌ 缺少必要的依赖包: {e}")
        print("请运行: pip install selenium")
        return None
    except Exception as e:
        print(f"❌ 启动Chrome浏览器失败: {e}")
        return None

def get_auth_info():
    """获取认证信息"""
    driver = None
    try:
        print("🚀 启动浏览器...")
        driver = setup_driver()
        
        if not driver:
            return None, None
        
        print("🌐 正在打开得力e+登录页面...")
        driver.get("https://v2-web.delicloud.com/login")
        
        # 等待页面加载
        time.sleep(5)
        print("✅ 登录页面加载完成")
        print("📱 请在页面上扫码登录...")
        print("⏳ 等待登录完成...")
        
        # 等待登录完成
        start_time = time.time()
        while time.time() - start_time < 300:  # 5分钟超时
            try:
                current_url = driver.current_url
                if "login" not in current_url:
                    print("✅ 检测到登录成功")
                    break
                time.sleep(2)
            except:
                time.sleep(2)
        else:
            print("❌ 登录超时")
            return None, None
        time.sleep(5)
        print("🌐 正在打开打卡记录页面...")
        
        # 在打开页面之前先注入JavaScript监听器
        print("🔍 注入网络请求监听器...")
        js_code = """
        window.authInfo = { authCode: null, memberId: null };
        
        // 监听XMLHttpRequest
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url, ...args) {
            this._url = url;
            return originalXHROpen.apply(this, [method, url, ...args]);
        };
        
        XMLHttpRequest.prototype.send = function(data) {
            if (this._url && (this._url.includes('add') || this._url.includes('tracking') || this._url.includes('api'))) {
                console.log('🎯 发现相关请求:', this._url);
                
                // 检查请求头
                const authHeader = this.getRequestHeader('Authorization') || this.getRequestHeader('authorization');
                const memberIdHeader = this.getRequestHeader('Member_id') || this.getRequestHeader('member_id');
                
                if (authHeader) {
                    window.authInfo.authCode = authHeader;
                    console.log('🔑 获取到authorization:', authHeader);
                }
                if (memberIdHeader) {
                    window.authInfo.memberId = memberIdHeader;
                    console.log('🆔 获取到member_id:', memberIdHeader);
                }
            }
            return originalXHRSend.apply(this, [data]);
        };
        
        // 监听fetch
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            if (url && (url.includes('add') || url.includes('tracking') || url.includes('api'))) {
                console.log('🎯 发现fetch请求:', url);
                
                if (options.headers) {
                    const authHeader = options.headers['Authorization'] || options.headers['authorization'];
                    const memberIdHeader = options.headers['Member_id'] || options.headers['member_id'];
                    
                    if (authHeader) {
                        window.authInfo.authCode = authHeader;
                        console.log('🔑 获取到authorization:', authHeader);
                    }
                    if (memberIdHeader) {
                        window.authInfo.memberId = memberIdHeader;
                        console.log('🆔 获取到member_id:', memberIdHeader);
                    }
                }
            }
            return originalFetch.apply(this, [url, options]);
        };
        
        console.log('✅ 网络请求监听器已注入');
        """
        
        driver.execute_script(js_code)
        
        # 先访问一些基础页面来获取认证信息
        print("🌐 访问基础页面获取认证信息...")
        
        # 访问打卡首页 - 使用正确的URL
        print("📱 访问打卡首页...")
        try:
            driver.get("https://v2-web.delicloud.com/checkin2/web/index")
            time.sleep(6)
            
            # 检查页面状态
            current_url = driver.current_url
            print(f"📍 当前页面: {current_url}")
            if "login" in current_url:
                print("⚠️  被重定向到登录页面，等待重新认证...")
                time.sleep(10)
        except Exception as e:
            print(f"❌ 访问打卡首页失败: {e}")
        
        # 尝试访问工作台中的打卡功能
        print("📋 访问工作台打卡功能...")
        try:
            # 先回到工作台
            driver.get("https://v2-web.delicloud.com/dashboard")
            time.sleep(5)
            
            # 尝试查找并点击打卡相关的链接
            print("🔍 在工作台查找打卡功能...")
            try:
                # 查找包含"打卡"、"签到"等关键词的链接
                links = driver.find_elements("tag name", "a")
                for link in links:
                    try:
                        link_text = link.text.strip()
                        if any(keyword in link_text for keyword in ["打卡", "签到", "考勤", "checkin"]):
                            print(f"🎯 找到打卡相关链接: {link_text}")
                            link.click()
                            time.sleep(5)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"❌ 查找打卡功能失败: {e}")
                
        except Exception as e:
            print(f"❌ 访问工作台打卡功能失败: {e}")
        
        # 尝试直接访问打卡记录页面
        print("📊 尝试访问打卡记录页面...")
        try:
            # 尝试多个可能的URL
            possible_urls = [
                "https://v2-web.delicloud.com/checkin2/web/record",
                "https://v2-web.delicloud.com/checkin2/web/checkIn/record",
                "https://v2-web.delicloud.com/checkin2/web/checkin/record",
                "https://v2-web.delicloud.com/checkin2/web/attendance/record"
            ]
            
            for url in possible_urls:
                try:
                    print(f"🌐 尝试访问: {url}")
                    driver.get(url)
                    time.sleep(5)
                    
                    current_url = driver.current_url
                    print(f"📍 当前页面: {current_url}")
                    
                    # 如果页面没有重定向到登录页面，说明访问成功
                    if "login" not in current_url and "dashboard" not in current_url:
                        print(f"✅ 成功访问: {url}")
                        break
                    else:
                        print(f"⚠️  页面被重定向: {current_url}")
                        
                except Exception as e:
                    print(f"❌ 访问 {url} 失败: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ 访问打卡记录页面失败: {e}")
        
        # 如果所有页面都无法访问，尝试从当前页面获取认证信息
        print("🔍 从当前页面获取认证信息...")
        current_url = driver.current_url
        print(f"📍 最终页面: {current_url}")
        
        # 现在打开打卡记录页面
        print("📊 访问打卡记录页面...")
        driver.get("https://v2-eapp.delicloud.com/checkin2/web/checkIn/record")
        
        # 等待页面加载
        print("⏳ 等待页面加载...")
        time.sleep(20)
        print("✅ 打卡记录页面加载完成")
        
        # 检查页面是否正确加载
        print("🔍 检查页面状态...")
        try:
            page_title = driver.title
            current_url = driver.current_url
            print(f"📄 页面标题: {page_title}")
            print(f"🌐 当前URL: {current_url}")
            
            # 检查页面内容
            page_text = driver.find_element("tag name", "body").text
            if "暂无数据" in page_text:
                print("⚠️  页面显示'暂无数据'，尝试等待更多内容加载...")
                time.sleep(10)
                
                # 再次检查
                page_text = driver.find_element("tag name", "body").text
                if "暂无数据" in page_text:
                    print("⚠️  页面仍然显示'暂无数据'，尝试刷新页面...")
                    driver.refresh()
                    time.sleep(15)
                    
                    # 检查是否有日期选择器或其他控件
                    try:
                        # 尝试查找日期选择器
                        date_inputs = driver.find_elements("css selector", "input[type='date'], input[placeholder*='日期'], input[placeholder*='时间']")
                        if date_inputs:
                            print(f"📅 找到 {len(date_inputs)} 个日期选择器")
                            # 尝试选择一个最近的日期
                            for date_input in date_inputs:
                                try:
                                    # 设置日期为今天
                                    from datetime import datetime
                                    today = datetime.now().strftime("%Y-%m-%d")
                                    driver.execute_script("arguments[0].value = arguments[1];", date_input, today)
                                    print(f"📅 设置日期为: {today}")
                                    break
                                except:
                                    continue
                    except:
                        pass
                    
                    # 尝试查找搜索按钮
                    try:
                        search_buttons = driver.find_elements("css selector", "button:contains('搜索'), button:contains('查询'), button:contains('Search')")
                        if search_buttons:
                            print("🔍 找到搜索按钮，尝试点击...")
                            search_buttons[0].click()
                            time.sleep(5)
                    except:
                        pass
                    
            else:
                print("✅ 页面内容正常加载")
                
        except Exception as e:
            print(f"❌ 检查页面状态失败: {e}")
        
        # 尝试多种方法获取认证信息
        auth_code, member_id = None, None
        
        # 方法1: 从JavaScript监听器获取
        print("🔍 方法1: 检查JavaScript监听器结果...")
        try:
            result = driver.execute_script("return window.authInfo;")
            if result:
                auth_code = result.get('authCode')
                member_id = result.get('memberId')
                
                if auth_code:
                    print(f"🔑 从监听器获取到authorization: {auth_code}")
                if member_id:
                    print(f"🆔 从监听器获取到member_id: {member_id}")
                    
        except Exception as e:
            print(f"❌ 获取监听器结果失败: {e}")
        
        # 方法2: 如果方法1失败，尝试从网络日志获取
        if not auth_code or not member_id:
            print("🔍 方法2: 从网络日志获取...")
            try:
                logs = driver.get_log('performance')
                print(f"📊 捕获到 {len(logs)} 条网络请求记录")
                
                for i, log in enumerate(logs):
                    try:
                        message = json.loads(log['message'])
                        if 'message' in message and message['message']['method'] == 'Network.requestWillBeSent':
                            request = message['message']['params']['request']
                            url = request.get('url', '')
                            headers = request.get('headers', {})
                            
                            # 特别关注包含 'add' 或 'tracking' 的请求
                            if 'add' in url.lower() or 'tracking' in url.lower():
                                print(f"🎯 发现相关请求 [{i+1}/{len(logs)}]: {url}")
                                print(f"   请求头: {list(headers.keys())}")
                                
                                # 检查各种可能的认证字段
                                if 'authorization' in headers:
                                    auth_code = headers['authorization']
                                    print(f"🔑 获取到authorization: {auth_code}")
                                
                                if 'member_id' in headers:
                                    member_id = headers['member_id']
                                    print(f"🆔 获取到member_id: {member_id}")
                                
                                if 'member-id' in headers:
                                    member_id = headers['member-id']
                                    print(f"🆔 获取到member-id: {member_id}")
                                
                                if 'x-member-id' in headers:
                                    member_id = headers['x-member-id']
                                    print(f"🆔 获取到x-member-id: {member_id}")
                                
                                if auth_code and member_id:
                                    print("✅ 从网络日志获取到完整认证信息")
                                    break
                        
                        # 每处理100条记录显示进度
                        if (i + 1) % 100 == 0:
                            print(f"📈 已处理 {i + 1}/{len(logs)} 条记录...")
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"❌ 获取网络日志失败: {e}")
        
        # 方法3: 如果方法2失败，尝试从localStorage获取
        if not auth_code or not member_id:
            print("🔍 方法3: 尝试从localStorage获取认证信息...")
            try:
                auth_code = driver.execute_script("return localStorage.getItem('auth_code') || localStorage.getItem('authorization') || localStorage.getItem('token');")
                member_id = driver.execute_script("return localStorage.getItem('member_id') || localStorage.getItem('user_id');")
                
                if auth_code:
                    print(f"🔑 从localStorage获取到认证信息: {auth_code}")
                if member_id:
                    print(f"🆔 从localStorage获取到用户ID: {member_id}")
                    
            except Exception as e:
                print(f"❌ 从localStorage获取失败: {e}")
        
        # 方法4: 如果方法3失败，尝试从sessionStorage获取
        if not auth_code or not member_id:
            print("🔍 方法4: 尝试从sessionStorage获取认证信息...")
            try:
                auth_code = driver.execute_script("return sessionStorage.getItem('auth_code') || sessionStorage.getItem('authorization') || sessionStorage.getItem('token');")
                member_id = driver.execute_script("return sessionStorage.getItem('member_id') || sessionStorage.getItem('user_id');")
                
                if auth_code:
                    print(f"🔑 从sessionStorage获取到认证信息: {auth_code}")
                if member_id:
                    print(f"🆔 从sessionStorage获取到用户ID: {member_id}")
                    
            except Exception as e:
                print(f"❌ 从sessionStorage获取失败: {e}")
        
        # 方法5: 如果方法4失败，尝试从cookie获取
        if not auth_code or not member_id:
            print("🔍 方法5: 尝试从cookie获取认证信息...")
            try:
                cookies = driver.get_cookies()
                for cookie in cookies:
                    if 'auth' in cookie['name'].lower() or 'token' in cookie['name'].lower():
                        auth_code = cookie['value']
                        print(f"🔑 从cookie获取到认证信息: {auth_code}")
                    if 'member' in cookie['name'].lower() or 'user' in cookie['name'].lower():
                        member_id = cookie['value']
                        print(f"🆔 从cookie获取到用户ID: {member_id}")
                        
            except Exception as e:
                print(f"❌ 从cookie获取失败: {e}")
        
        # 如果仍然没有获取到，尝试手动触发一些操作
        if not auth_code or not member_id:
            print("🔍 方法6: 尝试手动触发网络请求...")
            try:
                # 刷新页面
                print("🔄 刷新页面...")
                driver.refresh()
                time.sleep(15)
                
                # 再次检查JavaScript监听器结果
                result = driver.execute_script("return window.authInfo;")
                if result:
                    if not auth_code and result.get('authCode'):
                        auth_code = result['authCode']
                        print(f"🔑 刷新后从监听器获取到authorization: {auth_code}")
                    if not member_id and result.get('memberId'):
                        member_id = result['memberId']
                        print(f"🆔 刷新后从监听器获取到member_id: {member_id}")
                
                # 如果还是没有，再次获取网络日志
                if not auth_code or not member_id:
                    logs = driver.get_log('performance')
                    print(f"📊 刷新后捕获到 {len(logs)} 条网络请求记录")
                    
                    for log in logs:
                        try:
                            message = json.loads(log['message'])
                            if 'message' in message and message['message']['method'] == 'Network.requestWillBeSent':
                                request = message['message']['params']['request']
                                url = request.get('url', '')
                                headers = request.get('headers', {})
                                
                                if 'authorization' in headers:
                                    auth_code = headers['authorization']
                                    print(f"🔑 刷新后获取到authorization: {auth_code}")
                                
                                if 'member_id' in headers:
                                    member_id = headers['member_id']
                                    print(f"🆔 刷新后获取到member_id: {member_id}")
                                
                                if auth_code and member_id:
                                    break
                        except:
                            continue
                        
            except Exception as e:
                print(f"❌ 手动触发请求失败: {e}")
        
        # 方法7: 如果方法6失败，尝试访问其他页面
        if not auth_code or not member_id:
            print("🔍 方法7: 尝试访问其他页面获取认证信息...")
            try:
                # 尝试访问个人中心或其他可能包含用户信息的页面
                other_pages = [
                    "https://v2-eapp.delicloud.com/checkin2/web/checkIn/index",  # 打卡首页
                    "https://v2-eapp.delicloud.com/checkin2/web/checkIn/statistics",  # 统计页面
                    "https://v2-eapp.delicloud.com/checkin2/web/user/profile",  # 用户资料
                    "https://v2-eapp.delicloud.com/checkin2/web/user/settings",  # 用户设置
                ]
                
                for page_url in other_pages:
                    try:
                        print(f"🌐 尝试访问: {page_url}")
                        driver.get(page_url)
                        time.sleep(10)
                        
                        # 检查JavaScript监听器结果
                        result = driver.execute_script("return window.authInfo;")
                        if result:
                            if not auth_code and result.get('authCode'):
                                auth_code = result['authCode']
                                print(f"🔑 从 {page_url} 获取到authorization: {auth_code}")
                            if not member_id and result.get('memberId'):
                                member_id = result['memberId']
                                print(f"🆔 从 {page_url} 获取到member_id: {member_id}")
                        
                        if auth_code and member_id:
                            print(f"✅ 从 {page_url} 获取到完整认证信息")
                            break
                            
                    except Exception as e:
                        print(f"❌ 访问 {page_url} 失败: {e}")
                        continue
                        
            except Exception as e:
                print(f"❌ 访问其他页面失败: {e}")
        
        # 方法8: 如果方法7失败，尝试从当前页面的所有请求中查找
        if not auth_code or not member_id:
            print("🔍 方法8: 分析所有网络请求...")
            try:
                # 获取所有网络日志
                all_logs = driver.get_log('performance')
                print(f"📊 分析所有 {len(all_logs)} 条网络请求记录...")
                
                for i, log in enumerate(all_logs):
                    try:
                        message = json.loads(log['message'])
                        if 'message' in message and message['message']['method'] == 'Network.requestWillBeSent':
                            request = message['message']['params']['request']
                            url = request.get('url', '')
                            headers = request.get('headers', {})
                            
                            # 检查所有包含认证信息的请求
                            if 'authorization' in headers:
                                auth_code = headers['authorization']
                                print(f"🔑 从请求 [{i+1}] 获取到authorization: {auth_code}")
                            
                            if 'member_id' in headers:
                                member_id = headers['member_id']
                                print(f"🆔 从请求 [{i+1}] 获取到member_id: {member_id}")
                            
                            if 'member-id' in headers:
                                member_id = headers['member-id']
                                print(f"🆔 从请求 [{i+1}] 获取到member-id: {member_id}")
                            
                            if 'x-member-id' in headers:
                                member_id = headers['x-member-id']
                                print(f"🆔 从请求 [{i+1}] 获取到x-member-id: {member_id}")
                            
                            if auth_code and member_id:
                                print("✅ 从所有请求中获取到完整认证信息")
                                break
                        
                        # 每处理200条记录显示进度
                        if (i + 1) % 200 == 0:
                            print(f"📈 已处理 {i + 1}/{len(all_logs)} 条记录...")
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"❌ 分析所有网络请求失败: {e}")
        
        # 方法9: 如果方法8失败，尝试模拟用户操作
        if not auth_code or not member_id:
            print("🔍 方法9: 尝试模拟用户操作...")
            try:
                # 尝试查找并点击一些按钮来触发网络请求
                print("🔍 查找可点击的元素...")
                
                # 查找按钮
                buttons = driver.find_elements("tag name", "button")
                print(f"🔘 找到 {len(buttons)} 个按钮")
                
                for i, button in enumerate(buttons[:10]):  # 只尝试前10个按钮
                    try:
                        button_text = button.text.strip()
                        if button_text and len(button_text) < 20:  # 避免点击太长的文本
                            print(f"🔘 尝试点击按钮 [{i+1}]: {button_text}")
                            button.click()
                            time.sleep(3)
                            
                            # 检查JavaScript监听器结果
                            result = driver.execute_script("return window.authInfo;")
                            if result:
                                if not auth_code and result.get('authCode'):
                                    auth_code = result['authCode']
                                    print(f"🔑 点击按钮后获取到authorization: {auth_code}")
                                if not member_id and result.get('memberId'):
                                    member_id = result['memberId']
                                    print(f"🆔 点击按钮后获取到member_id: {member_id}")
                            
                            if auth_code and member_id:
                                print("✅ 通过模拟用户操作获取到完整认证信息")
                                break
                                
                    except Exception as e:
                        continue
                
                # 如果按钮点击没有效果，尝试查找链接
                if not auth_code or not member_id:
                    print("🔍 查找可点击的链接...")
                    links = driver.find_elements("tag name", "a")
                    print(f"🔗 找到 {len(links)} 个链接")
                    
                    for i, link in enumerate(links[:5]):  # 只尝试前5个链接
                        try:
                            link_text = link.text.strip()
                            if link_text and len(link_text) < 30:
                                print(f"🔗 尝试点击链接 [{i+1}]: {link_text}")
                                link.click()
                                time.sleep(3)
                                
                                # 检查JavaScript监听器结果
                                result = driver.execute_script("return window.authInfo;")
                                if result:
                                    if not auth_code and result.get('authCode'):
                                        auth_code = result['authCode']
                                        print(f"🔑 点击链接后获取到authorization: {auth_code}")
                                    if not member_id and result.get('memberId'):
                                        member_id = result['memberId']
                                        print(f"🆔 点击链接后获取到member_id: {member_id}")
                                
                                if auth_code and member_id:
                                    print("✅ 通过点击链接获取到完整认证信息")
                                    break
                                    
                        except Exception as e:
                            continue
                            
            except Exception as e:
                print(f"❌ 模拟用户操作失败: {e}")
        
        return auth_code, member_id
        
    finally:
        if driver:
            print("🔄 正在关闭浏览器...")
            try:
                driver.quit()
            except:
                pass

def update_config(auth_code, member_id):
    """更新配置文件"""
    if not auth_code or not member_id:
        print("❌ 认证信息不完整，无法更新配置文件")
        print(f"   AUTH_CODE: {auth_code}")
        print(f"   AUTH_ID: {member_id}")
        return False
    
    try:
        # 直接读取文件内容进行字符串替换
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
    print("得力e+系统认证信息获取工具 - 工作版")
    print("=" * 50)
    
    if not os.path.exists("Constant.ini"):
        print("❌ 未找到 Constant.ini 配置文件")
        print("请确保脚本与配置文件在同一目录下")
        return
    
    auth_code, member_id = get_auth_info()
    
    if auth_code and member_id:
        if update_config(auth_code, member_id):
            print("\n🎉 认证信息获取和更新完成！")
            print("\n🎯 使用说明：")
            print("1. 脚本已自动更新 Constant.ini 文件")
            print("2. 现在可以使用更新后的认证信息进行考勤统计")
            print("3. 如果认证信息过期，请重新运行此脚本")
        else:
            print("❌ 更新配置文件失败")
    else:
        print("\n💡 故障排除建议：")
        print("1. 确保Chrome浏览器已安装")
        print("2. 确保chromedriver-win64文件夹在项目目录中")
        print("3. 确保网络连接正常")
        print("4. 手动完成登录后重新运行脚本")
        print("5. 检查浏览器开发者工具中的网络请求")
        print("6. 尝试在登录成功后多等待一段时间再运行脚本")

if __name__ == "__main__":
    main()
