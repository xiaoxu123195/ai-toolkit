#!/usr/bin/env python3
"""
MegaLLM API 客户端
逆向自 js，实现了签名/PoW 机制
"""

import json
import time
import hashlib
import hmac
import secrets
from typing import Dict, Any, Tuple
import requests


class MegaLLMClient:
    """MegaLLM API 客户端，自动处理签名和 PoW"""
    
    def __init__(self, session_token: str, base_url: str = "https://megallm.io", fingerprint: str | None = None):
        """
        初始化客户端
        
        Args:
            session_token: __Secure-next-auth.session-token 的值
            base_url: API 基础 URL
        """
        self.base_url = base_url
        self.session_token = session_token
        self.fingerprint = fingerprint or self._generate_fingerprint()
        self.hmac_key = self._assemble_key()
        
    def _generate_fingerprint(self) -> str:
        """
        生成设备指纹
        浏览器里是用音频/canvas/UA 等生成，这里简化成随机值
        只要在同一个进程内保持一致就行，服务端只是拿它做标识
        """
        # 默认生成 32 字节随机 hex
        return secrets.token_hex(32)
    
    def _assemble_key(self) -> str:
        """
        组装 HMAC 密钥
        对应 a.js 里的 g() 函数
        """
        # 这些函数对应 c/d/u/x/m/f/p/h/b/v
        parts = [
            "MegaLLM",           # c(): String.fromCharCode(77, 101, 103, 97, 76, 76, 77)
            "_public",           # d(): atob("X3B1YmxpYw==")
            "_key",              # u()
            "_2025",             # x(): String.fromCharCode(95, 50, 48, 50, 53)
            "c2VjdX",            # m(): btoa("secure").substring(0, 6)
            "_v2",               # f()
            "_hmac",             # p(): String.fromCharCode(95, 104, 109, 97, 99)
            "_sig",              # h()
            "_final",            # b(): atob("X2ZpbmFs")
            "_32",               # v(): String.fromCharCode(95, 51, 50)
        ]
        
        # 拼接后再按位 XOR（对应 .map((e, t) => String.fromCharCode(e.charCodeAt(0) ^ 42 + t % 7))）
        joined = "".join(parts)
        xored = "".join(
            chr(ord(char) ^ (42 + idx % 7))
            for idx, char in enumerate(joined)
        )
        
        # base64 编码（对应 btoa(e)）
        import base64
        return base64.b64encode(xored.encode()).decode()
    
    def _random_hex(self, length: int = 32) -> str:
        """
        生成随机 hex 字符串
        对应 a.js 里的 y()
        """
        return secrets.token_hex(length)
    
    def _sha256_hex(self, data: str) -> str:
        """
        SHA-256 哈希，返回 hex
        对应 a.js 里的 w()
        """
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _solve_pow(self, challenge: str, difficulty: int = 2) -> Tuple[str, int]:
        """
        解 PoW 难题
        对应 a.js 里的 j()
        
        找到一个整数 solution，使得 SHA256(challenge:solution) 以 N 个 '0' 开头
        
        Returns:
            (solution, attempts)
        """
        prefix = "0" * difficulty
        solution = 0
        attempts = 0
        
        while True:
            attempts += 1
            candidate = f"{challenge}:{solution}"
            hash_result = self._sha256_hex(candidate)
            
            if hash_result.startswith(prefix):
                return str(solution), attempts
            
            solution += 1
            
            # 防止死循环
            if attempts > 1_000_000:
                raise RuntimeError("PoW: 超过最大尝试次数")
    
    def _hmac_sha256_hex(self, message: str, key: str) -> str:
        """
        HMAC-SHA256，返回 hex
        对应 a.js 里的 N()
        """
        return hmac.new(
            key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _generate_signature(self, method: str, path: str, body: str) -> Dict[str, str]:
        """
        生成签名和相关 headers
        对应 a.js 里的 k()
        
        Args:
            method: HTTP 方法，如 "POST"
            path: 路径+查询参数，如 "/api/chat"
            body: 请求体字符串（JSON）
            
        Returns:
            包含所有 X- 开头 header 的字典
        """
        nonce = self._random_hex(32)
        timestamp = str(int(time.time()))
        challenge = self._random_hex(32)
        
        # 解 PoW
        solution, attempts = self._solve_pow(challenge, difficulty=2)
        print(f"[PoW] 尝试 {attempts} 次，找到解: {solution}")
        
        # 计算 body 的哈希
        body_hash = self._sha256_hex(body)
        
        # 组装签名消息
        # base = method:path:timestamp:nonce:fingerprint:solution
        base = f"{method}:{path}:{timestamp}:{nonce}:{self.fingerprint}:{solution}"
        message = f"{base}:{body_hash}"
        
        # 计算 HMAC 签名
        signature = self._hmac_sha256_hex(message, self.hmac_key)
        
        return {
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "X-Fingerprint": self.fingerprint,
            "X-PoW-Challenge": challenge,
            "X-PoW-Solution": solution,
        }
    
    def chat(
        self,
        messages: list,
        model: str = "gpt-4.1",
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> requests.Response:
        """
        调用 /api/chat 接口
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model: 模型名称
            stream: 是否流式返回
            temperature: 温度
            max_tokens: 最大 token 数
            
        Returns:
            requests.Response 对象
        """
        url = f"{self.base_url}/api/chat"
        
        # 构造请求体
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "signal": {},  # 浏览器里的 AbortSignal，这里留空
        }
        
        body_str = json.dumps(payload, separators=(',', ':'))  # 紧凑格式
        
        # 生成签名
        sig_headers = self._generate_signature("POST", "/api/chat", body_str)
        
        # 组装完整 headers
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            **sig_headers,  # 加上签名相关的 X- headers
        }
        
        # 构造 cookies
        cookies = {
            "__Secure-next-auth.session-token": self.session_token,
        }
        
        # 发送请求
        print(f"[请求] POST {url}")
        print(f"[签名] {sig_headers['X-Signature'][:16]}...")
        
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            data=body_str,
            stream=stream,  # 如果 stream=True，需要自己处理 SSE
        )
        
        return response

    def list_models(self) -> requests.Response:
        """
        调用 /api/models 接口，获取模型列表
        使用 GET + 签名（body 为空字符串）
        """
        path = "/api/models"
        url = f"{self.base_url}{path}"
        body_str = ""
        
        # 生成签名
        sig_headers = self._generate_signature("GET", path, body_str)
        
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            **sig_headers,
        }
        
        cookies = {
            "__Secure-next-auth.session-token": self.session_token,
        }
        
        print(f"[请求] GET {url}")
        print(f"[签名] {sig_headers['X-Signature'][:16]}...")
        
        response = requests.get(
            url,
            headers=headers,
            cookies=cookies,
        )
        
        return response