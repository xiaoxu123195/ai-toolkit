#!/usr/bin/env python3
"""
OpenAI 兼容的 API 服务
把 MegaLLM 包装成标准的 OpenAI API 格式
"""

import time
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from megallm import MegaLLMClient

import os
import yaml
import secrets


# ==================== 配置 ====================


class AppConfig(BaseModel):
    session_tokens: List[str] = Field(default_factory=list)  # type: ignore[call-overload]
    access_key: Optional[str] = None
    port: int = 8000
    cache_model_list: bool = True
    fingerprint: Optional[str] = None


def load_config(path: str = "config.yaml") -> AppConfig:
    """
    从 YAML 配置文件加载配置
    结构示例:
    session_tokens:
      - token1
      - token2
    access_key: sk-123
    port: 8000
    cache_model_list: true
    fingerprint: "8bdd46d4..."  # 可选，默认每次启动随机生成
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return AppConfig(**raw)

    # 没有配置文件时，尝试从环境变量读取单个 token
    env_token = os.getenv("MEGALLM_SESSION_TOKEN")
    if env_token:
        return AppConfig(session_tokens=[env_token])

    # 最后一层兜底：空配置，后续会报错提示
    return AppConfig()


CONFIG: AppConfig = load_config()

# ==================== 全局客户端 ====================

clients: List[MegaLLMClient] = []
model_list_cache: Optional[Dict[str, Any]] = None
FINGERPRINT: Optional[str] = None


def get_client() -> MegaLLMClient:
    """从多个 session token 中随机选择一个 client"""
    if not clients:
        raise HTTPException(status_code=503, detail="没有可用的 session token，检查配置文件")
    import random
    return random.choice(clients)


def require_access_key(request: Request) -> None:
    """
    校验外部访问用的 access_key（OpenAI 风格的 Bearer token）
    如果 CONFIG.access_key 为空，则不校验
    """
    if not CONFIG.access_key:
        return
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺少 Authorization: Bearer sk-XXX")
    token = auth.split(" ", 1)[1].strip()
    if token != CONFIG.access_key:
        raise HTTPException(status_code=403, detail="无效的 API Key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global clients, model_list_cache, FINGERPRINT

    print("[启动] 加载配置 config.yaml ...")
    if not CONFIG.session_tokens:
        print("[警告] 配置中没有 session_tokens，服务无法正常调用上游 API")
    else:
        print(f"[配置] 加载到 {len(CONFIG.session_tokens)} 个 session token")

    # fingerprint 处理
    if CONFIG.fingerprint:
        FINGERPRINT = CONFIG.fingerprint
        print(f"[配置] 使用配置的 fingerprint: {FINGERPRINT}")
    else:
        FINGERPRINT = secrets.token_hex(32)
        print(f"[配置] 未设置 fingerprint，本次启动随机生成: {FINGERPRINT}")

    print("[启动] 初始化 MegaLLM 客户端...")
    clients = [MegaLLMClient(session_token=t, fingerprint=FINGERPRINT) for t in CONFIG.session_tokens]
    model_list_cache = None
    print("[就绪] 服务已启动")
    yield
    print("[关闭] 服务正在关闭...")


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="MegaLLM OpenAI-Compatible API",
    description="OpenAI 兼容的 MegaLLM API 转发服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 工具函数 ====================


def fetch_models_data() -> Dict[str, Any]:
    """从上游 /api/models 获取完整模型列表，带可选缓存"""
    global model_list_cache

    if CONFIG.cache_model_list and model_list_cache is not None:
        return model_list_cache

    try:
        resp = get_client().list_models()
    except Exception as e:
        print(f"[错误] 调用 /api/models 失败: {e}")
        raise HTTPException(status_code=500, detail="调用上游 /api/models 失败")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"MegaLLM /api/models 错误: {resp.text}",
        )

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=500, detail="解析 /api/models 响应失败")

    if CONFIG.cache_model_list:
        model_list_cache = data

    return data


# ==================== API 端点 ====================

@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models(_: None = Depends(require_access_key)):
    return fetch_models_data()


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str, _: None = Depends(require_access_key)):
    data = fetch_models_data()

    if not isinstance(data, dict) or "data" not in data or not isinstance(data["data"], list):
        raise HTTPException(status_code=500, detail="上游 /api/models 返回格式不符合预期")

    for m in data["data"]:
        if isinstance(m, dict) and m.get("id") == model_id:
            return m

    raise HTTPException(status_code=404, detail=f"Model {model_id} not found")


@app.post("/v1/chat/completions")
async def chat_completions(payload: Dict[str, Any] = Body(...), _: None = Depends(require_access_key)):
    model = payload.get("model")
    messages = payload.get("messages", [])
    stream = bool(payload.get("stream", False))
    temperature = payload.get("temperature", 0.7)
    max_tokens = payload.get("max_tokens", 2048)

    if not model or not messages:
        raise HTTPException(status_code=400, detail="model 和 messages 不能为空")

    print(f"[请求] model={model}, stream={stream}")

    try:
        response = get_client().chat(
            messages=messages,
            model=model,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"MegaLLM API 错误: {response.text}",
            )

        if stream:
            def iter_bytes():
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

            return StreamingResponse(
                iter_bytes(),
                media_type=response.headers.get("content-type", "text/event-stream"),
            )

        return response.json()

    except Exception as e:
        print(f"[错误] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "client_initialized": len(clients) > 0,
        "timestamp": int(time.time())
    }


# ==================== 启动服务 ====================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=CONFIG.port,
        log_level="info"
    )

