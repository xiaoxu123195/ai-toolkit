#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import base64
import hashlib
import requests


def solve_altcha(challenge_data):
    algorithm = challenge_data.get("algorithm", "SHA-256").upper()
    challenge = challenge_data["challenge"]
    salt = challenge_data["salt"]
    signature = challenge_data["signature"]
    max_num = challenge_data.get("maxNumber", 1000000)

    start_time = time.time()

    hash_func = hashlib.sha256
    salt_enc = salt.encode("utf-8")

    for number in range(max_num + 1):
        to_hash = salt_enc + str(number).encode("utf-8")
        attempt = hash_func(to_hash).hexdigest()

        if attempt == challenge:
            took_ms = int((time.time() - start_time) * 1000)
            result_obj = {
                "algorithm": algorithm,
                "challenge": challenge,
                "number": number,
                "salt": salt,
                "signature": signature,
                "took": took_ms
            }
            payload_str = json.dumps(result_obj, separators=(",", ":"))
            token_b64 = base64.b64encode(payload_str.encode("utf-8")).decode("utf-8")
            return token_b64

    return None


def get_ip_info(ip):
    base_headers = {
        'origin': 'https://ip.sy',
        'referer': 'https://ip.sy/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
    }
    create_url = "https://c.ip.sy/create"
    try:
        resp = requests.get(create_url, headers=base_headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return {
            "success": False,
            "message": f"获取验证码失败: {e}"
        }

    challenge_data = resp.json()

    token = solve_altcha(challenge_data)
    if not token:
        return {
            "success": False,
            "message": "在 0 ~ maxNumber 范围内未找到可用解。"
        }

    query_url = "https://ip.sy/api.php"
    query_headers = {
        "token": token,
        **base_headers
    }
    data = {
        "ip": ip
    }

    try:
        query_resp = requests.post(query_url, headers=query_headers, data=data, timeout=10)
        query_resp.raise_for_status()
        result = query_resp.json()
        if result.get("success"):
            return {
                "success": True,
                "data": result["data"]
            }
        else:
            return {
                "success": False,
                "message": result.get("message", "查询失败，请重试！")
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"查询 IP 接口出现错误: {e}"
        }


def main():
    """
    从命令行读取 IP 参数，并输出查询结果
    用法：python script_name.py <ip地址>
    """
    if len(sys.argv) < 2:
        print("用法: python {} <ip地址>".format(sys.argv[0]))
        sys.exit(1)

    ip = sys.argv[1].strip()
    result = get_ip_info(ip)

    if result["success"]:
        print("查询成功，返回数据如下：")
        print(json.dumps(result["data"], indent=2, ensure_ascii=False))
    else:
        print("查询失败：{}".format(result["message"]))


if __name__ == "__main__":
    main()
