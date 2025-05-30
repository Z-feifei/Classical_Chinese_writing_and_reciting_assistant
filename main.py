import asyncio
import os
import random
import smtplib
import string
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

from flask import Flask, request, jsonify, render_template
from flask import flash
from flask import redirect, url_for, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_
from werkzeug.security import generate_password_hash, check_password_hash

import UseModel
import split

# 创建全局事件循环（仅创建不立即设置）
global_loop = asyncio.new_event_loop()

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://feifei123:4RQl2C3Bzam1WGr4@mysql5.sqlpub.com:3310/classical_chinese'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# 邮件配置
app.config['MAIL_SERVER'] = 'smtp.qq.com'  # 以QQ邮箱为例
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@qq.com'  # 替换为您的邮箱
app.config['MAIL_PASSWORD'] = 'your-app-password'   # 替换为您的邮箱授权码

db = SQLAlchemy(app)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# 全局信号量控制并发数（最大2个并行请求）
semaphore = asyncio.Semaphore(2, loop=global_loop)


# 数据库模型
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255), default='')
    personal_tag = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    study_records = db.relationship('StudyRecord', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class StudyRecord(db.Model):
    __tablename__ = 'study_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    article_content = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer)
    study_time = db.Column(db.DateTime, default=datetime.utcnow)


class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 实虚词表模型
class LexicalParticle(db.Model):
    __tablename__ = 'lexical_particles'

    id = db.Column(db.Integer, primary_key=True)
    character = db.Column(db.String(50), nullable=False, unique=True)  # 汉字

    # 建立一对多关系
    parts_of_speech = db.relationship('PartOfSpeech', backref='particle', cascade='all, delete-orphan')


# 词性分类表模型
class PartOfSpeech(db.Model):
    __tablename__ = 'parts_of_speech'

    id = db.Column(db.Integer, primary_key=True)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 词性分类
    sub_category = db.Column(db.String(5))  # 子分类标记

    # 建立一对多关系
    definitions = db.relationship('Definition', backref='pos', cascade='all, delete-orphan')


# 释义表模型
class Definition(db.Model):
    __tablename__ = 'definitions'

    id = db.Column(db.Integer, primary_key=True)
    pos_id = db.Column(db.Integer, db.ForeignKey('parts_of_speech.id'), nullable=False)
    definition = db.Column(db.Text, nullable=False)  # 详细释义


    # 建立一对多关系
    examples = db.relationship('Example', backref='definition', cascade='all, delete-orphan')


# 例句表模型
class Example(db.Model):
    __tablename__ = 'examples'

    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(db.Integer, db.ForeignKey('definitions.id'), nullable=False)
    example = db.Column(db.Text, nullable=False)  # 文言例句

# 验证码存储（实际项目中建议使用Redis）
verification_codes = {}


# 装饰器：检查用户登录状态
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# 发送邮件函数
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        text = msg.as_string()
        server.sendmail(app.config['MAIL_USERNAME'], to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


# 生成验证码
def generate_verification_code():
    return ''.join(random.choices(string.digits, k=4))


# 更新用户信息
@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        field = request.form.get('field')
        value = request.form.get('value')

        user = User.query.get(session['user_id'])
        if field == 'personal_tag':
            user.personal_tag = value
        elif field == 'avatar':
            user.avatar = value

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


# 删除收藏
@app.route('/delete_favorite/<int:favorite_id>', methods=['DELETE'])
@login_required
def delete_favorite(favorite_id):
    try:
        favorite = Favorite.query.filter_by(id=favorite_id, user_id=session['user_id']).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '收藏不存在'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


# 添加收藏
@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    try:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')

        favorite = Favorite(
            user_id=session['user_id'],
            title=title,
            content=content
        )

        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


async def limited_execute(task_func):
    """带事件循环检查的异步执行器"""
    async with semaphore:
        return await task_func()

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('登录成功!', 'success')
            return redirect(url_for('home'))
        else:
            flash('用户名或密码错误，请检查后重试或进行注册', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已被使用', 'error')
            return render_template('register.html')

        # 检查邮箱是否已注册
        if User.query.filter_by(email=email).first():
            flash('邮箱/认证码已被注册', 'error')
            return render_template('register.html')

        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
            flash('注册成功！请登录', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('注册失败，请重试', 'error')

    return render_template('register.html')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        verification = request.form['verification']
        password = request.form['password']

        # 检查邮箱是否存在
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('请输入正确的邮箱', 'error')
            return render_template('reset_password.html')

        # 检查验证码
        if email not in verification_codes or verification_codes[email] != verification:
            flash('验证码错误', 'error')
            return render_template('reset_password.html')

        # 修改密码
        user.set_password(password)
        try:
            db.session.commit()
            # 清除验证码
            del verification_codes[email]
            # 清除会话，退出登录
            session.clear()
            flash('修改成功', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash('修改失败，请重试', 'error')

    return render_template('reset_password.html')


@app.route('/send_verification', methods=['POST'])
def send_verification():
    email = request.form['email']

    # 检查邮箱是否存在
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': False, 'message': '请输入正确的邮箱'})

    # 生成验证码
    code = generate_verification_code()
    verification_codes[email] = code

    # 发送邮件
    subject = "文言文助手 - 密码重置验证码"
    body = f"您的验证码是: {code}\n请在10分钟内使用。"

    if send_email(email, subject, body):
        return jsonify({'success': True, 'message': '验证码已发送'})
    else:
        return jsonify({'success': False, 'message': '邮件发送失败，请重试'})


@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    records = StudyRecord.query.filter_by(user_id=user.id).order_by(StudyRecord.study_time.desc()).limit(5).all()
    return render_template('profile.html', user=user, records=records)


@app.route('/history')
@login_required
def history():
    user = User.query.get(session['user_id'])
    records = StudyRecord.query.filter_by(user_id=user.id).order_by(StudyRecord.study_time.desc()).all()
    return render_template('history.html', user=user, records=records)


@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('home'))


@app.route('/exercise')
def exercise():
    return render_template('exercise.html')


@app.route('/recite')
def recite():
    """单词背诵页面 - 从数据库获取所有词汇，支持分页"""
    # 获取当前索引
    current_index = request.args.get('index', 0, type=int)

    # 获取所有词汇（使用joinedload优化查询）
    all_particles = LexicalParticle.query.options(
        db.joinedload(LexicalParticle.parts_of_speech)
            .joinedload(PartOfSpeech.definitions)
            .joinedload(Definition.examples)
    ).order_by(LexicalParticle.id).all()

    # 检查索引是否有效
    if current_index < 0:
        current_index = 0
    elif current_index >= len(all_particles):
        current_index = len(all_particles) - 1

    # 组织当前词汇数据
    current_particle = all_particles[current_index]

    parts = []
    for pos in current_particle.parts_of_speech:
        definitions = []
        for definition in pos.definitions:
            examples = [e.example for e in definition.examples]
            definitions.append({
                'text': definition.definition,
                'examples': examples
            })

        parts.append({
            'category': pos.category,
            'sub_category': pos.sub_category,
            'definitions': definitions
        })

    word_card = {
        'character': current_particle.character,
        'parts': sorted(parts, key=lambda x: x['category'])
    }

    return render_template('recite.html',
                           word_card=word_card,
                           current_index=current_index,
                           total_words=len(all_particles))

@app.route('/familiar')
def familiar():
    file_path = os.path.join(app.static_folder, 'images', 'carousel2.png')
    if os.path.exists(file_path):
        os.remove(file_path)
    return render_template('next1.html')


@app.route('/generate', methods=['POST'])
@limiter.limit("2 per second")
def generate():
    try:
        data = request.get_json()
        article = data.get('article')
        ratings = data.get('ratings')

        # 转换ratings格式
        rating_keys = ['first', 'second', 'third', 'fourth', 'fifth']
        ratings_list = [int(ratings[key]) for key in rating_keys]

        # 设置UseModel全局变量
        UseModel.content = article
        UseModel.DiffofQ1, UseModel.DiffofQ2, UseModel.DiffofQ3, UseModel.DiffofQ4, UseModel.DiffofQ5 = ratings_list

        # 在全局事件循环中执行异步任务
        async def async_wrapper():
            tasks = [
                limited_execute(UseModel.Q1),
                limited_execute(UseModel.Q2),
                limited_execute(UseModel.Q3),
                limited_execute(UseModel.Q4),
                limited_execute(UseModel.Q5)
            ]
            return await asyncio.gather(*tasks, loop=global_loop)

        # 在同步视图中运行异步任务
        results = global_loop.run_until_complete(async_wrapper())
        OutofQ1, OutofQ2, OutofQ3, OutofQ4, OutofQ5 = results

        # 写入文件
        file_path = os.path.join(app.static_folder, 'text', 'generate.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(f"{result.content}\n" for result in results)

        # 调用generate_model生成结果
        result = generate_model('generate.txt')

        # 在全局事件循环中执行异步任务
        async def async_wrapper():
            # 同时生成译文的两个部分（主翻译+注释）
            translation_task = limited_execute(UseModel.TR)
            return await translation_task

        # 在同步视图中运行异步任务
        translation = global_loop.run_until_complete(async_wrapper())
        print(translation.content)


        return jsonify({
            'article': article,
            'questions': result['questions'],
            'answers': result['answers'],
            'translation': translation.content
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_model(filename):
    questions = {}
    answers = {}
    nums = [1, 2, 3, 4, 5]
    file_path = os.path.join(app.static_folder, 'text', filename)
    result = split.read_and_parse_file(file_path, nums)
    for num in nums:
        questions[f'question{num}'] = result['questions'][f'question{num}']
        answers[f'answer{num}'] = result['answers'][f'answer{num}']
    return {'questions': questions, 'answers': answers}

@app.route('/regenerate/<nums>', methods=['POST'])
@limiter.limit("2 per second")
def regenerate(nums):
    try:
        nums = list(map(int, nums.split(',')))

        # 在全局事件循环中执行异步任务
        async def async_wrapper():
            task_map = {
                1: UseModel.Q1,
                2: UseModel.Q2,
                3: UseModel.Q3,
                4: UseModel.Q4,
                5: UseModel.Q5
            }
            tasks = [limited_execute(task_map[num]) for num in nums]
            return await asyncio.gather(*tasks, loop=global_loop)

        results = global_loop.run_until_complete(async_wrapper())

        # 写入文件
        file_path = os.path.join(app.static_folder, 'text', 'regenerate.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(f"{result.content}\n" for result in results)

        # 返回结果
        if nums == [1, 2, 3, 4, 5]:
            result_data = generate_model('regenerate.txt')
        else:
            result_data = regenerate_model(nums)
        return jsonify(result_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def regenerate_model(nums):
    questions = {}
    answers = {}
    file_path = os.path.join(app.static_folder, 'text', 'regenerate.txt')
    result = split.read_and_parse_file(file_path, nums)
    for num in nums:
        questions[f'question{num}'] = result['questions'][f'question{num}']
        answers[f'answer{num}'] = result['answers'][f'answer{num}']
    return {'questions': questions, 'answers': answers}

@app.route('/api/lexicon')
def lexicon_data():
    """词库数据API（支持搜索和分类筛选）"""
    # 获取请求参数
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    categories = request.args.get('categories', '').split(',') if 'categories' in request.args else []
    per_page = 3
    main_categories = {'连词', '助词', '语气词', '比况词', '代词', '副词', '介词', '形容词'}

    # 构建基础查询
    base_query = LexicalParticle.query

    # 分类过滤条件
    category_filters = []
    if categories:
        # 特殊处理"其他"分类
        other_selected = '其他' in categories
        valid_categories = [c for c in categories if c in main_categories or c == '其他']

        # 构建分类条件
        if valid_categories:
            conditions = []
            if '其他' in valid_categories:
                # 其他分类的条件：原分类不在主分类列表中
                conditions.append(~PartOfSpeech.category.in_(main_categories))
                valid_categories.remove('其他')
            if valid_categories:
                conditions.append(PartOfSpeech.category.in_(valid_categories))

            if conditions:
                category_filters = [or_(*conditions)] if len(conditions) > 1 else conditions

    # 搜索条件
    search_filters = []
    if search_query:
        search_filters.append(LexicalParticle.character.ilike(f'%{search_query}%'))

    # 组合所有条件
    if category_filters or search_filters:
        base_query = base_query.join(PartOfSpeech)
        if category_filters and search_filters:
            base_query = base_query.filter(and_(*category_filters, *search_filters))
        else:
            base_query = base_query.filter(or_(*(category_filters + search_filters)))
        base_query = base_query.distinct()

    # 执行分页查询（优化关联加载）
    pagination = base_query.options(
        db.joinedload(LexicalParticle.parts_of_speech)
          .joinedload(PartOfSpeech.definitions)
          .joinedload(Definition.examples)
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # 处理返回数据
    processed_data = []
    for particle in pagination.items:
        parts = []
        for pos in particle.parts_of_speech:
            # 分类处理
            main_cat = pos.category if pos.category in main_categories else '其他'
            display = f"{pos.category}{f'({pos.sub_category})' if pos.sub_category else ''}"

            # 处理定义和例句
            definitions = [{
                "definition": d.definition,
                "examples": [e.example for e in d.examples]
            } for d in pos.definitions]

            parts.append({
                "main_category": main_cat,
                "display_category": display,
                "definitions": definitions
            })

        processed_data.append({
            "character": particle.character,
            "parts_of_speech": parts
        })

    return jsonify({
        "data": processed_data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })
@app.route('/lexicon', endpoint='lexicon')
def lexicon_page():
    """词库页面路由"""
    return render_template('lexicon.html')
@app.route('/personal')
def personal():
    return render_template('profile.html')

if __name__ == '__main__':
    # 设置全局事件循环
    asyncio.set_event_loop(global_loop)
    try:
        from hypercorn.asyncio import serve
        from hypercorn.config import Config
        config = Config()
        config.bind = ["127.0.0.1:8000"]
        global_loop.run_until_complete(serve(app, config))
    except ImportError:
        # 如果未安装hypercorn则回退到Flask开发服务器
        app.run(host='127.0.0.1', port=8000, debug=True, use_reloader=False)