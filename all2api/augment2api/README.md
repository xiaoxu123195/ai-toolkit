### Augment2api

官方网站：https://www.augmentcode.com/

是类似于cursor的code软件

get_apikey是用于获取访问令牌(API Key)

注意：不是批量获取的

augment2api_server是封装的具体作用是

 1. 获取apikey
 2. 服务跑起来后开放端口（已封装为openai格式）

docker部署

1. 拉取项目

```Git
git clone https://github.com/linqiu919/augment2api.git
```
2. 进入项目目录

```Git
cd augment2api
```
3. 创建`.env`文件，填写下面两个环境变量：

```Git
# 设置Redis密码
REDIS_PASSWORD=your-redis-password

# 设置api鉴权token
AUTH_TOKEN=your-auth-token
```
4. 运行

```Git
docker-compose up -d
```

使用：
1. 访问`http://ip:27080/`进入管理页面
2. 点击获取授权链接
3. 复制授权链接到浏览器中打开
4. 使用邮箱进行登录（域名邮箱也可）
5. 复制`augment code`到授权响应输入框中，点击获取token
6. 开始对话测试