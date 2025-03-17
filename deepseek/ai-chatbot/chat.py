# -*- coding:utf-8 -*-
import json
import random
import uuid
from datetime import datetime, timezone
import time
import re
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
import httpx
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


class Config:
    API_KEY = "sk-TkoWuEN8cpDJubb7Zfwxln16NQDZIc8z"
    DEFAULT_MODEL = "DeepSeek-R1"


class SessionManager:
    def __init__(self):
        self.chat_id = None
        self.sign = None
        self.current_time = None
        self.answer_id = []
        self.think_list = []

    def initialize(self):
        self.chat_id = get_chat_id()
        self.current_time, self.sign = generate_sign(self.chat_id)
        logger.info(f"Session initialized: chat_id={self.chat_id}, current_time={self.current_time}, sign={self.sign}")

    def is_initialized(self):
        return all([self.chat_id, self.current_time, self.sign])

    async def refresh_if_needed(self):
        if not self.is_initialized():
            self.initialize()


session_manager = SessionManager()


class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    user: Optional[str] = None


class ModelData(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str
    permission: List[Dict[str, Any]] = Field(default_factory=list)
    root: str
    parent: Optional[str] = None


def get_chat_id():
    cookies = {
        '_ga_HVMZBNYJML': 'GS1.1.1742013194.1.0.1742013194.0.0.0',
        '_ga': 'GA1.1.1029622546.1742013195',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://ai-chatbot.top/',
        'RSC': '1',
        'Next-Router-State-Tree': '%5B%22%22%2C%7B%22children%22%3A%5B%22(chat)%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C%22%2F%22%2C%22refresh%22%5D%7D%5D%7D%2Cnull%2C%22refetch%22%5D',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Priority': 'u=0',
    }

    params = {
        '_rsc': 'l4cx',
    }

    response = httpx.get('https://ai-chatbot.top/', params=params, cookies=cookies, headers=headers, timeout=30)
    return \
        re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}',
                   response.text)[
            -1]


def generate_sign(conversation_id: str):
    current_time = int(time.time() * 1000)
    message = conversation_id + str(current_time) + "@!~chatbot.0868"
    sign = hashlib.md5(message.encode('utf-8')).hexdigest()
    return current_time, sign


def generate_uuid():
    template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"

    def replace_char(match):
        char = match.group()
        if char == 'x':
            return format(random.randint(0, 15), 'x')
        elif char == 'y':
            return format(random.randint(8, 11), 'x')

    uuid = re.sub(r'[xy]', replace_char, template)
    return uuid


def get_createdAt():
    now = datetime.now(timezone.utc)
    iso_str = now.isoformat()
    return iso_str[:-9] + 'Z'


async def verify_api_key(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = authorization.replace("Bearer ", "").strip()
    if api_key != Config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


def create_chunk(sse_id: str, created: int, content: Optional[str] = None,
                 is_first: bool = False, meta: Optional[dict] = None,
                 finish_reason: Optional[str] = None) -> dict:
    delta = {}

    if content is not None:
        if is_first:
            delta = {"role": "assistant", "content": content}
        else:
            delta = {"content": content}

    if meta is not None:
        delta["meta"] = meta

    return {
        "id": f"chatcmpl-{sse_id}",
        "object": "chat.completion.chunk",
        "created": created,
        "model": Config.DEFAULT_MODEL,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason
        }]
    }


async def process_message_event(data: str, is_first_chunk: bool, in_thinking_block: bool,
                                thinking_started: bool, thinking_content: list) -> Tuple[str, bool, bool, bool, list]:
    content = data[2:].strip().replace('"', '').replace("\\n", "\n")
    created = int(time.time())
    sse_id = uuid.uuid4()
    result = ""

    if "g" == data[0] and not thinking_started:
        thinking_started = True
        in_thinking_block = True
        # Send thinking block start marker
        chunk = create_chunk(
            sse_id=sse_id,
            created=created,
            content="<think>\n\n" + content,
            is_first=is_first_chunk
        )
        session_manager.think_list.append(content)
        result = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        return result, in_thinking_block, thinking_started, is_first_chunk, thinking_content

    if "0" == data[0] and in_thinking_block:
        in_thinking_block = False
        chunk = create_chunk(
            sse_id=sse_id,
            created=created,
            content="\n</think>\n\n" + content
        )
        session_manager.think_list[-1] += content
        result = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        return result, in_thinking_block, thinking_started, is_first_chunk, thinking_content

    if in_thinking_block:
        thinking_content.append(content)
        chunk = create_chunk(
            sse_id=sse_id,
            created=created,
            content=content
        )
        session_manager.think_list[-1] += content
        result = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        return result, in_thinking_block, thinking_started, is_first_chunk, thinking_content

    chunk = create_chunk(
        sse_id=sse_id,
        created=created,
        content=content,
        is_first=is_first_chunk
    )
    result = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    return result, in_thinking_block, thinking_started, False, thinking_content


def process_generate_end_event(data: dict, in_thinking_block: bool, thinking_content: list) -> List[str]:
    result = []
    created = int(time.time())
    sse_id = data.get('sseId', str(uuid.uuid4()))

    if in_thinking_block:
        end_thinking_chunk = create_chunk(
            sse_id=sse_id,
            created=created,
            content="\n</think>\n\n"
        )
        result.append(f"data: {json.dumps(end_thinking_chunk, ensure_ascii=False)}\n\n")

    meta_chunk = create_chunk(
        sse_id=sse_id,
        created=created,
        meta={"thinking_content": "".join(thinking_content) if thinking_content else None}
    )
    result.append(f"data: {json.dumps(meta_chunk, ensure_ascii=False)}\n\n")

    end_chunk = create_chunk(
        sse_id=sse_id,
        created=created,
        finish_reason="stop"
    )
    result.append(f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n")
    result.append("data: [DONE]\n\n")
    return result


async def generate_response(messages: List[dict], model: str, temperature: float, stream: bool,
                            max_tokens: Optional[int] = None, presence_penalty: float = 0,
                            frequency_penalty: float = 0, top_p: float = 1.0) -> AsyncGenerator[str, None]:
    await session_manager.refresh_if_needed()
    cookies = {
        '_ga_HVMZBNYJML': 'GS1.1.1742013194.1.1.1742013780.0.0.0',
        '_ga': 'GA1.1.1029622546.1742013195',
    }

    list_message = []
    for i in range(len(messages)):
        if messages[i]['role'] == 'user':
            json_message = {
                "content": messages[i]['content'],
                "createdAt": get_createdAt(),
                "id": generate_uuid(),
                "parts": [
                    {
                        "text": messages[i]['content'],
                        "type": "text"
                    }
                ],
                "role": messages[i]['role']
            }
            list_message.append(json_message)
        elif messages[i]['role'] == 'assistant':
            json_message = {
                "content": messages[i]['content'],
                "createdAt": get_createdAt(),
                "id": session_manager.answer_id[i],
                "parts": [
                    {
                        "details": [
                            {
                                "text": session_manager.think_list[i],
                                "type": "text"
                            }
                        ],
                        "reasoning": session_manager.think_list[i],
                        "type": "reasoning"
                    },
                    {
                        "text": messages[i]['content'],
                        "type": "text"
                    }
                ],
                "reasoning": session_manager.think_list[i],
                "revisionId": generate_uuid(),
                "role": "assistant"
            }
            list_message.append(json_message)

    if model == 'DeepSeek-R1-Web':
        payload = {
            'id': session_manager.chat_id,
            'messages': list_message,
            'selectedChatModel': 'deepseek-huoshan',
            'isDeepThinkingEnabled': True,
            'isWebSearchEnabled': True,
        }
    else:
        payload = {
            'id': session_manager.chat_id,
            'messages': list_message,
            'selectedChatModel': 'deepseek-huoshan',
            'isDeepThinkingEnabled': True,
            'isWebSearchEnabled': False,
        }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://ai-chatbot.top/chat/' + session_manager.chat_id,
        'Content-Type': 'application/json',
        'currentTime': str(session_manager.current_time),
        'sign': session_manager.sign,
        'Origin': 'https://ai-chatbot.top',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Priority': 'u=0',
    }

    session_manager.answer_id.append("0")
    session_manager.think_list.append("0")
    session_manager.current_time, session_manager.sign = generate_sign(session_manager.chat_id)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(900)) as client:
            async with client.stream('POST', 'https://ai-chatbot.top/api/chat',
                                     headers=headers, json=payload, cookies=cookies) as response:
                response.raise_for_status()

                is_first_chunk = True
                current_event = None
                in_thinking_block = False
                thinking_content = []
                thinking_started = False

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        current_event = None
                        continue

                    # Parse event type
                    if line.startswith("f:"):
                        json_str = line[2:].strip()
                        json_data = json.loads(json_str)
                        session_manager.answer_id.append(json_data['messageId'])

                    if line.startswith("g:"):
                        data = line[:].strip()
                        result, in_thinking_block, thinking_started, is_first_chunk, thinking_content = await process_message_event(
                            data, is_first_chunk, in_thinking_block, thinking_started, thinking_content
                        )
                        if result:
                            yield result

                    if line.startswith("0:"):
                        data = line[:].strip()
                        result, in_thinking_block, thinking_started, is_first_chunk, thinking_content = await process_message_event(
                            data, is_first_chunk, in_thinking_block, thinking_started, thinking_content
                        )
                        if result:
                            yield result

                if in_thinking_block:
                    for chunk in process_generate_end_event({}, in_thinking_block, thinking_content):
                        yield chunk

    except httpx.RequestError as e:
        logger.error(f"Response generation error: {e}")
        try:
            session_manager.initialize()
            logger.info("Session reinitialized")
        except Exception as re_init_error:
            logger.error(f"Session reinitialization failed: {re_init_error}")
        raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")


@app.get("/v1/models")
async def list_models():
    current_time = int(time.time())
    models_data = [
        ModelData(
            id=Config.DEFAULT_MODEL,
            created=current_time,
            owned_by="aichatbot",
            root=Config.DEFAULT_MODEL,
            permission=[{
                "id": f"modelperm-{Config.DEFAULT_MODEL}",
                "object": "model_permission",
                "created": current_time,
                "allow_create_engine": False,
                "allow_sampling": True,
                "allow_logprobs": True,
                "allow_search_indices": False,
                "allow_view": True,
                "allow_fine_tuning": False,
                "organization": "aichatbot",
                "group": None,
                "is_blocking": False
            }]
        ),
        ModelData(
            id='DeepSeek-R1-Web',
            created=current_time,
            owned_by="aichatbot",
            root='DeepSeek-R1-Web',
            permission=[{
                "id": f"modelperm-DeepSeek-R1-Web",
                "object": "model_permission",
                "created": current_time,
                "allow_create_engine": False,
                "allow_sampling": True,
                "allow_logprobs": True,
                "allow_search_indices": False,
                "allow_view": True,
                "allow_fine_tuning": False,
                "organization": "aichatbot",
                "group": None,
                "is_blocking": False
            }]
        )
    ]

    return {"object": "list", "data": models_data}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, authorization: str = Header(None)):
    await verify_api_key(authorization)

    logger.info(f"Received chat request: model={request.model}, stream={request.stream}")

    messages = [msg.model_dump() for msg in request.messages]

    return StreamingResponse(
        generate_response(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            stream=request.stream,
            max_tokens=request.max_tokens,
            presence_penalty=request.presence_penalty,
            frequency_penalty=request.frequency_penalty,
            top_p=request.top_p
        ),
        media_type="text/event-stream"
    )


@app.on_event("startup")
async def startup_event():
    try:
        session_manager.initialize()
    except Exception as e:
        logger.error(f"Startup initialization error: {e}")
        raise


@app.get("/health")
async def health_check():
    if session_manager.is_initialized():
        return {"status": "ok", "session": "active"}
    else:
        return {"status": "degraded", "session": "inactive"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
