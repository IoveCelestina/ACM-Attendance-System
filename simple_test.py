#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的认证测试脚本
"""

import requests
import json
import time

def test_auth():
    """测试认证"""
    print("=== 测试认证 ===")
    
    # 从Constant.ini读取配置
    try:
        from Modulo import Constant
        print(f"✓ 成功导入配置模块")
    except Exception as e:
        print(f"✗ 无法导入配置模块: {e}")
        return False
    
    # 显示配置信息
    print(f"AUTH_CODE: {Constant.AUTH_CODE}")
    print(f"AUTH_ID: {Constant.AUTH_ID}")
    print(f"ORG_ID: {Constant.ORG_ID}")
    print(f"REMOTE_URL: {Constant.REMOTE_URL}")
    
    # 测试请求
    url = Constant.REMOTE_URL
    
    # 请求头
    headers = {
        'authority': 'checkin2-app.delicloud.com',
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json;charset=UTF-8',
        'Authorization': f'Bearer {Constant.AUTH_CODE}',
        'member_id': str(Constant.AUTH_ID),
        'org_id': str(Constant.ORG_ID),
    }
    
    # 请求数据
    test_data = {
        'org_id': Constant.ORG_ID,
        'page': 1,
        'size': 1,
        'start_time': int(time.time() - 86400) * 1000,  # 1天前
        'end_time': int(time.time()) * 1000,  # 现在
        'dept_ids': [],
        'member_ids': [],
    }
    
    print(f"\n发送请求...")
    print(f"URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            headers=headers, 
            json=test_data,
            verify=False,  # 禁用SSL验证
            timeout=30
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text[:500]}...")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('code') == 0:
                    print("✓ API调用成功!")
                    return True
                else:
                    print(f"⚠ API返回错误: {data.get('msg')}")
                    return False
            except Exception as e:
                print(f"⚠ 响应不是有效JSON: {e}")
                return False
        else:
            print(f"✗ HTTP错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

if __name__ == '__main__':
    print("开始认证测试...")
    success = test_auth()
    
    if success:
        print("\n🎉 认证测试成功！")
    else:
        print("\n❌ 认证测试失败！")
