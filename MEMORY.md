# MEMORY.md - Long-term Memory

## 数字人AI - 人格问卷系统 (P1项目)

### 部署信息
- **GitHub仓库**: https://github.com/cuizheng198604-glitch/digital-human-ai
- **Render生产环境**: https://digital-human-ai.onrender.com
- **独立问卷H5**: https://digital-human-ai.onrender.com/standalone
- **管理后台**: https://digital-human-ai.onrender.com/admin

### 技术栈
- 后端: Flask + Gunicorn (Python)
- 前端: 移动端H5 + CSS响应式设计
- 数据库: JSON文件 (data/questionnaire_db.json, data/users_db.json)
- 依赖: flask, flask-cors, gunicorn, numpy

### 核心功能
1. 用户注册/登录
2. 四套人格问卷 (大五人格、社交类型、价值观、兴趣)
3. 人格向量计算与可视化
4. 独立问卷分享页 (standalone_questionnaire.html)
5. 管理后台 (admin.html) - 查看所有用户答题数据

### 项目结构
```
digital_human_ai/
├── web/
│   ├── app.py          # Flask后端
│   ├── index.html      # 主页
│   ├── questionnaire.html
│   ├── login.html
│   ├── register.html
│   ├── persona.html
│   ├── share.html
│   ├── admin.html      # 管理后台 (新增)
│   └── standalone_questionnaire.html
├── data/               # JSON数据库
├── model/              # 模型相关
├── requirements.txt
└── standalone_questionnaire.html
```

### 网络问题记录
- GitHub连接不稳定，有时需要多次重试
- Git认证用Token (已在远程配置中)
- 命令: `git remote set-url origin https://cuizheng198604-glitch:<TOKEN>@github.com/cuizheng198604-glitch/digital-human-ai.git`

### 启动命令
本地: `cd C:\Users\Administrator\Projects\digital_human_ai && py web/app.py`
Render: `gunicorn web.app:app -b 0.0.0.0:$PORT`
