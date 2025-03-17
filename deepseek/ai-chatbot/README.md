### 国外网站ai-chatbot的sign逆向以及开箱即用

https://ai-chatbot.top/

当前使用不用登录，且服务端没有请求校验，但发现请求时有一条加密参数为sign

提前逆一下这个sign，以防后面服务端进行校验

可以使用get_sign获取sign

使用chat开箱即用

    当前程序运行会占用8000端口，使用/v1/models获取当前支持的模型

    代码中有自定义的apikey在使用其他软件(cherry studio/open webui等)请求时需填入

当前网站宣称自己为满血deepseek，但是却内置的有提示词，一问他就说自己是openAI的ChatGPT

但从思考以及种种验证后得出，此为自部署的deepseek
