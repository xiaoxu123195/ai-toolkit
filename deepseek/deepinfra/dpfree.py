import asyncio
import aiohttp
import json
from pydantic import BaseModel, Field
from typing import List, Optional, Callable, Awaitable, AsyncGenerator


class Pipe:
    class Valves(BaseModel):
        api_url: str = Field(
            default="https://api.deepinfra.com/v1/openai",
            description="Base URL for the Deepinfra API.",
        )
        model: str = Field(
            default="deepseek-ai/DeepSeek-R1",
            description="The name of the model.",
        )
        max_tokens: int = Field(
            default=2048,
            description="Maximum number of tokens to generate.",
        )
        temperature: float = Field(
            default=0.7,
            description="Sampling temperature for generation.",
        )

    def __init__(self):
        self.type = "manifold"
        self.name = "deep_chat_"
        self.valves = self.Valves()
        self.emitter = None

    async def emit_status(self, message: str = "", done: bool = False):
        if self.emitter:
            await self.emitter(
                {"type": "status", "data": {"description": message, "done": done}}
            )

    async def process_stream(self, response) -> AsyncGenerator[str, None]:
        """处理SSE事件流"""
        buffer = b""
        async for chunk in response.content.iter_any():
            buffer += chunk
            while b"\n\n" in buffer:
                line, buffer = buffer.split(b"\n\n", 1)
                line = line.strip()

                if not line:
                    continue

                # 处理SSE格式
                if line.startswith(b"data: "):
                    data = line[6:]  # 去除data: 前缀
                    if data == b"[DONE]":
                        return

                    try:
                        json_data = json.loads(data)
                        if "choices" in json_data:
                            for choice in json_data["choices"]:
                                content = choice.get("delta", {}).get("content", "")
                                if content:
                                    yield content
                    except json.JSONDecodeError:
                        await self.emit_status("JSON解析错误", done=False)

    async def get_request_stream(self, messages: list) -> AsyncGenerator[str, None]:
        url = f"{self.valves.api_url}/chat/completions"
        payload = {
            "model": self.valves.model,
            "messages": messages,
            "stream": True,
            "max_tokens": self.valves.max_tokens,
            "temperature": self.valves.temperature,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
            "Accept": "text/event-stream",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "sec-ch-ua-platform": "Windows",
            "X-Deepinfra-Source": "web-page",
            "sec-ch-ua": '"Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="133"',
            "sec-ch-ua-mobile": "?0",
            "Origin": "https://deepinfra.com",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://deepinfra.com/",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise Exception(f"API Error {response.status}: {error}")

                    async for content in self.process_stream(response):
                        yield content
        except Exception as e:
            yield f"🚨 错误: {str(e)}"

    # 辅助方法
    def get_models(self):
        return [
            {"id": model, "name": model}
            for model in [
                "deepseek-ai/DeepSeek-R1"
                # "meta-llama/Meta-Llama-3-70B-Instruct",
                # "mistralai/Mixtral-8x22B-Instruct-v0.1"
            ]
        ]

    def pipes(self) -> List[dict]:
        return self.get_models()

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __event_call__: Callable[[dict], Awaitable[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        self.emitter = __event_emitter__
        await self.emit_status("验证请求...")

        try:
            messages = body["messages"]
            if not messages:
                await self.emit_status("错误：空消息列表", done=True)
                yield "❌ 错误：至少需要一个消息"
                return

            # 构建有效消息列表
            valid_messages = []
            for msg in messages:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    valid_messages.append(
                        {"role": msg["role"], "content": str(msg["content"])}
                    )

            if not valid_messages:
                await self.emit_status("错误：无有效消息", done=True)
                yield "❌ 错误：消息格式无效"
                return

            await self.emit_status("开始生成响应...", done=False)

            try:
                async for chunk in self.get_request_stream(valid_messages):
                    await self.emit_status("正在生成...")
                    yield chunk
            except Exception as e:
                yield f"🚨 流式传输错误: {str(e)}"

        except Exception as e:
            await self.emit_status(f"严重错误: {str(e)}", done=True)
            yield f"❌ 系统错误: {str(e)}"
        finally:
            await self.emit_status("完成生成", done=True)