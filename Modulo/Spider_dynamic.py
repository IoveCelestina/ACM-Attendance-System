import json
import time
import requests
from Modulo import Constant


class SpiderDynamic:
    def __init__(self, st: float, ed: float, auth_code=None, member_id=None, org_id=None):
        # 查询的最小粒度为 10min
        st = int(st) // 600 * 600
        ed = (int(ed) + 1) // 600 * 600 - 1
        self.TimeRange = st, ed

        # 打卡记录. {工号: [(开始时间, 结束时间), ...]}, Unix 时间
        self.MemberClockinRecords = {}
        
        # 动态认证信息
        self.auth_code = auth_code or Constant.AUTH_CODE
        self.member_id = member_id or Constant.AUTH_ID
        self.org_id = org_id or Constant.ORG_ID
        
        self._parser_data()

    def _get_dynamic_headers(self):
        """获取动态的请求头"""
        return {
            'authority': 'checkin2-app.delicloud.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'authorization': self.auth_code,
            'client_id': 'eplus_web',
            'content-type': 'application/json;charset=UTF-8',
            'member_id': self.member_id,
            'org_id': self.org_id,
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

    def _requests(self, page: int, size: int) -> dict:
        _json_data = {
            'org_id': self.org_id,
            'page': page,
            'size': size,
            'start_time': self.TimeRange[0] * 1000,  # 单位 ms
            'end_time': self.TimeRange[1] * 1000,    # 单位 ms
            'dept_ids': [],
            'member_ids': [],
        }

        # 使用动态请求头
        headers = self._get_dynamic_headers()
        
        print(f"使用动态认证信息发送请求...")
        print(f"  AUTH_CODE: {self.auth_code[:50] if self.auth_code else 'None'}...")
        print(f"  AUTH_ID: {self.member_id}")
        print(f"  ORG_ID: {self.org_id}")
        print(f"  请求URL: {Constant.REMOTE_URL}")
        print(f"  请求数据: {_json_data}")

        # 验证认证信息
        if not self.auth_code or not self.member_id or not self.org_id:
            raise requests.RequestException('认证信息不完整: AUTH_CODE={}, AUTH_ID={}, ORG_ID={}'.format(
                '有值' if self.auth_code else '无值',
                '有值' if self.member_id else '无值',
                '有值' if self.org_id else '无值'
            ))

        try:
            _response = requests.post(
                Constant.REMOTE_URL,
                headers=headers,
                json=_json_data,
                timeout=30  # 添加超时设置
            )
            
            print(f"响应状态码: {_response.status_code}")
            print(f"响应头: {dict(_response.headers)}")
            
            if _response.status_code != 200:
                print(f"API请求失败，状态码: {_response.status_code}")
                print(f"响应内容: {_response.text}")
                
                # 如果是认证错误，提供更详细的诊断信息
                if _response.status_code == 401:
                    print("=== 认证失败诊断信息 ===")
                    print("可能的原因:")
                    print("1. 认证令牌已过期")
                    print("2. 认证令牌格式不正确")
                    print("3. 用户ID或组织ID不匹配")
                    print("4. 权限不足")
                    print("建议:")
                    print("1. 重新登录获取新的认证信息")
                    print("2. 检查认证信息的格式")
                    print("3. 确认用户权限")
                    print("========================")
                
                raise requests.RequestException('Unexpected Status Code: {}'.format(_response.status_code))
                
            _response.encoding = 'utf-8'
            _data = json.loads(_response.text)
            
            if _data["code"] != 0:
                print(f"API返回错误: {_data['msg']}")
                raise requests.RequestException('Unexpected JSON Message: {}'.format(_data["msg"]))
                
            return _data["data"]
            
        except requests.exceptions.Timeout:
            print("请求超时，请检查网络连接")
            raise
        except requests.exceptions.ConnectionError:
            print("连接错误，请检查网络连接")
            raise
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"响应内容: {_response.text}")
            raise
        except Exception as e:
            print(f"请求过程中出现未知错误: {e}")
            raise

    def _parser_data(self):
        _records = {}

        # 获取原始数据
        _data = self._requests(1, 100000000)["rows"]  # 最多获取 1e8 条记录

        # 数据整合
        for _item in _data:
            # _id = _item["member_name"]  # 人员主键
            _id = _item["checkin_extra_data"]["employee_num"].strip().upper()  # 人员主键
            if _id == '':  # 过滤无编号人员
                continue
            _time = int(_item["check_in_time"]) // 1000
            if _id not in _records:
                _records[_id] = []
            _records[_id].append(_time)

        # 数据处理
        for _id, _record in _records.items():
            _record.sort()

            # 原地过滤频繁打卡
            _pre, _j = 0, 0
            for _i in range(len(_record)):
                if _record[_i] - _pre >= Constant.FREQUENCY_FILTER:
                    _record[_j] = _record[_i]
                    _pre = _record[_j]
                    _j += 1
            # _record = _record[:_j]  # 目前注释掉也无妨

            # 将同一天的打卡记录配对导出
            _i = 1
            while _i < _j:
                _pre_tm = time.localtime(_record[_i - 1])
                _now_tm = time.localtime(_record[_i])
                if _pre_tm.tm_year == _now_tm.tm_year and _pre_tm.tm_yday == _now_tm.tm_yday:
                    if _id not in self.MemberClockinRecords:
                        self.MemberClockinRecords[_id] = []
                    self.MemberClockinRecords[_id].append((_record[_i - 1], _record[_i]))
                    _i += 2
                else:  # 过滤同一天落单的一条记录
                    _i += 1


# 测试程序
if __name__ == '__main__':
    spider = SpiderDynamic(1696089600, 1698163199)
    input("Exit >")
