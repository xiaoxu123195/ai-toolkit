### trae2api

使用get_key获取当前电脑上安装的trae部分信息用于docker部署


```dockerfile
docker run -d \
  --name trae2api \
  -p 17080:17080 \
  -e APP_ID="app_id" \               # Trae APP ID
  -e CLIENT_ID="client_id" \         # Trae 客户端ID
  -e REFRESH_TOKEN="refresh_token" \ # Trae 刷新令牌
  -e USER_ID="user_id" \             # Trae 用户 ID
  -e AUTH_TOKEN="auth_token" \       # 接口鉴权，为空则不需要api接口鉴权
  --restart always \
  linqiu1199/trae2api:v1.0.5
```

```dockerfile
docker run -d `
  --name trae2api `
  -p 17080:17080 `
  -e APP_ID="" `
  -e CLIENT_ID="" `
  -e REFRESH_TOKEN="" `
  -e USER_ID="" `
  -e AUTH_TOKEN="yue123" `
  --restart always `
  linqiu1199/trae2api:v1.0.5

```

