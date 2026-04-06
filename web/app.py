# -*- coding: utf-8 -*-
"""
Digital Human AI - 问卷系统后端 API
基于 Flask，提供 RESTful API
"""
import os
import sys
import json
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS

from modeling.personality_encoder import PersonalityEncoder, UserPersona, BigFiveTraits
from modeling.social_media_collector import SocialMediaCollector
from engine.llm_engine import LLMEngine
from questionnaire.questionnaire_engine import QuestionnaireEngine, QuestionType
from engine.memory_retriever import MemoryRetriever
app = Flask(__name__, static_folder='../web', static_url_path='')
CORS(app)

app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), '..', 'data', 'questionnaire_db.json')
app.config['USERS_FILE'] = os.path.join(os.path.dirname(__file__), '..', 'data', 'users_db.json')

# ==================== 数据存储 ====================

def load_json(path, default):
    """加载 JSON 文件"""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_json(path, data):
    """保存 JSON 文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_db():
    """获取数据库"""
    return load_json(app.config['DATABASE'], {
        "sessions": {},
        "answers": {},  # {session_id: {questionnaire_id: [answers]}}
        "progress": {},  # {session_id: {questionnaire_id: current_index}}
        "results": {},  # {session_id: final_persona}
        "analysis": {}  # {session_id: analysis_results}
    })

def get_users():
    """获取用户库"""
    return load_json(app.config['USERS_FILE'], {
        "users": {}  # {user_id: {user_id, username, password_hash, created_at}}
    })

def save_db(data):
    """保存数据库"""
    save_json(app.config['DATABASE'], data)

def save_users(data):
    """保存用户库"""
    save_json(app.config['USERS_FILE'], data)

# ==================== 认证 ====================

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_token():
    """创建会话 Token"""
    return secrets.token_urlsafe(32)

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({"error": "未提供认证令牌"}), 401
        
        db = get_db()
        if token not in db['sessions']:
            return jsonify({"error": "无效的会话"}), 401
        
        g.session_id = token
        g.user_id = db['sessions'][token]['user_id']
        return f(*args, **kwargs)
    return decorated

# ==================== 认证 API ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "密码长度至少6位"}), 400
    
    users_db = get_users()
    
    # 检查用户名是否存在
    for uid, user in users_db['users'].items():
        if user['username'] == username:
            return jsonify({"error": "用户名已存在"}), 400
    
    # 创建用户
    user_id = str(uuid.uuid4())[:8]
    users_db['users'][user_id] = {
        "user_id": user_id,
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat()
    }
    save_users(users_db)
    
    # 创建会话
    token = create_token()
    db = get_db()
    db['sessions'][token] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
    }
    save_db(db)
    
    return jsonify({
        "token": token,
        "user_id": user_id,
        "username": username
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    users_db = get_users()
    
    # 查找用户
    user = None
    for uid, u in users_db['users'].items():
        if u['username'] == username and u['password_hash'] == hash_password(password):
            user = u
            break
    
    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401
    
    # 创建会话
    token = create_token()
    db = get_db()
    db['sessions'][token] = {
        "user_id": user['user_id'],
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
    }
    save_db(db)
    
    return jsonify({
        "token": token,
        "user_id": user['user_id'],
        "username": username
    })

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """用户登出"""
    db = get_db()
    if g.session_id in db['sessions']:
        del db['sessions'][g.session_id]
        save_db(db)
    return jsonify({"success": True})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """获取当前用户信息"""
    users_db = get_users()
    user = users_db['users'].get(g.user_id, {})
    
    return jsonify({
        "user_id": user.get('user_id'),
        "username": user.get('username'),
        "created_at": user.get('created_at')
    })

# ==================== 问卷 API ====================

# 初始化问卷引擎
questionnaire_engine = QuestionnaireEngine()
# 初始化记忆检索器
memory_retriever = MemoryRetriever(
    llm_engine=None,
    config={"embedding_dimension": 128},
    storage_dir=os.path.join(os.path.dirname(__file__), '..', 'data')
)
@app.route('/api/questionnaires', methods=['GET'])
def get_questionnaires():
    """获取所有问卷列表"""
    questionnaires = questionnaire_engine.get_all_questionnaires()
    
    return jsonify({
        "questionnaires": [
            {
                "id": q.id,
                "name": q.name,
                "description": q.description,
                "question_count": len(q.questions),
                "estimated_time": q.estimated_time
            }
            for q in questionnaires
        ]
    })

@app.route('/api/questionnaire/<questionnaire_id>', methods=['GET'])
def get_questionnaire(questionnaire_id):
    """获取问卷详情"""
    questionnaire = questionnaire_engine.get_questionnaire(questionnaire_id)
    
    if not questionnaire:
        return jsonify({"error": "问卷不存在"}), 404
    
    questions = []
    for q in questionnaire.questions:
        questions.append({
            "id": q.id,
            "type": q.type.value,
            "text": q.text,
            "options": q.options,
            "scale_range": list(q.scale_range),
            "dimension": q.dimension
        })
    
    return jsonify({
        "id": questionnaire.id,
        "name": questionnaire.name,
        "description": questionnaire.description,
        "estimated_time": questionnaire.estimated_time,
        "questions": questions
    })

@app.route('/api/questionnaire/<questionnaire_id>/answer', methods=['POST'])
@require_auth
def submit_answer(questionnaire_id):
    """提交答案"""
    data = request.get_json()
    question_id = data.get('question_id')
    answer = data.get('answer')
    
    if question_id is None or answer is None:
        return jsonify({"error": "缺少必要参数"}), 400
    
    db = get_db()
    
    # 确保用户数据结构存在
    if g.user_id not in db['answers']:
        db['answers'][g.user_id] = {}
    if questionnaire_id not in db['answers'][g.user_id]:
        db['answers'][g.user_id][questionnaire_id] = []
    
    # 检查是否已回答过该题
    existing_answers = db['answers'][g.user_id][questionnaire_id]
    for i, a in enumerate(existing_answers):
        if a['question_id'] == question_id:
            existing_answers[i] = {
                "question_id": question_id,
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            }
            save_db(db)
            return jsonify({"success": True, "updated": True})
    
    # 添加新答案
    existing_answers.append({
        "question_id": question_id,
        "answer": answer,
        "timestamp": datetime.now().isoformat()
    })
    save_db(db)
    
    return jsonify({"success": True, "updated": False})

@app.route('/api/questionnaire/<questionnaire_id>/progress', methods=['GET'])
@require_auth
def get_progress(questionnaire_id):
    """获取问卷进度"""
    db = get_db()
    answers = db['answers'].get(g.user_id, {}).get(questionnaire_id, [])
    
    return jsonify({
        "completed_count": len(answers),
        "completed_ids": [a['question_id'] for a in answers]
    })

@app.route('/api/questionnaire/<questionnaire_id>/submit', methods=['POST'])
@require_auth
def submit_questionnaire(questionnaire_id):
    """提交问卷并分析"""
    db = get_db()
    answers = db['answers'].get(g.user_id, {}).get(questionnaire_id, [])
    
    if not answers:
        return jsonify({"error": "请先完成问卷"}), 400
    
    # 计算分数
    questionnaire = questionnaire_engine.get_questionnaire(questionnaire_id)
    if not questionnaire:
        return jsonify({"error": "问卷不存在"}), 404
    
    dimension_scores = {}
    for answer_data in answers:
        qid = answer_data['question_id']
        answer = answer_data['answer']
        
        # 找到题目
        question = None
        for q in questionnaire.questions:
            if q.id == qid:
                question = q
                break
        
        if not question or not question.dimension:
            continue
        
        # 计算分数
        score = 0.0
        if question.type == QuestionType.SCALE and isinstance(answer, int):
            score = answer / question.scale_range[1]
            if question.reverse_score:
                score = 1 - score
        
        if question.dimension not in dimension_scores:
            dimension_scores[question.dimension] = []
        dimension_scores[question.dimension].append(score)
    
    # 计算各维度平均分
    dimension_avg = {}
    for dim, scores in dimension_scores.items():
        if scores:
            dimension_avg[dim] = sum(scores) / len(scores)
    
    # 保存分析结果
    if g.user_id not in db['analysis']:
        db['analysis'][g.user_id] = {}
    db['analysis'][g.user_id][questionnaire_id] = {
        "dimension_scores": dimension_scores,
        "dimension_avg": dimension_avg,
        "submitted_at": datetime.now().isoformat()
    }
    save_db(db)
    
    return jsonify({
        "success": True,
        "dimension_avg": dimension_avg
    })

# ==================== 人格分析 API ====================

@app.route('/api/persona/build', methods=['POST'])
@require_auth
def build_persona():
    """构建用户人格画像"""
    db = get_db()
    
    # 收集所有问卷结果
    all_results = {}
    user_answers = db['answers'].get(g.user_id, {})
    
    for qid, answers in user_answers.items():
        questionnaire = questionnaire_engine.get_questionnaire(qid)
        if not questionnaire:
            continue
        
        # 计算分数
        dimension_scores = {}
        for answer_data in answers:
            qid_inner = answer_data['question_id']
            answer = answer_data['answer']
            
            question = None
            for q in questionnaire.questions:
                if q.id == qid_inner:
                    question = q
                    break
            
            if not question or not question.dimension:
                continue
            
            score = 0.0
            if question.type == QuestionType.SCALE and isinstance(answer, int):
                score = answer / question.scale_range[1]
                if question.reverse_score:
                    score = 1 - score
            
            if question.dimension not in dimension_scores:
                dimension_scores[question.dimension] = []
            dimension_scores[question.dimension].append(score)
        
        dimension_avg = {}
        for dim, scores in dimension_scores.items():
            if scores:
                dimension_avg[dim] = sum(scores) / len(scores)
        
        if dimension_avg:
            all_results[qid] = dimension_avg
    
    # 构建人格画像
    encoder = PersonalityEncoder()
    questionnaire_results = {}
    for qid, dims in all_results.items():
        questionnaire_results[qid] = [
            {"dimension": dim, "score": score}
            for dim, score in dims.items()
        ]
    
    # 传递原始答案用于提取兴趣和价值观
    persona = encoder.build_persona(
        user_id=g.user_id,
        questionnaire_results=questionnaire_results,
        raw_answers=user_answers
    )
    
    # 保存画像 (完整数据)
        if g.user_id not in db['results']:
             db['results'][g.user_id] = {}
        db['results'][g.user_id] = {
             "persona": persona.to_dict(),
             "built_at": datetime.now().isoformat()
        }
        save_db(db)

    # 存入记忆系统
    try:
        if persona.interests:
            for interest in persona.interests:
                memory_retriever.add_fact(
                    user_id=g.user_id,
                    fact=f"用户兴趣领域: {interest}",
                    fact_type="interest",
                    importance=0.7,
                    metadata={"source": "persona_build"}
                )

        if persona.values:
            for value in persona.values:
                memory_retriever.add_fact(
                    user_id=g.user_id,
                    fact=f"用户价值观: {value}",
                    fact_type="value",
                    importance=0.6,
                    metadata={"source": "persona_build"}
                )

        memory_retriever.add_fact(
            user_id=g.user_id,
            fact=f"大五人格: 开放性={persona.big_five.openness:.2f}, 尽责性={persona.big_five.conscientiousness:.2f}, 外向性={persona.big_five.extraversion:.2f}, 宜人性={persona.big_five.agreeableness:.2f}, 神经质={persona.big_five.neuroticism:.2f}",
            fact_type="big_five",
            importance=0.8,
            metadata={"source": "persona_build"}
        )

        memory_retriever.save_all()
    except Exception as e:
        print(f"Warning: Failed to store memory: {e}")

    return jsonify({
        "success": True,
        "persona": persona.to_dict()
    })

    # 存入记忆系统
    try:
        if persona.interests:
            for interest in persona.interests:
                memory_retriever.add_fact(
                    user_id=g.user_id,
                    fact=f"用户兴趣领域: {interest}",
                    fact_type="interest",
                    importance=0.7,
                    metadata={"source": "persona_build"}
                )

        if persona.values:
            for value in persona.values:
                memory_retriever.add_fact(
                    user_id=g.user_id,
                    fact=f"用户价值观: {value}",
                    fact_type="value",
                    importance=0.6,
                    metadata={"source": "persona_build"}
                )

        memory_retriever.add_fact(
            user_id=g.user_id,
            fact=f"大五人格: 开放性={persona.big_five.openness:.2f}, 尽责性={persona.big_five.conscientiousness:.2f}, 外向性={persona.big_five.extraversion:.2f}, 宜人性={persona.big_five.agreeableness:.2f}, 神经质={persona.big_five.neuroticism:.2f}",
            fact_type="big_five",
            importance=0.8,
            metadata={"source": "persona_build"}
        )

        memory_retriever.save_all()
    except Exception as e:
        print(f"Warning: Failed to store memory: {e}")

    return jsonify({
        "success": True,
        "persona": persona.to_dict()
    })

 # ====== 存入记忆系统 ======
 if persona.interests:
     for interest in persona.interests:
         memory_retriever.add_fact(
             user_id=g.user_id,
             fact=f"用户兴趣领域: {interest}",
             fact_type="interest",
             importance=0.7,
             metadata={"source": "persona_build"}
         )

 if persona.values:
     for value in persona.values:
         memory_retriever.add_fact(
             user_id=g.user_id,
             fact=f"用户价值观: {value}",
             fact_type="value",
             importance=0.6,
             metadata={"source": "persona_build"}
         )

 memory_retriever.add_fact(
     user_id=g.user_id,
     fact=f"大五人格: 开放性={persona.big_five.openness:.2f}, 尽责性={persona.big_five.conscientiousness:.2f}, 外向性={persona.big_five.extraversion:.2f}, 宜人性={persona.big_five.agreeableness:.2f}, 神经质={persona.big_five.neuroticism:.2f}",
     fact_type="big_five",
     importance=0.8,
     metadata={"source": "persona_build"}
 )

 memory_retriever.save_all()

 return jsonify({
     "success": True,
     "persona": persona.to_dict()
 })

 # ====== 存入记忆系统 ======
 if persona.interests:
     for interest in persona.interests:
         memory_retriever.add_fact(
             user_id=g.user_id,
             fact=f"用户兴趣领域: {interest}",
             fact_type="interest",
             importance=0.7,
             metadata={"source": "persona_build"}
         )

 if persona.values:
     for value in persona.values:
         memory_retriever.add_fact(
             user_id=g.user_id,
             fact=f"用户价值观: {value}",
             fact_type="value",
             importance=0.6,
             metadata={"source": "persona_build"}
         )

 # 存储大五人格
 memory_retriever.add_fact(
     user_id=g.user_id,
     fact=f"大五人格: 开放性={persona.big_five.openness:.2f}, 尽责性={persona.big_five.conscientiousness:.2f}, 外向性={persona.big_five.extraversion:.2f}, 宜人性={persona.big_five.agreeableness:.2f}, 神经质={persona.big_five.neuroticism:.2f}",
     fact_type="big_five",
     importance=0.8,
     metadata={"source": "persona_build"}
 )

 # 保存记忆
 memory_retriever.save_all()

 return jsonify({
     "success": True,
     "persona": persona.to_dict()
 })

@app.route('/api/persona', methods=['GET'])
@require_auth
def get_persona():
    """获取用户人格画像"""
    db = get_db()
    result = db['results'].get(g.user_id)
    
    if not result:
        return jsonify({"error": "尚未构建人格画像"}), 404
    
    return jsonify(result)

@app.route('/api/persona/description', methods=['GET'])
@require_auth
def get_persona_description():
    """获取人格画像描述"""
    db = get_db()
    result = db['results'].get(g.user_id)
    
    if not result:
        return jsonify({"error": "尚未构建人格画像"}), 404
    
    persona_data = result.get('persona', {})
    persona = UserPersona.from_dict(persona_data)
    
    encoder = PersonalityEncoder()
    description = encoder.generate_personality_description(persona)
    
    return jsonify({
        "description": description,
        "big_five": persona.big_five.to_vector(),
        "traits": {
            "openness": persona.big_five.openness,
            "conscientiousness": persona.big_five.conscientiousness,
            "extraversion": persona.big_five.extraversion,
            "agreeableness": persona.big_five.agreeableness,
            "neuroticism": persona.big_five.neuroticism
        }
    })
# ==================== 对话记忆 API ====================

@app.route('/api/memory/conversation', methods=['POST'])
@require_auth
def add_conversation_memory():
    """添加对话记忆"""
    data = request.get_json()
    content = data.get('content', '')
    role = data.get('role', 'user')
    session_id = data.get('session_id', g.user_id)
    
    if not content:
        return jsonify({"error": "内容不能为空"}), 400
    
    memory_retriever.add_conversation(
        session_id=session_id,
        role=role,
        content=content,
        user_id=g.user_id
    )
    
    return jsonify({"success": True})


@app.route('/api/memory/retrieve', methods=['GET'])
@require_auth
def retrieve_memories():
    """检索相关记忆"""
    query = request.args.get('query', '')
    session_id = request.args.get('session_id', g.user_id)
    
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400
    
    results = memory_retriever.retrieve(
        query=query,
        user_id=g.user_id,
        session_id=session_id,
        top_k=5
    )
    
    return jsonify(results)


@app.route('/api/memory/context', methods=['GET'])
@require_auth
def get_memory_context():
    """获取RAG上下文字符串"""
    query = request.args.get('query', '')
    session_id = request.args.get('session_id', g.user_id)
    
    if not query:
        return jsonify({"error": "查询内容不能为空"}), 400
    
    context = memory_retriever.build_rag_context(
        query=query,
        user_id=g.user_id,
        session_id=session_id
    )
    
    return jsonify({"context": context})


@app.route('/api/memory/summary', methods=['GET'])
@require_auth
def get_memory_summary():
    """获取用户记忆摘要"""
    summary = memory_retriever.get_user_memories_summary(g.user_id)
    return jsonify(summary)


@app.route('/api/memory/clear', methods=['POST'])
@require_auth
def clear_user_memories():
    """清除用户所有记忆"""
    memory_retriever.clear_user_memory(g.user_id)
    return jsonify({"success": True})

# ==================== 仪表盘 API ====================

@app.route('/api/dashboard', methods=['GET'])
@require_auth
def get_dashboard():
    """获取仪表盘数据"""
    db = get_db()
    
    # 问卷完成情况
    all_questionnaires = questionnaire_engine.get_all_questionnaires()
    completed = []
    pending = []
    
    user_answers = db['answers'].get(g.user_id, {})
    for q in all_questionnaires:
        if q.id in user_answers and user_answers[q.id]:
            completed.append({
                "id": q.id,
                "name": q.name,
                "answered_count": len(user_answers[q.id])
            })
        else:
            pending.append({
                "id": q.id,
                "name": q.name,
                "question_count": len(q.questions)
            })
    
    # 人格画像状态
    persona_status = "not_started"
    persona_data = db['results'].get(g.user_id)
    if persona_data:
        persona_status = "completed"
    
    # 社交媒体数据
    analysis = db['analysis'].get(g.user_id, {})
    
    return jsonify({
        "user_id": g.user_id,
        "questionnaire_status": {
            "total": len(all_questionnaires),
            "completed": len(completed),
            "pending": pending,
            "completed_list": completed
        },
        "persona_status": persona_status,
        "analysis_available": len(analysis) > 0
    })

# ==================== 静态文件 ====================

@app.route('/')
def index():
    """首页"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/questionnaire')
def questionnaire_page():
    """问卷页面"""
    return send_from_directory(app.static_folder, 'questionnaire.html')

@app.route('/persona')
def persona_page():
    """人格画像页面"""
    return send_from_directory(app.static_folder, 'persona.html')

@app.route('/login')
def login_page():
    """登录页面"""
    return send_from_directory(app.static_folder, 'login.html')

@app.route('/register')
def register_page():
    """注册页面"""
    return send_from_directory(app.static_folder, 'register.html')

@app.route('/share')
def share_page():
    """分享页面"""
    return send_from_directory(app.static_folder, 'share.html')

@app.route('/standalone')
def standalone_page():
    """独立问卷页面"""
    return send_from_directory(app.static_folder, 'standalone_questionnaire.html')

@app.route('/admin')
def admin_page():
    """管理后台页面"""
    return send_from_directory(app.static_folder, 'admin.html')

@app.route('/api/admin/all-data')
def admin_all_data():
    """获取所有用户数据"""
    db = get_db()
    users_db = get_users()
    
    all_users = []
    for uid, user in users_db['users'].items():
        user_answers = db['answers'].get(uid, {})
        answer_count = sum(len(answers) for answers in user_answers.values())
        has_persona = uid in db['results']
        persona = db['results'].get(uid, {}).get('persona') if has_persona else None
        
        all_users.append({
            'user_id': uid,
            'username': user.get('username', ''),
            'created_at': user.get('created_at', ''),
            'answer_count': answer_count,
            'has_persona': has_persona,
            'persona': persona
        })
    
    return jsonify({'users': all_users})

@app.route('/api/admin/recalculate-all', methods=['POST'])
def admin_recalculate_all():
    """重新计算所有用户的人格画像（修复50%问题）"""
    db = get_db()
    users_db = get_users()
    
    encoder = PersonalityEncoder()
    recalculated = 0
    errors = []
    
    for uid, user in users_db['users'].items():
        user_answers = db['answers'].get(uid, {})
        if not user_answers:
            continue
        
        # 构建问卷结果
        questionnaire_results = {}
        for qid, answers in user_answers.items():
            questionnaire = questionnaire_engine.get_questionnaire(qid)
            if not questionnaire:
                continue
            
            dimension_scores = {}
            for answer_data in answers:
                qid_inner = answer_data['question_id']
                answer = answer_data['answer']
                
                question = None
                for q in questionnaire.questions:
                    if q.id == qid_inner:
                        question = q
                        break
                
                if not question or not question.dimension:
                    continue
                
                score = 0.0
                if question.type == QuestionType.SCALE and isinstance(answer, int):
                    score = answer / question.scale_range[1]
                    if question.reverse_score:
                        score = 1 - score
                
                if question.dimension not in dimension_scores:
                    dimension_scores[question.dimension] = []
                dimension_scores[question.dimension].append(score)
            
            if dimension_scores:
                questionnaire_results[qid] = [
                    {"dimension": dim, "score": score}
                    for dim, scores in dimension_scores.items()
                    for score in scores
                ]
        
        if questionnaire_results:
            try:
                persona = encoder.build_persona(
                    user_id=uid,
                    questionnaire_results=questionnaire_results,
                    raw_answers=user_answers  # 传递原始答案用于提取兴趣和价值观
                )
                
                db['results'][uid] = {
                    "persona": persona.to_dict(),
                    "built_at": datetime.now().isoformat()
                }
                recalculated += 1
            except Exception as e:
                errors.append({"user_id": uid, "error": str(e)})
    
    save_db(db)
    
    return jsonify({
        "success": True,
        "recalculated": recalculated,
        "total_users": len(users_db['users']),
        "errors": errors
    })

# ==================== 启动 ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'='*50}")
    print("数字人 AI - 问卷系统")
    print(f"{'='*50}")
    print(f"\n移动端访问地址: http://localhost:{port}")
    print(f"问卷页面: http://localhost:{port}/questionnaire")
    print(f"人格画像: http://localhost:{port}/persona")
    print("\n按 Ctrl+C 停止服务器\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
