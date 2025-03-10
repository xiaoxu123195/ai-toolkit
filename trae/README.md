### trae2api

使用get_key获取当前电脑上安装的trae部分信息用于docker部署

使用get_token获取当前电脑上安装的trea的token以及当前token的过期时间

token的过期时间也可以在网站`https://jwt.io/` 中进行查询，当前获取token的有效期大概是3天左右


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

# 查看当前作者是否更新了当前库
1. `docker pull linqiu1199/trae2api:latest`

2. 或者访问`https://hub.docker.com/r/linqiu1199/trae2api/tags` 查看
