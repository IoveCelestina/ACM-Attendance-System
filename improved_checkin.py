#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版：从 performance 日志中快速、稳健地提取 Authorization 与 member_id
主要改进点：
 1. 在解析 performance 日志时优先按时间倒序遍历（找到即返），避免无谓的遍历与 JSON.loads。
 2. 在大量日志中先用字符串判定 "Network.requestWillBeSent" 再做 JSON 解析，避免重复解析耗时。
 3. 使用预编译正则、快速字符串查找作为兜底，只有必要时才把 postData 当 JSON 解析。
 4. safe_click_element 增强：在正常 click 失败时先尝试 scrollIntoView、ActionChains、JS click；并在点击被遮挡时优先尝试关闭 modal / overlay。
 5. 减少 debug 文件与大数据写入，提供可选 verbose 模式。

使用说明：
 - 将 CHROMEDRIVER_PATH/CONSTANT_INI_PATH 调整为本机路径
 - 运行脚本，按提示扫码登录，脚本会尽量快速找到最近的 add/tracking 请求并解析 auth/member

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
from selenium.webdriver.common.action_chains import ActionChains

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
CHROMEDRIVER_PATH = "./chromedriver-win64/chromedriver.exe"
CONSTANT_INI_PATH = "Constant.ini"
LOGIN_URL = "https://v2-web.delicloud.com/login"
MAX_LOGIN_WAIT = 300  # seconds
TARGET_CHECKIN_RULE_PART = "/checkIn/rule"
VERBOSE = True  # 若为 False 将少打印并减少 debug 文件写入
# ----------------------

# 预编译正则（用于在 postData/raw 中快速抽取）
AUTH_RE = re.compile(r'["\']?(?:authorization|auth|token)["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-\._]{6,})', re.I)
MEMBER_RE = re.compile(r'["\']?(?:member_id|memberId|memberid|member)["\']?\s*[:=]\s*["\']?([0-9A-Za-z\-_]{1,})', re.I)
BEARER_RE = re.compile(r'Bearer\s+([A-Za-z0-9\-\._]+)', re.I)

# ----------------------
# 驱动设置
# ----------------------

def setup_driver(chromedriver_path=CHROMEDRIVER_PATH):
    try:
        if VERBOSE: print("[setup_driver] 正在配置 Chrome 浏览器...")
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--remote-debugging-port=0")

        temp_dir = tempfile.mkdtemp(prefix="chrome_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        if VERBOSE: print(f"[setup_driver] 使用临时用户数据目录: {temp_dir}")

        # 启用 performance 日志（注意：某些 chromedriver/chrome 版本收效不同）
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        if not os.path.exists(chromedriver_path):
            print(f"[setup_driver] ChromeDriver 不存在: {chromedriver_path}")
            return None

        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        if VERBOSE: print("[setup_driver] Chrome 浏览器启动成功")
        return driver

    except Exception as e:
        print(f"[setup_driver] 启动 Chrome 失败: {e}")
        traceback.print_exc()
        return None

# ----------------------
# 点击相关增强
# ----------------------

def close_ant_modal_if_present(driver, timeout=2):
    """尝试快速关闭常见的 Ant Modal 或遮罩，返回 True if closed."""
    modal_wrapper_xpath = "//div[contains(@class, 'ant-modal-wrap') and not(contains(@style,'display: none'))]"
    try:
        modal = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, modal_wrapper_xpath))
        )
    except TimeoutException:
        return False

    # 尝试几种关闭策略
    close_xpaths = [
        "//button[contains(@class,'ant-modal-close')]|//button[contains(@class,'ant-modal-close-x')]",
        "//div[contains(@class,'ant-modal-footer')]//button",
        "//button[contains(., '确') or contains(., '取') or contains(., '取消') or contains(., '关闭')]"
    ]
    for xp in close_xpaths:
        try:
            btns = driver.find_elements(By.XPATH, xp)
            for b in btns:
                if b.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", b)
                        WebDriverWait(driver, 2).until(EC.invisibility_of_element_located((By.XPATH, modal_wrapper_xpath)))
                        if VERBOSE: print(f"[close_ant_modal_if_present] 通过 {xp} 关闭弹窗")
                        return True
                    except Exception:
                        continue
        except Exception:
            continue

    # 如果上面没成功，尝试点击 overlay
    try:
        overlay = driver.find_element(By.XPATH, modal_wrapper_xpath)
        driver.execute_script("arguments[0].click();", overlay)
        WebDriverWait(driver, 1).until(EC.invisibility_of_element_located((By.XPATH, modal_wrapper_xpath)))
        if VERBOSE: print("[close_ant_modal_if_present] 通过 overlay 点击 关闭弹窗")
        return True
    except Exception:
        return False


def safe_click_element(driver, by, value, description="", wait_timeout=10, max_retries=3):
    """更健壮的点击：
    - 先等待 element_to_be_clickable
    - 如果 click 失败，尝试 scrollIntoView -> ActionChains -> JS click
    - 若被遮挡则尝试关闭 modal
    """
    attempt = 0
    last_exc = None
    while attempt < max_retries:
        attempt += 1
        try:
            el = WebDriverWait(driver, wait_timeout).until(
                EC.presence_of_element_located((by, value))
            )

            # 如果元素存在但不在可点击区域，先滚动并等待
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            except Exception:
                pass

            try:
                el.click()
                time.sleep(0.2)
                if VERBOSE: print(f"[safe_click_element] 成功点击 ({description}) (尝试 {attempt})")
                return True
            except ElementClickInterceptedException as e:
                last_exc = e
                if VERBOSE: print(f"[safe_click_element] 点击被拦截 ({description}), 尝试关闭弹窗并降级点击 (尝试 {attempt})")
                closed = close_ant_modal_if_present(driver, timeout=2)
                if closed:
                    time.sleep(0.2)
                    continue

                # 尝试 ActionChains 移动并点击
                try:
                    ActionChains(driver).move_to_element(el).pause(0.05).click(el).perform()
                    time.sleep(0.2)
                    if VERBOSE: print(f"[safe_click_element] ActionChains 点击成功 ({description})")
                    return True
                except Exception:
                    pass

                # JS 点击作为最后手段
                try:
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.2)
                    if VERBOSE: print(f"[safe_click_element] JS 点击成功 ({description})")
                    return True
                except Exception as e2:
                    last_exc = e2
                    time.sleep(0.2)
                    continue

        except (TimeoutException, StaleElementReferenceException, WebDriverException) as e:
            last_exc = e
            if VERBOSE: print(f"[safe_click_element] 等待/定位异常 ({description}) (尝试 {attempt}): {e}")
            time.sleep(0.3)
            continue

    if VERBOSE: print(f"[safe_click_element] 无法点击 {description}（尝试 {max_retries} 次） - 最后异常: {last_exc}")
    return False

# ----------------------
# 日志解析核心：高效查找 add/tracking 请求并抓取 auth/member
# ----------------------

def extract_auth_and_member_from_request_obj_fast(request_obj):
    """更快的解析逻辑：
    - 先从 headers（统一为小写 key map）中查找
    - 再从 URL query 中查找 member
    - 再在 postData 原始字符串中用正则快速匹配（避免 JSON.loads）
    - 只有当必要时才 JSON 解析 postData
    返回 (auth, member)
    """
    auth = None
    member = None

    headers = request_obj.get('headers') or {}
    if headers:
        # 构造小写键映射（避免对每个键做多次 lower）
        lmap = {k.lower(): v for k, v in headers.items() if v}
        for k, v in lmap.items():
            if not v:
                continue
            if ('auth' in k or 'authorization' in k or 'token' in k) and not auth:
                auth = v
            if ('member' in k) and not member:
                member = v

    # 从 URL query 中提取 member_id
    url = request_obj.get('url', '') or ''
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for key in ('member_id', 'memberId', 'memberid', 'member'):
            if key in qs and qs[key]:
                if not member:
                    member = qs[key][0]
    except Exception:
        pass

    postData = request_obj.get('postData') or ''
    if postData and (not auth or not member):
        # 先用正则快速查找
        if not auth:
            m = AUTH_RE.search(postData)
            if m:
                auth = m.group(1)
            else:
                m2 = BEARER_RE.search(postData)
                if m2:
                    auth = m2.group(1)
        if not member:
            mm = MEMBER_RE.search(postData)
            if mm:
                member = mm.group(1)

        # 仅当上述正则都没命中且 postData 看起来像 JSON 时再尝试 JSON 解析
        if (not auth or not member) and postData.strip().startswith('{') and len(postData) < 20000:
            try:
                pdj = json.loads(postData)
                # 递归查找工具（轻量）
                def search_dict_for_keys(d, keys):
                    if isinstance(d, dict):
                        for kk, vv in d.items():
                            kl = str(kk).lower()
                            if any(kx.lower() in kl for kx in keys):
                                return vv
                            else:
                                r = search_dict_for_keys(vv, keys)
                                if r is not None:
                                    return r
                    elif isinstance(d, list):
                        for it in d:
                            r = search_dict_for_keys(it, keys)
                            if r is not None:
                                return r
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
                pass

    # 清理 auth（去掉 Bearer 前缀等）
    if isinstance(auth, str):
        m = BEARER_RE.search(auth)
        if m:
            auth = m.group(1)
        auth = auth.strip()

    if isinstance(member, (int, float)):
        member = str(member)
    if isinstance(member, str):
        member = member.strip()

    return auth, member


def parse_performance_logs_for_auth(driver, lookback_seconds=120, max_candidates=500):
    """从 driver.get_log('performance') 中高效搜索包含 'add' 的请求，按时间倒序解析 Authorization 与 member_id。
    优化策略：
      - 只解析 message 字段包含 'Network.requestWillBeSent' 的条目
      - 按倒序遍历，遇到第一个同时有 auth/member 的请求立即返回
    返回 (auth, member) 或 (None, None)
    """
    try:
        try:
            raw_logs = driver.get_log('performance')
        except Exception as e:
            if VERBOSE: print("[parse_performance_logs_for_auth] 无法获取 performance 日志:", e)
            return None, None

        nlogs = len(raw_logs)
        if VERBOSE: print(f"[parse_performance_logs_for_auth] 共捕获到 {nlogs} 条 performance 日志，开始解析（倒序）...")

        candidates_checked = 0

        # 倒序遍历，优先处理最新的日志（常见场景：刚点击后不久会产生 add 请求）
        for entry in reversed(raw_logs):
            # 快速字符串判定，避免大量 json.loads
            msg_text = entry.get('message', '') or ''
            if 'Network.requestWillBeSent' not in msg_text:
                continue

            # 尝试 JSON 解析这一条消息（通常只有少量会被解析）
            try:
                msg = json.loads(msg_text)
            except Exception:
                continue

            # 解析 request 对象
            params = msg.get('message', {}).get('params', {})
            request = params.get('request') or {}
            url = request.get('url', '') or ''
            low = url.lower()

            # 只关注可能的目标请求（快速关键字过滤）
            if not any(k in low for k in ('/add', '/tracking', '/checkin', 'attendance', 'punch', 'clock', '/api/')):
                continue

            candidates_checked += 1
            if candidates_checked > max_candidates:
                if VERBOSE: print(f"[parse_performance_logs_for_auth] 已检查 {max_candidates} 个候选，停止以节约时间")
                break

            if VERBOSE: print(f"[parse_performance_logs_for_auth] 解析候选请求: url={url}")

            auth, member = extract_auth_and_member_from_request_obj_fast(request)
            if auth:
                if VERBOSE: print(f"  -> 解析到 Authorization: {auth}")
            if member:
                if VERBOSE: print(f"  -> 解析到 member_id: {member}")

            if auth and member:
                return auth, member

        # 如果未找到完整 auth+member，尝试只找到 auth 或 member 并返回部分结果
        # 我们再做一次更宽松的扫描（允许缺一项）
        if VERBOSE: print("[parse_performance_logs_for_auth] 未找到同时包含 auth 与 member 的请求，尝试宽松匹配（先返回 auth 或 member）")
        last_auth = None
        last_member = None
        for entry in reversed(raw_logs):
            msg_text = entry.get('message', '') or ''
            if 'Network.requestWillBeSent' not in msg_text:
                continue
            try:
                msg = json.loads(msg_text)
            except Exception:
                continue
            request = msg.get('message', {}).get('params', {}).get('request') or {}
            url = request.get('url', '') or ''
            low = url.lower()
            if not any(k in low for k in ('/add', '/tracking', '/checkin', 'attendance', 'punch', 'clock', '/api/')):
                continue
            a, m = extract_auth_and_member_from_request_obj_fast(request)
            if a and not last_auth:
                last_auth = a
            if m and not last_member:
                last_member = m
            if last_auth and last_member:
                return last_auth, last_member

        # 兜底写 debug（可控）
        if VERBOSE:
            debug_file = 'debug_possible_requests.json'
            dump_list = []
            for entry in reversed(raw_logs[-max_candidates:]):
                try:
                    msg_text = entry.get('message','') or ''
                    if 'Network.requestWillBeSent' not in msg_text:
                        continue
                    msg = json.loads(msg_text)
                    req = msg.get('message',{}).get('params',{}).get('request') or {}
                    dump_list.append({
                        'url': req.get('url'),
                        'method': req.get('method'),
                        'headers_sample': {k: ('<redacted>' if 'cookie' in k.lower() else v) for k, v in (req.get('headers') or {}).items()},
                        'postData_preview': (req.get('postData')[:400] + '...') if req.get('postData') else None
                    })
                except Exception:
                    continue
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(dump_list, f, ensure_ascii=False, indent=2)
                if VERBOSE: print(f"[parse_performance_logs_for_auth] 未匹配到完整 auth/member，已将 {len(dump_list)} 条候选写入 {debug_file}")
            except Exception:
                pass

        return last_auth, last_member

    except Exception as e:
        print("[parse_performance_logs_for_auth] 异常:", e)
        traceback.print_exc()
        return None, None

# ----------------------
# 其余流程保持一致，但对流程顺序/等待做了小优化
# ----------------------

def handle_checkin_rule_page(driver, timeout_for_url=15, max_refresh_attempts=2):
    """
    当 driver 已经导航到包含 /checkIn/rule 的页面时：
    - 尝试确保页面可交互（关闭 modal / overlay；必要时刷新）
    - 点击 '考勤数据' -> 再点击 '打卡记录'
    返回 True/False 表示是否成功点击到 打卡记录
    """
    start = time.time()
    while time.time() - start < timeout_for_url:
        try:
            cur = driver.current_url
            if TARGET_CHECKIN_RULE_PART in cur:
                if VERBOSE: print(f"[handle_checkin_rule_page] 检测到目标 URL: {cur}")
                break
        except Exception:
            pass
        time.sleep(0.3)
    else:
        if VERBOSE: print("[handle_checkin_rule_page] 超时：未检测到目标 URL")
        return False

    # ---- 确保页面可交互的子策略 ----
    def page_ready_check():
        """判断页面是否没有明显 modal/遮罩阻挡（返回 True/False）"""
        try:
            # 判断常见 ant-modal-wrap 是否存在且可见
            visible_modal = driver.execute_script(
                "return !!document.querySelector(\"div.ant-modal-wrap:not([style*='display: none']),"
                " div[class*='modal'][style*='display: block'], .el-dialog__wrapper:not([style*='display: none'])\");"
            )
            if visible_modal:
                if VERBOSE: print("[page_ready_check] 检测到 visible modal/overlay")
                return False
            # 也检查 document.readyState
            ready = driver.execute_script("return document.readyState")
            if ready != 'complete':
                if VERBOSE: print(f"[page_ready_check] document.readyState = {ready}")
                return False
            return True
        except Exception:
            return False

    # 若页面直接被 modal 阻挡：尝试关闭 modal，若无效则刷新后重试（最多 max_refresh_attempts 次）
    refresh_attempt = 0
    while refresh_attempt <= max_refresh_attempts:
        # 尝试关闭常见弹窗
        closed = False
        try:
            closed = close_ant_modal_if_present(driver, timeout=1)
        except Exception:
            closed = False

        if page_ready_check():
            if VERBOSE: print(f"[handle_checkin_rule_page] 页面可交互（refresh_attempt={refresh_attempt}, closed={closed})")
            break

        # 如果已经关闭但仍不 ready，再等待短时并重试一次
        if closed:
            time.sleep(0.5)
            if page_ready_check():
                break

        # 若未关闭或仍不 ready，刷新页面后等待并继续
        if refresh_attempt < max_refresh_attempts:
            try:
                if VERBOSE: print(f"[handle_checkin_rule_page] 页面仍被遮挡，刷新页面（第 {refresh_attempt+1} 次尝试）...")
                driver.refresh()
                time.sleep(1.0 + 0.4 * refresh_attempt)  # 逐步加长等待
            except Exception:
                pass
        refresh_attempt += 1

    # 最后兜底：如果检测到 modal 且普通关闭方法无效，可以尝试用 JS 将遮罩隐藏（**侵入性操作，慎用**）
    if not page_ready_check():
        if VERBOSE: print("[handle_checkin_rule_page] 最后兜底：尝试用 JS 隐藏可能的 overlay（侵入性）")
        try:
            driver.execute_script("""
            // 试图隐藏常见遮罩/弹窗容器，仅作为调试/兜底手段
            var sels = document.querySelectorAll('div.ant-modal-wrap, div[class*=\"modal\"], .el-dialog__wrapper, .v-modal, .mask, .overlay');
            sels.forEach(function(el){ try{ el.style.display='none'; el.remove(); }catch(e){} });
            // 同时尝试移除可能的阻挡层级样式
            var bod = document.body; if(bod){ bod.style.overflow='auto'; }
            """)
            time.sleep(0.4)
        except Exception:
            pass

    # small wait to let DOM settle
    time.sleep(0.4)

    # --- 下面是点击 '考勤数据' 与 '打卡记录' 的流程（同你原逻辑，但更宽容） ---
    attendance_data_xpaths = [
        "//span[contains(text(),'考勤数据')]/..",
        "//a[.//span[contains(text(),'考勤数据')]]",
        "//button[normalize-space(.)='考勤数据']",
        "//*[contains(text(),'考勤数据')]"
    ]

    clicked_attendance_data = False
    for xp in attendance_data_xpaths:
        if VERBOSE: print(f"[handle_checkin_rule_page] 尝试点击 '考勤数据' -> {xp}")
        if safe_click_element(driver, By.XPATH, xp, "考勤数据", wait_timeout=6, max_retries=4):
            clicked_attendance_data = True
            time.sleep(0.6)
            if VERBOSE: print("[handle_checkin_rule_page] '考勤数据' 已点击")
            break
        time.sleep(0.3)

    # 如果没有点击成功：记录快照并继续（不直接放弃）
    if not clicked_attendance_data:
        try:
            driver.save_screenshot('debug_attendance_click_failed_after_ready.png')
            with open('debug_attendance_page_after_ready.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass

    punch_record_xpaths = [
        "//span[contains(text(),'打卡记录')]/..",
        "//a[.//span[contains(text(),'打卡记录')]]",
        "//button[normalize-space(.)='打卡记录']",
        "//*[contains(text(),'打卡记录')]"
    ]

    clicked_punch = False
    for xp in punch_record_xpaths:
        if VERBOSE: print(f"[handle_checkin_rule_page] 尝试点击 '打卡记录' -> {xp}")
        # 注意：这里给更长的 wait_timeout，因为打卡记录可能是异步渲染出来的
        if safe_click_element(driver, By.XPATH, xp, "打卡记录", wait_timeout=8, max_retries=4):
            clicked_punch = True
            time.sleep(0.6)
            if VERBOSE: print("[handle_checkin_rule_page] '打卡记录' 已点击")
            break
        time.sleep(0.3)

    if not clicked_punch:
        try:
            driver.save_screenshot('debug_no_punch_record_after_ready.png')
            with open('debug_attendance_page_after_refresh.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass

    return clicked_punch



def get_auth_from_add_requests():
    driver = None
    auth_code = None
    member_id = None

    try:
        if VERBOSE: print("[main] 启动浏览器...")
        driver = setup_driver()
        if not driver:
            return None, None

        if VERBOSE: print(f"[main] 打开登录页面: {LOGIN_URL}")
        driver.get(LOGIN_URL)

        if VERBOSE: print("[main] 等待登录（扫码）...")
        start_time = time.time()
        while time.time() - start_time < MAX_LOGIN_WAIT:
            try:
                cur = driver.current_url
                if "login" not in cur:
                    if VERBOSE: print("[main] 登录成功，当前 URL:", cur)
                    break
                time.sleep(1.2)
            except Exception:
                time.sleep(1.2)
        else:
            print("[main] 登录超时")
            return None, None

        time.sleep(1.0)
        driver.refresh()
        time.sleep(1.2)

        # 步骤1: 点击 综合签到（快速候选）
        sign_buttons = [
            ("//span[contains(text(), '综合签到')]/..", "综合签到 span 父元素"),
            ("//button[contains(@class, 'ant-btn') and .//span[contains(text(), '综合签到')]]", "综合签到(button ant-btn)"),
            ("//*[contains(text(), '综合签到')]", "综合签到 任意元素")
        ]
        for xpath, desc in sign_buttons:
            if safe_click_element(driver, By.XPATH, xpath, desc, wait_timeout=6):
                break
            time.sleep(0.2)

        # 标签页切换（如果有）
        try:
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(0.3)
                close_ant_modal_if_present(driver, timeout=1)
        except Exception:
            pass

        # 点击 考勤管理（若存在）
        attendance_clicked = False
        attendance_button_xpath = "//li[contains(@class, 'ant-menu-item')]//span[text()='考勤管理']"
        if safe_click_element(driver, By.XPATH, attendance_button_xpath, "考勤管理(文本定位)", wait_timeout=6):
            attendance_clicked = True
        else:
            header_li_xpath = "/html/body/div/section/header/ul/li[6]"
            if safe_click_element(driver, By.XPATH, header_li_xpath, "header li[6]", wait_timeout=4):
                attendance_clicked = True

        # 若已在目标页面或跳转完成则点击考勤数据->打卡记录
        try:
            cur_url = driver.current_url
        except Exception:
            cur_url = ""

        clicked_punch = False
        if TARGET_CHECKIN_RULE_PART in cur_url:
            clicked_punch = handle_checkin_rule_page(driver, timeout_for_url=8)
        else:
            start = time.time()
            while time.time() - start < 8:
                try:
                    for wh in driver.window_handles:
                        driver.switch_to.window(wh)
                        if TARGET_CHECKIN_RULE_PART in driver.current_url:
                            clicked_punch = handle_checkin_rule_page(driver, timeout_for_url=6)
                            break
                    if clicked_punch:
                        break
                except Exception:
                    pass
                time.sleep(0.4)

        # 等待短时请求生成
        time.sleep(2.8)

        auth_code, member_id = parse_performance_logs_for_auth(driver, lookback_seconds=120)
        if auth_code and member_id:
            if VERBOSE: print("[main] 成功解析到认证信息:")
            if VERBOSE: print("   Authorization:", auth_code)
            if VERBOSE: print("   member_id:", member_id)
            return auth_code, member_id

        # 再等一小会并重试一次
        time.sleep(2.5)
        auth_code, member_id = parse_performance_logs_for_auth(driver, lookback_seconds=120)
        if auth_code and member_id:
            return auth_code, member_id

        return auth_code, member_id

    finally:
        if driver:
            try:
                if VERBOSE: print("[main] 关闭浏览器...")
                driver.quit()
            except Exception:
                pass


# ----------------------
# 更新配置文件
# ----------------------

def update_config_file(auth_code, member_id, org_id=None, ini_path=CONSTANT_INI_PATH):
    if not auth_code or not member_id:
        if VERBOSE: print("[update_config_file] 认证信息不完整，无法更新配置文件")
        return False
    try:
        with open(ini_path, 'r', encoding='utf-8') as f:
            content = f.read()

        content = re.sub(r"AUTH_CODE\s*=\s*'[^']*'", f"AUTH_CODE = '{auth_code}'", content)
        content = re.sub(r"AUTH_ID\s*=\s*'[^']*'", f"AUTH_ID = '{member_id}'", content)
        if org_id:
            content = re.sub(r"ORG_ID\s*=\s*'[^']*'", f"ORG_ID = '{org_id}'", content)

        with open(ini_path, 'w', encoding='utf-8') as f:
            f.write(content)

        if VERBOSE: print("[update_config_file] 配置文件更新成功")
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
    print("快速提取 Authorization 与 member_id（优化版）")
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

    if not auth_code and not member_id:
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


if __name__ == '__main__':
    main()
