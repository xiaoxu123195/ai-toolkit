# ChatGPT 账号自动注册 / 取 Token

批量注册 OpenAI 账号的脚本，含两条流程：

| 脚本 | 用途 | 是否需接码 | 输出 |
|------|------|-----------|------|
| **`register_token.py`** | 走 **chatgpt.com 网页注册**，拿网页 `accessToken` | **否** | `ac/tokens.txt`（每行一个 token） |
| `auto.py` | 走 **codex 授权流程**，拿 codex 凭据 JSON | 是（OTP 后会要求手机验证） | `files/{email}.json` |

> 推荐用 `register_token.py`——网页注册是普通消费者流程，不会被强制手机验证。

---

## 依赖

**Python（3.8+）**
```bash
pip install pyyaml requests curl_cffi
```

**Node.js（必需）**
- 用于 sentinel 风控的算力/turnstile 校验（见下文「工作原理」）。
- 需要 `node` 在 PATH 中（验证：`node --version`）。
- 若 node 不在默认 PATH，可用环境变量 `OPENAI_SENTINEL_NODE_PATH` 指定。

---

## 文件结构

```
new_auto_register/
├── register_token.py            # 主脚本：网页注册 → accessToken
├── auto.py                      # codex 流程（需接码，备用）
├── openai_sentinel_quickjs.js   # sentinel 适配脚本（node 跑真实 sdk.js，必需，勿删）
├── domains.py                   # 查询临时邮箱可用域名
├── config.yaml                  # 配置
├── ac/                          # accessToken 输出目录（自动创建）
│   └── tokens.txt
└── logs/                        # 日志（log_to_file=1 时生成）
```

---

## 配置 `config.yaml`

```yaml
count: 1                         # 注册数量
max_workers: 1                   # 并发数（1 为串行）

email_api: https://yourmail # 临时邮箱服务 (moe mail) 地址
email_api_key: mk_xxx            # 邮箱服务 API Key
email_domain: mailname           # 邮箱域名（留空则用默认）

log_to_file: 0                   # 1 则同时写日志到 logs/

access_token_file: ac/tokens.txt # accessToken 输出文件（相对路径基于脚本目录）

# 以下仅 auto.py(codex 流程) 用到：
upload: 0
upload_url: http://...
upload_token: xxx
```

> 查看临时邮箱服务支持哪些域名：`python domains.py`

---

## 使用

```bash
python register_token.py
```

成功时每个账号往 `ac/tokens.txt` 追加一行 accessToken。日志关键行：

```
sentinel(...) QuickJS 成功 (p=... t=1 ...)   # sentinel 走了 QuickJS 路径（正常）
register: 200
validate-otp: 200 page=... continue_url=...  # page 不应是 add_phone
create_account: 200
accessToken 获取成功 (长度 ...)               # 成功
```

批量：把 `config.yaml` 的 `count` / `max_workers` 调大即可（并发会同时跑多个 node 子进程算 sentinel，注意机器负载）。

---

## 工作原理

### 注册链路（register_token.py）
1. `GET chatgpt.com/api/auth/csrf` → csrfToken
2. `POST chatgpt.com/api/auth/signin/openai` → 服务端生成「网页 client_id + chatgpt.com 回调」的授权 URL（追加 `screen_hint=signup` 指示注册）
3. `GET 授权URL` → 建立网页登录会话
4. `authorize/continue`(提交邮箱) → `user/register`(设密码) → `email-otp/send` + `email-otp/validate`(邮箱验证码) → `create_account`(昵称/生日)
5. 跟随 `continue_url` 落到 `chatgpt.com/api/auth/callback` → 写入 `__Secure-next-auth.session-token`
6. `GET chatgpt.com/api/auth/session` → 取 `accessToken`

> 关键：用网页 client_id 而非 codex client_id 发起授权，才是普通消费者注册，**OTP 后不会弹手机验证（add_phone）**。codex 流程才会要求接码。

### Sentinel 风控（每个写操作都要带）
OpenAI 的注册接口需要 `openai-sentinel-token`，且服务端会用真实 `sdk.js` 做**深层校验**——只发表层 PoW（空 turnstile）会被判 `account_creation_failed`。所以：

- **QuickJS 路径（默认，关键）**：`node` 在伪造的浏览器运行时里 `eval` OpenAI 真实的 `sdk.js`（`openai_sentinel_quickjs.js` 负责打补丁暴露内部方法），产出带 **turnstile `t`** 的合法 token。
- **纯 Python 兜底**：QuickJS 不可用时退化为 FNV-1a 算力 PoW（`t=""`），多数风控 flow 过不了，仅兜底。
- 设 `OPENAI_SENTINEL_DISABLE_QUICKJS=1` 可强制禁用 QuickJS（一般不要）。
- `sdk.js` 按版本号缓存到系统临时目录，只下载一次。

---

## 注意事项

- **`openai_sentinel_quickjs.js` 不能删**，且与 `sdk.js` 版本强绑定。当 OpenAI 升级 `sdk.js`（`register_token.py` 里的 `SENTINEL_VERSION` 变化）时，该适配脚本的字符串补丁可能失效，需同步更新。
- **出口 IP**：OpenAI 不支持 CN/HK 出口。自查：访问 `https://chat.openai.com/cdn-cgi/trace` 看 `loc` 字段。
- 若 `validate-otp` 的 `page` 出现 `add_phone`，说明被风控要求手机验证——网页流正常不会，若出现多半是 IP/风控因素。
- 临时邮箱、并发数、注册频率都会影响成功率；同一 IP 短时间大量注册风险升高。
- 仅用于授权范围内的合法用途。
