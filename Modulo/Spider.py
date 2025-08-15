#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACM考勤统计系统 - Spider模块
功能：负责从得力云API获取考勤数据
特点：完全动态认证，支持重试机制，延迟初始化
"""

import requests
import time
import json
import urllib3
from typing import Dict, List, Any, Optional
from Modulo import Constant


class Spider:
    """
    考勤数据爬取器
    
    主要功能：
    1. 从得力云API获取考勤记录
    2. 支持分页获取大量数据
    3. 自动重试和错误处理
    4. 延迟初始化，避免不必要的网络请求
    """
    
    def __init__(self, start_time: float, end_time: float):
        """
        初始化Spider
        
        Args:
            start_time: 开始时间戳（Unix时间）
            end_time: 结束时间戳（Unix时间）
        """
        # 时间范围（查询的最小粒度为10分钟）
        self.start_time = int(start_time) // 600 * 600
        self.end_time = (int(end_time) + 1) // 600 * 600 - 1
        self.TimeRange = (self.start_time, self.end_time)
        
        # 存储考勤记录 {工号: [记录列表]}
        self.MemberClockinRecords: Dict[str, List[Dict[str, Any]]] = {}
        
        # 延迟初始化标志
        self._initialized = False
        
        # 请求配置
        self.max_retries = getattr(Constant, 'MAX_RETRIES', 5)
        self.timeout = getattr(Constant, 'SSL_TIMEOUT', 60)
        self.verify_ssl = getattr(Constant, 'VERIFY_SSL', False)
        
        # 禁用SSL警告
        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def get_member_records(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取成员考勤记录（延迟加载）
        
        Returns:
            考勤记录字典 {工号: [记录列表]}
        """
        self._ensure_initialized()
        return self.MemberClockinRecords
    
    def _ensure_initialized(self):
        """确保Spider已初始化，延迟加载数据"""
        if not self._initialized:
            self._fetch_all_data()
            self._initialized = True
    
    def _build_headers(self) -> Dict[str, str]:
        """
        构建请求头
        
        Returns:
            完整的请求头字典
        """
        return {
            'authority': 'checkin2-app.delicloud.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'client_id': 'eplus_web',
            'content-type': 'application/json;charset=UTF-8',
            'Authorization': f'Bearer {Constant.AUTH_CODE}',
            'member_id': str(Constant.AUTH_ID),
            'org_id': str(Constant.ORG_ID),
            'origin': 'https://v2-eapp.delicloud.com',
            'sec-ch-ua': '"Chromium";v="118", "Microsoft Edge";v="118", "Not=A?Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.61',
            'x-service-id': 'ass-integration',
        }
    
    def _build_request_data(self, page: int, size: int) -> Dict[str, Any]:
        """
        构建请求数据
        
        Args:
            page: 页码
            size: 每页大小
            
        Returns:
            请求数据字典
        """
        return {
            'org_id': Constant.ORG_ID,
            'page': page,
            'size': size,
            'start_time': self.start_time * 1000,  # 转换为毫秒
            'end_time': self.end_time * 1000,      # 转换为毫秒
            'dept_ids': [],
            'member_ids': [],
        }
    
    def _make_request(self, page: int, size: int) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            page: 页码
            size: 每页大小
            
        Returns:
            API响应数据
            
        Raises:
            requests.RequestException: 请求失败时抛出
        """
        headers = self._build_headers()
        data = self._build_request_data(page, size)
        
        # 创建会话
        session = requests.Session()
        
        # 重试机制
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                print(f"[Spider] 发送请求 第{page}页 (尝试 {attempt + 1}/{self.max_retries + 1})")
                
                response = session.post(
                    Constant.REMOTE_URL,
                    headers=headers,
                    json=data,
                    verify=self.verify_ssl,
                    timeout=self.timeout,
                )
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    error_msg = f"HTTP错误: {response.status_code}"
                    if response.status_code == 401:
                        error_msg += " (认证失败，请检查AUTH_CODE、AUTH_ID、ORG_ID)"
                    elif response.status_code == 403:
                        error_msg += " (权限不足)"
                    elif response.status_code == 500:
                        error_msg += " (服务器内部错误)"
                    
                    raise requests.RequestException(error_msg)
                
                # 解析JSON响应
                try:
                    response_data = response.json()
                except json.JSONDecodeError as e:
                    raise requests.RequestException(f"JSON解析失败: {e}, 响应内容: {response.text[:200]}")
                
                # 检查API业务状态码
                if response_data.get("code") != 0:
                    api_error = response_data.get('msg', '未知错误')
                    raise requests.RequestException(f"API业务错误: {api_error}")
                
                return response_data.get("data", {})
                
            except (requests.exceptions.SSLError, 
                    requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout, 
                    requests.exceptions.RequestException) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"[Spider] 请求失败: {e}, {wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[Spider] 所有重试都失败了，最后异常: {e}")
                    raise
        
        # 如果所有重试都失败
        if last_exception:
            raise last_exception
    
    def _fetch_all_data(self):
        """
        获取所有考勤数据（分页处理）
        """
        print(f"[Spider] 开始获取考勤数据，时间范围: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))} 至 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.end_time))}")
        
        page = 1
        page_size = 100
        total_records = 0
        
        try:
            while True:
                print(f"[Spider] 正在获取第 {page} 页数据...")
                
                # 获取当前页数据
                data = self._make_request(page, page_size)
                records = data.get('records', [])
                
                if not records:
                    print(f"[Spider] 第 {page} 页无数据，停止获取")
                    break
                
                # 处理当前页记录
                page_records = 0
                for record in records:
                    member_id = record.get('member_id', '')
                    if member_id:
                        if member_id not in self.MemberClockinRecords:
                            self.MemberClockinRecords[member_id] = []
                        self.MemberClockinRecords[member_id].append(record)
                        page_records += 1
                        total_records += 1
                
                print(f"[Spider] 第 {page} 页获取到 {page_records} 条记录")
                
                # 检查是否还有更多数据
                if len(records) < page_size:
                    print(f"[Spider] 第 {page} 页数据不足 {page_size} 条，已到最后一页")
                    break
                
                page += 1
                
                # 防止无限循环
                if page > 100:
                    print("[Spider] 警告：分页过多，可能存在数据问题，停止获取")
                    break
                
                # 避免请求过于频繁
                time.sleep(0.1)
            
            print(f"[Spider] 数据获取完成，共获取 {total_records} 条记录，涉及 {len(self.MemberClockinRecords)} 个成员")
            
        except Exception as e:
            print(f"[Spider] 获取数据失败: {e}")
            raise
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取数据摘要信息
        
        Returns:
            包含统计信息的字典
        """
        self._ensure_initialized()
        
        total_members = len(self.MemberClockinRecords)
        total_records = sum(len(records) for records in self.MemberClockinRecords.values())
        
        return {
            'total_members': total_members,
            'total_records': total_records,
            'time_range': {
                'start': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)),
                'end': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.end_time))
            },
            'member_ids': list(self.MemberClockinRecords.keys())
        }
    
    def validate_authentication(self) -> bool:
        """
        验证认证信息是否有效
        
        Returns:
            True表示认证有效，False表示认证无效
        """
        try:
            # 尝试获取第一页数据来验证认证
            test_data = self._make_request(1, 1)
            return True
        except requests.RequestException as e:
            if '401' in str(e) or '认证失败' in str(e):
                print(f"[Spider] 认证验证失败: {e}")
                return False
            else:
                # 其他错误不影响认证验证
                print(f"[Spider] 认证验证时遇到其他错误: {e}")
                return True
        except Exception as e:
            print(f"[Spider] 认证验证时遇到未知错误: {e}")
            return False


# 测试程序
if __name__ == '__main__':
    print("=== Spider模块测试 ===")
    
    # 创建测试实例
    start_time = time.time() - 86400  # 24小时前
    end_time = time.time()            # 现在
    
    try:
        spider = Spider(start_time, end_time)
        print(f"Spider实例创建成功")
        print(f"时间范围: {spider.start_time} 至 {spider.end_time}")
        
        # 测试认证验证
        print("\n--- 测试认证验证 ---")
        auth_valid = spider.validate_authentication()
        print(f"认证状态: {'有效' if auth_valid else '无效'}")
        
        if auth_valid:
            # 测试数据获取
            print("\n--- 测试数据获取 ---")
            records = spider.get_member_records()
            summary = spider.get_summary()
            print(f"数据摘要: {summary}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...")
