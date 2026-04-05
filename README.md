# 数字人 AI - 人格问卷系统

基于 Flask 的移动端人格画像问卷系统。

## 功能

- 📋 4份人格问卷 (大五人格/社交关系/价值观/兴趣)
- 📱 移动端H5界面，响应式设计
- 🔐 用户注册/登录系统
- 🧠 自动构建人格向量画像
- 📤 数据回传到本地服务器

## 快速部署到 Render

1. Fork 此仓库到你的 GitHub
2. 访问 [render.com](https://render.com) 注册账号
3. 点击 "New" → "Web Service"
4. 连接你的 GitHub 仓库
5. 设置：
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn web.app:app -b 0.0.0.0:$PORT`
6. 点击 "Create Web Service"

## 本地运行

```bash
pip install -r requirements.txt
py web/app.py
```

访问 http://localhost:5000

## API 端点

- `GET /api/questionnaires` - 获取问卷列表
- `GET /api/questionnaire/<id>` - 获取问卷详情
- `POST /api/questionnaire/<id>/answer` - 提交答案
- `POST /api/persona/build` - 构建人格画像
- `GET /api/persona/description` - 获取画像描述

## 分享链接

部署后分享: `https://你的域名/share`
