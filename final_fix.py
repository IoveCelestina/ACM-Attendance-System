#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终修复脚本 - 尝试不同的认证方式
"""

import requests
import json
import time
import traceback

def test_auth_formats():
    """测试不同的认证格式"""
    print("=== 测试不同认证格式 ===")
    
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
    
    # 测试不同的认证格式
    auth_formats = [
        # 格式1：标准Bearer格式
        {
            'name': '标准Bearer格式',
            'headers': {
                'authority': 'checkin2-app.delicloud.com',
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json;charset=UTF-8',
                'Authorization': f'Bearer {Constant.AUTH_CODE}',
                'member_id': str(Constant.AUTH_ID),
                'org_id': str(Constant.ORG_ID),
            }
        },
        # 格式2：无Bearer前缀
        {
            'name': '无Bearer前缀',
            'headers': {
                'authority': 'checkin2-app.delicloud.com',
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json;charset=UTF-8',
                'Authorization': Constant.AUTH_CODE,
                'member_id': str(Constant.AUTH_ID),
                'org_id': str(Constant.ORG_ID),
            }
        },
        # 格式3：小写authorization
        {
            'name': '小写authorization',
            'headers': {
                'authority': 'checkin2-app.delicloud.com',
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json;charset=UTF-8',
                'authorization': f'Bearer {Constant.AUTH_CODE}',
                'member_id': str(Constant.AUTH_ID),
                'org_id': str(Constant.ORG_ID),
            }
        },
        # 格式4：使用连字符
        {
            'name': '使用连字符',
            'headers': {
                'authority': 'checkin2-app.delicloud.com',
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json;charset=UTF-8',
                'Authorization': f'Bearer {Constant.AUTH_CODE}',
                'member-id': str(Constant.AUTH_ID),
                'org-id': str(Constant.ORG_ID),
            }
        },
        # 格式5：最小化headers
        {
            'name': '最小化headers',
            'headers': {
                'content-type': 'application/json;charset=UTF-8',
                'Authorization': f'Bearer {Constant.AUTH_CODE}',
            }
        }
    ]
    
    success_count = 0
    for i, auth_format in enumerate(auth_formats, 1):
        print(f"\n--- 测试 {i}/{len(auth_formats)}: {auth_format['name']} ---")
        
        try:
            response = requests.post(
                url, 
                headers=auth_format['headers'], 
                json=test_data,
                verify=False,  # 禁用SSL验证
                timeout=30
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('code') == 0:
                        print("✓ 成功！")
                        success_count += 1
                        # 保存成功的格式
                        with open('working_auth_format.json', 'w', encoding='utf-8') as f:
                            json.dump({
                                'format_name': auth_format['name'],
                                'headers': auth_format['headers'],
                                'timestamp': time.time()
                            }, f, ensure_ascii=False, indent=2)
                        print("✓ 已保存成功的认证格式到 working_auth_format.json")
                    else:
                        print(f"⚠ API返回错误: {data.get('msg')}")
                except Exception as e:
                    print(f"⚠ 响应不是有效JSON: {e}")
            elif response.status_code == 401:
                print("✗ 认证失败 (401)")
            else:
                print(f"⚠ HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"✗ 请求失败: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"成功格式数: {success_count}/{len(auth_formats)}")
    
    if success_count > 0:
        print("🎉 找到可用的认证格式！")
        return True
    else:
        print("❌ 所有认证格式都失败了")
        return False

def diagnose_auth_issue():
    """诊断认证问题"""
    print("\n=== 认证问题诊断 ===")
    
    try:
        from Modulo import Constant
        
        # 检查认证信息
        print("1. 检查认证信息:")
        print(f"   AUTH_CODE长度: {len(Constant.AUTH_CODE) if Constant.AUTH_CODE else 0}")
        print(f"   AUTH_CODE格式: {Constant.AUTH_CODE[:20] if Constant.AUTH_CODE else 'None'}...")
        print(f"   AUTH_ID: {Constant.AUTH_ID}")
        print(f"   ORG_ID: {Constant.ORG_ID}")
        
        # 检查是否包含特殊字符
        if Constant.AUTH_CODE:
            special_chars = [c for c in [' ', '\n', '\r', '\t'] if c in Constant.AUTH_CODE]
            if special_chars:
                print(f"   ⚠ AUTH_CODE包含特殊字符: {special_chars}")
            else:
                print("   ✓ AUTH_CODE格式正常")
        
        # 检查网络连接
        print("\n2. 检查网络连接:")
        try:
            response = requests.get('https://checkin2-app.delicloud.com', verify=False, timeout=10)
            print(f"   ✓ 基础连接成功: {response.status_code}")
        except Exception as e:
            print(f"   ✗ 基础连接失败: {e}")
        
        # 建议
        print("\n3. 建议:")
        print("   - 重新登录获取新的认证信息")
        print("   - 检查用户权限是否足够")
        print("   - 确认组织ID是否正确")
        print("   - 检查认证token是否已过期")
        
    except Exception as e:
        print(f"诊断过程中出现错误: {e}")

if __name__ == '__main__':
    print("开始最终认证修复...")
    
    # 测试不同认证格式
    success = test_auth_formats()
    
    # 诊断问题
    diagnose_auth_issue()
    
    if success:
        print("\n🎉 找到可用的认证格式！请使用 working_auth_format.json 中的配置。")
    else:
        print("\n❌ 所有认证格式都失败了，需要重新获取认证信息。")
