#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟登录获取认证信息（含弹窗自动处理）
增强：从 performance 日志中稳健解析 add 请求，优先提取 Authorization 与 member_id
保存 debug 文件以便人工排查
"""

import os
import sys
import time
import json
import re
import tempfile
import traceback
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException
)

# ----------------------
# 配置（根据需要修改）
# ----------------------
CHROMEDRIVER_PATH = "./chromedriver-win64/chromedriver.exe"  # <- 修改为您的 chromedriver 路径
CONSTANT_INI_PATH = "Constant.ini"                            # <- 修改为您的配置文件路径（通常无需改动）
LOGIN_URL = "https://v2-web.delicloud.com/login"              # 登录 URL，可酌情修改
MAX_LOGIN_WAIT = 300  # seconds
TARGET_CHECKIN_RULE_PART = "/checkIn/rule"  # 识别目标页面的 URL 片段
# ----------------------

def setup_driver(chromedriver_path=CHROMEDRIVER_PATH):
    """设置并启动 Chrome 浏览器驱动，返回 driver（失败返回 None）"""
    try:
        print("[setup_driver] 正在配置 Chrome 浏览器...")
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--remote-debugging-port=0")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")

        temp_dir = tempfile.mkdtemp(prefix="chrome_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        print(f"[setup_driver] 使用临时用户数据目录: {temp_dir}")

        # 启用 performance 日志
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        if not os.path.exists(chromedriver_path):
            print(f"[setup_driver] ChromeDriver 不存在: {chromedriver_path}")
            return None

        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("[setup_driver] Chrome 浏览器启动成功")
        return driver

    except Exception as e:
        print(f"[setup_driver] 启动 Chrome 失败: {e}")
        traceback.print_exc()
        return None

# ----------------------
# 基础辅助函数
# ----------------------
def wait_for_element(driver, by, value, timeout=10, description=""):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except Exception as e:
        print(f"[wait_for_element] 等待元素失败 ({description}): {e}")
        return None

def close_ant_modal_if_present(driver, timeout=3):
    """
    检测并尝试关闭 Ant Design 弹窗（ant-modal-wrap）。
    返回 True 如果发现并关闭了弹窗，False 否则。
    """
    modal_wrapper_xpath = "//div[contains(@class, 'ant-modal-wrap') and not(contains(@style,'display: none'))]"
    try:
        modal = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, modal_wrapper_xpath))
        )
    except TimeoutException:
        return False

    try:
        candidates = [
            "//button[contains(@class,'ant-modal-close')]",
            "//button[contains(@class,'ant-modal-close-x')]",
            "//button[contains(@class,'ant-btn') and (contains(., '确') or contains(., '取') or contains(., '取消') or contains(., '关闭'))]",
            "//span[contains(@class,'ant-modal-close-x')]/..",
            "//div[contains(@class,'ant-modal-footer')]//button"
        ]
        for xp in candidates:
            try:
                btn = driver.find_element(By.XPATH, xp)
                if btn and btn.is_displayed():
                    print(f"[close_ant_modal_if_present] 找到关闭按钮, 点击: {xp}")
                    driver.execute_script("arguments[0].click();", btn)
                    WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.XPATH, modal_wrapper_xpath)))
                    print("[close_ant_modal_if_present] 弹窗已关闭（通过关闭按钮）")
                    return True
            except Exception:
                continue

        try:
            overlay = driver.find_element(By.XPATH, modal_wrapper_xpath)
            driver.execute_script("arguments[0].click();", overlay)
            WebDriverWait(driver, 3).until(EC.invisibility_of_element_located((By.XPATH, modal_wrapper_xpath)))
            print("[close_ant_modal_if_present] 弹窗已关闭（通过 overlay）")
            return True
        except Exception:
            pass

    except Exception as e:
        print(f"[close_ant_modal_if_present] 关闭弹窗异常: {e}")
        traceback.print_exc()

    return False

def safe_click_element(driver, by, value, description="", wait_timeout=15, max_retries=3):
    """
    更健壮的点击：等待元素可点击；若点击被拦截则尝试关闭 modal 后重试。
    """
    attempt = 0
    last_exc = None
    while attempt < max_retries:
        attempt += 1
        try:
            el = WebDriverWait(driver, wait_timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            try:
                el.click()
                time.sleep(0.25)
                print(f"[safe_click_element] 成功点击 ({description}) (尝试 {attempt})")
                return True
            except ElementClickInterceptedException as e:
                last_exc = e
                print(f"[safe_click_element] 点击被拦截 ({description}), 尝试关闭弹窗并重试 (尝试 {attempt})")
                closed = close_ant_modal_if_present(driver, timeout=3)
                if not closed:
                    try:
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(0.25)
                        print(f"[safe_click_element] 使用 JS 点击成功 ({description})")
                        return True
                    except Exception as e2:
                        last_exc = e2
                        time.sleep(0.5)
                        continue
                else:
                    time.sleep(0.3)
                    continue

        except (TimeoutException, StaleElementReferenceException, WebDriverException) as e:
            last_exc = e
            print(f"[safe_click_element] 等待/定位异常 ({description}) (尝试 {attempt}): {e}")
            time.sleep(0.5)
            continue

    print(f"[safe_click_element] 无法点击 {description}（尝试 {max_retries} 次） - 最后异常: {last_exc}")
    return False

# ----------------------
# 新增：从 performance 日志中解析 Authorization 和 member_id
# ----------------------
def extract_auth_and_member_from_request_obj(request_obj):
    """
    从 Network.requestWillBeSent 的 request 对象（已解析 JSON）中提取 authorization 与 member_id。
    返回 (auth, member_id)（缺失项为 None）。
    """
    auth = None
    member = None

    headers = request_obj.get('headers', {}) or {}
    # Headers keys 大小写不敏感，优先寻找包含 'auth' 的 header 以及包含 'member' 的 header
    for k, v in headers.items():
        if not v:
            continue
        kl = k.lower()
        if 'auth' in kl and not auth:
            auth = v
        if 'member' in kl and not member:
            member = v

    # 如果 headers 没有，尝试从 URL query 中提取 member_id
    url = request_obj.get('url', '') or ''
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        # 常见 key: member_id, memberId, memberid, member
        for key in ['member_id', 'memberId', 'memberid', 'member']:
            if key in qs and qs[key]:
                if not member:
                    member = qs[key][0]
    except Exception:
        pass

    # 尝试解析 postData（可能是 JSON 字符串），从中提取 authorization/member_id
    postData = request_obj.get('postData') or ''
    if postData and (not auth or not member):
        # 尝试把 postData 当成 JSON 解析
        try:
            pdj = json.loads(postData)
            # 搜索键名
            def search_dict_for_keys(d, keys):
                if isinstance(d, dict):
                    for k, v in d.items():
                        kl = str(k).lower()
                        if any(kx.lower() in kl for kx in keys):
                            return v
                        else:
                            res = search_dict_for_keys(v, keys)
                            if res is not None:
                                return res
                elif isinstance(d, list):
                    for it in d:
                        res = search_dict_for_keys(it, keys)
                        if res is not None:
                            return res
                return None
            if not auth:
                a = search_dict_for_keys(pdj, ['auth', 'authorization', 'token'])
                if a:
                    auth = a
            if not member:
                m = search_dict_for_keys(pdj, ['member', 'member_id', 'memberId', 'memberid'])
                if m:
                    member = m
        except Exception:
            # 作为兜底，用正则在原始字符串中查找
            if not auth:
                m = re.search(r'["\']?(authorization|auth|token)["\']?\s*[:=]\s*["\']([^"\']{5,})["\']', postData, re.IGNORECASE)
                if m:
                    auth = m.group(2)
            if not member:
                m2 = re.search(r'["\']?(member_id|memberId|memberid|member)["\']?\s*[:=]\s*["\']([^"\']{1,})["\']', postData, re.IGNORECASE)
                if m2:
                    member = m2.group(2)

    return auth, member

def parse_performance_logs_for_auth(driver, lookback_seconds=120):
    """
    从 driver.get_log('performance') 中搜索包含 'add' 的请求，按时间倒序解析 Authorization 与 member_id。
    lookback_seconds: 向前搜索最近多少秒的日志（若无法从日志获取时间戳，就搜索全部）。
    返回 (auth, member_id) 或 (None, None)
    """
    try:
        raw_logs = []
        try:
            raw_logs = driver.get_log('performance')
        except Exception as e:
            print("[parse_performance_logs_for_auth] 无法获取 performance 日志:", e)
            return None, None

        print(f"[parse_performance_logs_for_auth] 共捕获到 {len(raw_logs)} 条 performance 日志，开始解析...")

        candidates = []  # 每项为 (index, request_obj, raw_message)
        for i, entry in enumerate(raw_logs):
            try:
                msg = json.loads(entry.get('message', '{}'))
                # 我们关注 Network.requestWillBeSent (请求发送) 事件
                if msg.get('message', {}).get('method') == 'Network.requestWillBeSent':
                    params = msg['message']['params']
                    request = params.get('request', {})
                    url = request.get('url', '') or ''
                    low = url.lower()
                    # 优先选择 URL 中包含 'add' 或 '/add' 或 'attendance' 的请求作为候选
                    if 'add' in low or '/add' in low or 'attendance' in low or 'punch' in low or 'clock' in low:
                        candidates.append((i, request, entry.get('message')))
            except Exception:
                continue

        # 若没有候选，则也收集部分 /api/ 请求作为备选
        if not candidates:
            for i, entry in enumerate(raw_logs):
                try:
                    msg = json.loads(entry.get('message', '{}'))
                    if msg.get('message', {}).get('method') == 'Network.requestWillBeSent':
                        request = msg['message']['params'].get('request', {})
                        url = request.get('url', '') or ''
                        low = url.lower()
                        if '/api/' in low or 'checkin' in low or 'tracking' in low:
                            candidates.append((i, request, entry.get('message')))
                except Exception:
                    continue

        print(f"[parse_performance_logs_for_auth] 找到 {len(candidates)} 个候选请求，按倒序优先检查最近的...")

        # 检查候选，优先从后向前（较新的先）
        for idx, req_obj, raw_msg in reversed(candidates):
            try:
                url = req_obj.get('url', '')
                print(f"[parse_performance_logs_for_auth] 解析候选请求: idx={idx}, url={url}")
                auth, member = extract_auth_and_member_from_request_obj(req_obj)
                if auth:
                    print(f"  -> 从 headers/postData/url 提取到 Authorization: {auth}")
                if member:
                    print(f"  -> 从 headers/postData/url 提取到 member_id: {member}")
                if auth and member:
                    return auth, member
            except Exception as e:
                print("[parse_performance_logs_for_auth] 解析单条请求时异常:", e)
                continue

        # 如果走到这里仍未找到，则把若干可疑请求写到 debug 文件供人工查看
        debug_file = 'debug_possible_requests.json'
        dump_list = []
        for idx, req_obj, raw_msg in candidates[:200]:
            dump_list.append({
                'index': idx,
                'url': req_obj.get('url'),
                'method': req_obj.get('method'),
                'headers_sample': {k: ('<redacted>' if 'cookie' in k.lower() else v) for k, v in (req_obj.get('headers') or {}).items()},
                'postData_preview': (req_obj.get('postData')[:300] + '...') if req_obj.get('postData') else None
            })
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(dump_list, f, ensure_ascii=False, indent=2)
            print(f"[parse_performance_logs_for_auth] 未匹配到完整 auth/member，已将 {len(dump_list)} 条候选写入 {debug_file}")
        except Exception as e:
            print("[parse_performance_logs_for_auth] 写 debug 文件失败:", e)

        return None, None

    except Exception as e:
        print("[parse_performance_logs_for_auth] 异常:", e)
        traceback.print_exc()
        return None, None

# ----------------------
# 其余流程保持与之前版本一致
# ----------------------
def handle_checkin_rule_page(driver, timeout_for_url=15):
    """
    当 driver 已经导航到包含 /checkIn/rule 的页面时：
    - 刷新页面
    - 关闭 modal（如果有）
    - 先点击 '考勤数据' -> 再点击 '打卡记录'
    返回 True/False 表示是否成功点击到 打卡记录
    """
    start = time.time()
    while time.time() - start < timeout_for_url:
        try:
            cur = driver.current_url
            if TARGET_CHECKIN_RULE_PART in cur:
                print(f"[handle_checkin_rule_page] 检测到目标 URL: {cur}")
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        print("[handle_checkin_rule_page] 超时：未检测到目标 URL")
        return False

    try:
        print("[handle_checkin_rule_page] 刷新页面...")
        driver.refresh()
        time.sleep(2.0)
    except Exception as e:
        print("[handle_checkin_rule_page] 刷新页面异常:", e)

    close_ant_modal_if_present(driver, timeout=3)

    attendance_data_xpaths = [
        "//span[contains(text(),'考勤数据')]/..",
        "//a[.//span[contains(text(),'考勤数据')]]",
        "//button[normalize-space(.)='考勤数据']",
        "//*[contains(text(),'考勤数据')]"
    ]

    clicked_attendance_data = False
    for xp in attendance_data_xpaths:
        print(f"[handle_checkin_rule_page] 尝试点击 '考勤数据' -> {xp}")
        if safe_click_element(driver, By.XPATH, xp, "考勤数据", wait_timeout=8):
            clicked_attendance_data = True
            time.sleep(1.0)
            print("[handle_checkin_rule_page] '考勤数据' 已点击")
            break
        time.sleep(0.4)

    punch_record_xpaths = [
        "//span[contains(text(),'打卡记录')]/..",
        "//a[.//span[contains(text(),'打卡记录')]]",
        "//button[normalize-space(.)='打卡记录']",
        "//*[contains(text(),'打卡记录')]"
    ]

    clicked_punch = False
    for xp in punch_record_xpaths:
        print(f"[handle_checkin_rule_page] 尝试点击 '打卡记录' -> {xp}")
        if safe_click_element(driver, By.XPATH, xp, "打卡记录", wait_timeout=8):
            clicked_punch = True
            time.sleep(1.0)
            print("[handle_checkin_rule_page] '打卡记录' 已点击")
            break
        time.sleep(0.4)

    if not clicked_punch:
        try:
            driver.save_screenshot('debug_no_punch_record.png')
            with open('debug_attendance_page_after_refresh.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass

    return clicked_punch

def get_auth_from_add_requests():
    """
    主流程：登录 -> 点击综合签到 -> 点击考勤管理 -> 进入 checkIn/rule -> 点击考勤数据/打卡记录 -> 解析日志获取 Authorization & member_id
    """
    driver = None
    auth_code = None
    member_id = None

    try:
        print("[main] 启动浏览器...")
        driver = setup_driver()
        if not driver:
            return None, None

        print(f"[main] 打开登录页面: {LOGIN_URL}")
        driver.get(LOGIN_URL)

        print("[main] 等待登录（扫码）...")
        start_time = time.time()
        while time.time() - start_time < MAX_LOGIN_WAIT:
            try:
                cur = driver.current_url
                if "login" not in cur:
                    print("[main] 登录成功，当前 URL:", cur)
                    break
                time.sleep(2)
            except Exception:
                time.sleep(2)
        else:
            print("[main] 登录超时")
            return None, None

        print("[main] 登录后刷新页面...")
        time.sleep(1.5)
        driver.refresh()
        time.sleep(3)

        # 步骤1: 点击 综合签到（重试候选）
        print("\n[步骤1] 点击 综合签到 ...")
        sign_buttons = [
            ("//button[contains(@class, 'dashboard_btn') and .//span[contains(text(), '综合签到')]]", "综合签到(button dashboard_btn)"),
            ("//button[contains(@class, 'ant-btn') and .//span[contains(text(), '综合签到')]]", "综合签到(button ant-btn)"),
            ("//span[contains(text(), '综合签到')]/..", "综合签到 span 父元素"),
            ("//*[contains(text(), '综合签到')]", "综合签到 任意元素")
        ]
        sign_clicked = False
        for xpath, desc in sign_buttons:
            print(f"[步骤1] 尝试: {desc} -> {xpath}")
            if safe_click_element(driver, By.XPATH, xpath, desc, wait_timeout=8):
                sign_clicked = True
                break
            time.sleep(0.5)

        # 步骤2: 点击 综合签到内的精确按钮 (可选)
        print("\n[步骤2] 尝试点击精确位置按钮 /html/body/div/section/div/div/div[2]/div/button[3] ...")
        specific_button_xpath = "/html/body/div/section/div/div/div[2]/div/button[3]"
        if safe_click_element(driver, By.XPATH, specific_button_xpath, "精确位置按钮(button[3])", wait_timeout=6):
            print("[步骤2] 精确位置按钮 点击成功")
        else:
            print("[步骤2] 精确位置按钮 未点击成功，继续")

        time.sleep(2)

        # 切换到新标签页（如果打开了）
        print("\n[标签页切换] 检查新标签页...")
        try:
            window_handles = driver.window_handles
            print("[标签页切换] window_handles:", window_handles)
            if len(window_handles) > 1:
                driver.switch_to.window(window_handles[-1])
                print("[标签页切换] 已切换到最新标签页，URL:", driver.current_url)
                time.sleep(0.5)
                close_ant_modal_if_present(driver, timeout=2)
            else:
                print("[标签页切换] 只有一个窗口，继续在当前页面操作")
        except Exception as e:
            print("[标签页切换] 切换标签页异常:", e)

        # 步骤3: 点击 考勤管理（尝试文本定位与 header 位置）
        print("\n[步骤3] 尝试点击 考勤管理 ...")
        attendance_clicked = False
        attendance_button_xpath = "//li[contains(@class, 'ant-menu-item')]//span[text()='考勤管理']"
        if safe_click_element(driver, By.XPATH, attendance_button_xpath, "考勤管理(文本定位)", wait_timeout=12):
            attendance_clicked = True
        else:
            header_li_xpath = "/html/body/div/section/header/ul/li[6]"
            if safe_click_element(driver, By.XPATH, header_li_xpath, "header li[6]", wait_timeout=6):
                attendance_clicked = True
            else:
                try:
                    header_li_elements = driver.find_elements(By.XPATH, "//div/section/header/ul/li")
                    for i, li in enumerate(header_li_elements):
                        try:
                            txt = li.text.strip()
                            if txt and ("考勤" in txt or "管理" in txt):
                                driver.execute_script("arguments[0].scrollIntoView(true);", li)
                                try:
                                    driver.execute_script("arguments[0].click();", li)
                                    attendance_clicked = True
                                    break
                                except Exception:
                                    xp = f"//div/section/header/ul/li[contains(., '{txt}')]"
                                    if safe_click_element(driver, By.XPATH, xp, f"header li containing '{txt}'", wait_timeout=5):
                                        attendance_clicked = True
                                        break
                        except Exception:
                            continue
                except Exception:
                    pass

        if not attendance_clicked:
            print("[步骤3] 未能点击 考勤管理，保存调试信息...")
            try:
                driver.save_screenshot('debug_attendance_click_failed.png')
                with open('debug_attendance_page.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
            except Exception:
                pass

        # 如果已经或随后跳转到 checkIn/rule 页面，则刷新并点击考勤数据->打卡记录
        try:
            cur_url = driver.current_url
        except Exception:
            cur_url = ""

        clicked_punch = False
        if TARGET_CHECKIN_RULE_PART in cur_url:
            print("[主流程] 当前已在目标 checkIn/rule 页面，调用处理函数...")
            clicked_punch = handle_checkin_rule_page(driver, timeout_for_url=10)
        else:
            print("[主流程] 未在目标页面，等待短时跳转到目标 URL（最多 10s）...")
            start = time.time()
            while time.time() - start < 10:
                try:
                    cur = driver.current_url
                    if TARGET_CHECKIN_RULE_PART in cur:
                        print("[主流程] 发现页面跳转到目标 URL:", cur)
                        clicked_punch = handle_checkin_rule_page(driver, timeout_for_url=8)
                        break
                except Exception:
                    pass
                try:
                    for wh in driver.window_handles:
                        try:
                            driver.switch_to.window(wh)
                            if TARGET_CHECKIN_RULE_PART in driver.current_url:
                                print("[主流程] 在其它 tab 检测到目标 URL:", driver.current_url)
                                clicked_punch = handle_checkin_rule_page(driver, timeout_for_url=8)
                                break
                        except Exception:
                            continue
                    if clicked_punch:
                        break
                except Exception:
                    pass
                time.sleep(0.5)

        # ----------------------------
        # 步骤4: 解析 performance 日志以查找 Authorization & member_id
        # ----------------------------
        print("\n[步骤4] 解析 performance 日志寻找 Authorization 与 member_id ...")
        # 等待一小段时间让请求发出（如果刚点击可能会延迟）
        time.sleep(6)

        auth_code, member_id = parse_performance_logs_for_auth(driver, lookback_seconds=120)
        if auth_code and member_id:
            print("[步骤4] 成功解析到认证信息:")
            print("   Authorization:", auth_code)
            print("   member_id:", member_id)
            return auth_code, member_id
        else:
            print("[步骤4] 未解析到完整认证信息（auth/member），尝试再等一会并重试一次...")
            time.sleep(4)
            auth_code, member_id = parse_performance_logs_for_auth(driver, lookback_seconds=120)
            if auth_code and member_id:
                print("[步骤4] 重试成功解析到认证信息")
                return auth_code, member_id

        # 兜底：如果没拿到 auth，则返回 None 或默认值
        if not member_id:
            member_id = "46"
            print("[兜底] 未能获取 member_id，使用默认 member_id:", member_id)

        return auth_code, member_id

    finally:
        if driver:
            try:
                print("[main] 关闭浏览器...")
                driver.quit()
            except Exception:
                pass

# ----------------------
# 更新配置文件
# ----------------------
def update_config_file(auth_code, member_id, org_id=None, ini_path=CONSTANT_INI_PATH):
    """更新 Constant.ini（或其它配置文件），替换 AUTH_CODE, AUTH_ID, ORG_ID"""
    if not auth_code or not member_id:
        print("[update_config_file] 认证信息不完整，无法更新配置文件")
        return False
    try:
        with open(ini_path, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        content = re.sub(r"AUTH_CODE\s*=\s*'[^']*'", f"AUTH_CODE = '{auth_code}'", content)
        content = re.sub(r"AUTH_ID\s*=\s*'[^']*'", f"AUTH_ID = '{member_id}'", content)
        if org_id:
            content = re.sub(r"ORG_ID\s*=\s*'[^']*'", f"ORG_ID = '{org_id}'", content)

        with open(ini_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("[update_config_file] 配置文件更新成功")
        print("   AUTH_CODE:", auth_code)
        print("   AUTH_ID:", member_id)
        if org_id:
            print("   ORG_ID:", org_id)
        return True
    except Exception as e:
        print("[update_config_file] 更新配置文件失败:", e)
        traceback.print_exc()
        return False

# ----------------------
# 主入口
# ----------------------
def main():
    print("="*60)
    print("模拟登录获取认证信息（含从日志中解析 Authorization 与 member_id）")
    print("="*60)

    if not os.path.exists(CONSTANT_INI_PATH):
        print("❌ 未找到 Constant.ini 配置文件:", CONSTANT_INI_PATH)
        input("按 Enter 退出...")
        return

    if not os.path.exists(CHROMEDRIVER_PATH):
        print("❌ 未找到 ChromeDriver:", CHROMEDRIVER_PATH)
        input("按 Enter 退出...")
        return

    auth_code, member_id = get_auth_from_add_requests()

    if not auth_code or not member_id:
        print("❌ 获取认证信息失败（或部分缺失）")
        print("   auth_code:", auth_code)
        print("   member_id:", member_id)
        input("按 Enter 退出...")
        return

    print("[main] 成功获取认证信息，开始更新配置文件...")
    if update_config_file(auth_code, member_id):
        print("[main] 完成！")
    else:
        print("[main] 更新配置文件失败，请检查磁盘权限与文件格式")

    input("按 Enter 键退出...")

if __name__ == "__main__":
    main()
