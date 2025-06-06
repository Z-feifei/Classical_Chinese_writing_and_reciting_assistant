import asyncio
import os
import random
import smtplib
import string
from datetime import datetime
from datetime import timedelta  # 修改此处，导入timedelta
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
from sqlalchemy import func  # 添加导入func
from werkzeug.security import generate_password_hash, check_password_hash

import UseModel
import split

# 创建全局事件循环（仅创建不立即设置）
global_loop = asyncio.new_event_loop()

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'

app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://feifei123:4RQl2C3Bzam1WGr4@mysql5.sqlpub.com:3310/classical_chinese'
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
app.config['MAIL_PASSWORD'] = 'your-app-password'  # 替换为您的邮箱授权码

db = SQLAlchemy(app)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# 全局信号量控制并发数（最大2个并行请求）
semaphore = asyncio.Semaphore(2, loop=global_loop)


# 用户系统数据模型
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
    # study_records = db.relationship('StudyRecord', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# 用户背诵进度模型
class RecitationProgress(db.Model):
    __tablename__ = 'recitation_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    last_studied = db.Column(db.DateTime, default=datetime.utcnow)
    mastery_level = db.Column(db.Integer, default=0)  # 0-陌生, 1-熟悉, 2-掌握
    wrong_count = db.Column(db.Integer, default=0)
    right_count = db.Column(db.Integer, default=0)

    # 关系
    user = db.relationship('User', backref=db.backref('progress', lazy=True, cascade='all, delete-orphan'))
    particle = db.relationship('LexicalParticle')


# 用户背词记录模型
class VocabularyRecord(db.Model):
    __tablename__ = 'vocabulary_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    study_time = db.Column(db.DateTime, default=datetime.utcnow)
    wrong_example_ids = db.Column(db.JSON)  # 存储答错的例句ID
    correct_answer_ids = db.Column(db.JSON)  # 存储正确答案的释义ID
    user_answers = db.Column(db.JSON)  # 存储用户选择的答案

    # 关系
    particle = db.relationship('LexicalParticle')


# 用户收藏题目模型
class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)  # 文章内容
    question = db.Column(db.Text)  # 题目
    answer = db.Column(db.Text)  # 答案
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# 实词库数据模型
class LexicalParticle(db.Model):
    __tablename__ = 'lexical_particles'

    id = db.Column(db.Integer, primary_key=True)
    character = db.Column(db.String(50), nullable=False, unique=True)  # 汉字

    # 建立一对多关系
    parts_of_speech = db.relationship('PartOfSpeech', backref='particle', cascade='all, delete-orphan')


class PartOfSpeech(db.Model):
    __tablename__ = 'parts_of_speech'

    id = db.Column(db.Integer, primary_key=True)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 词性分类
    sub_category = db.Column(db.String(5))  # 子分类标记

    # 建立一对多关系
    definitions = db.relationship('Definition', backref='pos', cascade='all, delete-orphan')


class Definition(db.Model):
    __tablename__ = 'definitions'

    id = db.Column(db.Integer, primary_key=True)
    pos_id = db.Column(db.Integer, db.ForeignKey('parts_of_speech.id'), nullable=False)
    definition = db.Column(db.Text, nullable=False)  # 详细释义

    # 建立一对多关系
    examples = db.relationship('Example', backref='definition', cascade='all, delete-orphan')


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


# 添加收藏
@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    try:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        question = data.get('question')  # 获取问题
        answer = data.get('answer')  # 获取答案

        favorite = Favorite(
            user_id=session['user_id'],
            title=title,
            content=content,
            question=question,
            answer=answer
        )

        db.session.add(favorite)
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


# 学习进度
@app.route('/api/study_progress', methods=['GET'])
@login_required
def get_study_progress():
    user_id = session['user_id']

    # 查询用户的学习进度
    progress_records = RecitationProgress.query.filter_by(user_id=user_id).all()

    # 统计各掌握级别的词汇数量
    stats = {
        'mastered': 0,  # mastery_level=2
        'familiar': 0,  # mastery_level=1
        'unfamiliar': 0,  # mastery_level=0
        'total': LexicalParticle.query.count()  # 总词汇量
    }

    # 收集词汇列表
    mastered_words = []
    unfamiliar_words = []

    # 按掌握级别分组
    for record in progress_records:
        if record.mastery_level == 2:
            stats['mastered'] += 1
            mastered_words.append(record.particle.character)
        elif record.mastery_level == 1:
            stats['familiar'] += 1
        else:
            stats['unfamiliar'] += 1
            unfamiliar_words.append(record.particle.character)

    # 添加未学习过的词汇到陌生词汇列表
    all_words = [p.character for p in LexicalParticle.query.all()]
    never_studied = set(all_words) - set(mastered_words) - set(unfamiliar_words)
    stats['unfamiliar'] += len(never_studied)
    unfamiliar_words.extend(never_studied)

    # 生成燃尽图数据（过去30天的学习记录）
    burndown_data = []
    today = datetime.utcnow().date()
    mastered_by_date = {}

    # 查询过去30天内掌握的词
    for i in range(30):
        date = today - timedelta(days=i)
        mastered_by_date[date.strftime('%Y-%m-%d')] = 0

    # 查询每天掌握的词
    mastered_records = db.session.query(
        func.date(RecitationProgress.last_studied).label('study_date'),
        func.count().label('count')
    ).filter(
        RecitationProgress.user_id == user_id,
        RecitationProgress.mastery_level == 2,
        func.date(RecitationProgress.last_studied) >= today - timedelta(days=30)
    ).group_by('study_date').all()

    # 填充燃尽图数据
    cumulative = 0
    for i in range(30):
        date = today - timedelta(days=30 - i)
        date_str = date.strftime('%Y-%m-%d')

        # 查找当天掌握的词
        daily_count = next((record[1] for record in mastered_records if record[0] == date), 0)
        cumulative += daily_count

        burndown_data.append({
            'date': date_str,
            'mastered': cumulative
        })

    return jsonify({
        'stats': stats,
        'mastered_words': mastered_words,
        'unfamiliar_words': list(unfamiliar_words),
        'burndown_data': burndown_data
    })


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
    records = VocabularyRecord.query.filter_by(user_id=user.id).order_by(VocabularyRecord.study_time.desc()).limit(
        5).all()
    return render_template('profile.html', user=user, records=records)


@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('home'))


@app.route('/exercise')
def exercise():
    return render_template('exercise.html')

@app.route('/recite', methods=['GET', 'POST'])
@login_required
def recite():
    """单词背诵页面 - 智能背诵机制"""
    # 获取当前索引
    current_index = request.args.get('index', 0, type=int)

    # 获取用户ID
    user_id = session['user_id']

    # 查询用户的学习进度
    progress_records = RecitationProgress.query.filter_by(user_id=user_id).all()

    # 获取所有词汇（使用joinedload优化查询）
    all_particles = LexicalParticle.query.options(
        db.joinedload(LexicalParticle.parts_of_speech)
        .joinedload(PartOfSpeech.definitions)
        .joinedload(Definition.examples)
    ).all()

    # 修改1: 过滤出未掌握的词汇（掌握级别小于2的词汇）
    def is_unmastered(particle):
        # 查找该词汇的用户学习记录
        progress = next((p for p in progress_records if p.particle_id == particle.id), None)
        return not progress or progress.mastery_level < 2

    # 创建未掌握的词汇列表
    unmastered_particles = [p for p in all_particles if is_unmastered(p)]
    total_unmastered = len(unmastered_particles)  # 未掌握的词汇总数

    # 修改sort_key函数，排除已掌握的词汇
    def sort_key(particle):
        # 查找该词汇的用户学习记录
        progress = next((p for p in progress_records if p.particle_id == particle.id), None)

        # 如果已经掌握，优先级最低（确保不会出现）
        if progress and progress.mastery_level == 2:
            return (999, 0, 0, particle.id)  # 最高数字确保排在最后

        # 如果还没有学习记录，优先显示
        if not progress:
            return (0, 0, 0, particle.id)  # 优先级最高

        # 计算权重：错误次数 + (当前时间 - 上次学习时间) * 系数
        time_passed = (datetime.utcnow() - progress.last_studied).total_seconds() / 3600  # 小时
        weight = progress.wrong_count + time_passed * 0.1

        # 按照权重降序排序（权重高的先出现）
        return (-weight, progress.wrong_count, -progress.right_count, particle.id)

    # 根据智能算法排序
    sorted_particles = sorted(all_particles, key=sort_key)

    # 修改2: 过滤掉已掌握的词汇
    sorted_particles = [p for p in sorted_particles if is_unmastered(p)]

    # 检查索引是否有效
    if current_index < 0:
        current_index = 0
    elif current_index >= total_unmastered:
        current_index = total_unmastered - 1

    # 组织当前词汇数据
    current_particle = sorted_particles[current_index] if sorted_particles else None

    # 如果没有词汇，显示空状态
    if not current_particle:
        return render_template('recite.html', word_card=None, current_index=0, total_words=0)

    # 获取当前词汇的学习进度
    progress = RecitationProgress.query.filter_by(
        user_id=user_id,
        particle_id=current_particle.id
    ).first()

    # 处理POST请求（提交答案）
    if request.method == 'POST':
        # 获取用户提交的答案
        answers = request.form

        # 验证答案
        correct = True
        details = []

        # 收集所有可能的释义
        all_definitions = []
        for pos in current_particle.parts_of_speech:
            for definition in pos.definitions:
                all_definitions.append({
                    'id': definition.id,
                    'text': definition.definition,
                    'pos': pos.category
                })

        # 准备记录错误题目信息
        wrong_example_ids = []
        correct_answer_ids = []
        user_answers = []

        # 检查每个例句对应的答案
        for pos in current_particle.parts_of_speech:
            for definition in pos.definitions:
                for example in definition.examples:
                    answer_key = f'example_{example.id}'
                    if answer_key in answers:
                        selected_def = int(answers[answer_key])
                        is_correct = selected_def == definition.id

                        # 记录用户答案
                        user_answers.append({
                            'example_id': example.id,
                            'selected_answer': selected_def,
                            'correct_answer': definition.id,
                            'is_correct': is_correct
                        })

                        # 记录错误题目
                        if not is_correct:
                            correct = False
                            wrong_example_ids.append(example.id)
                            correct_answer_ids.append(definition.id)

                        # 记录详情
                        details.append({
                            'example': example.example,
                            'selected': next((d['text'] for d in all_definitions if d['id'] == selected_def), '未选择'),
                            'correct': definition.definition,
                            'is_correct': is_correct
                        })

        # 确保progress对象存在（处理用户首次学习的情况）
        if not progress:
            progress = RecitationProgress(
                user_id=user_id,
                particle_id=current_particle.id,
                last_studied=datetime.utcnow(),
                mastery_level=0,
                wrong_count=0,
                right_count=0
            )
            db.session.add(progress)

        # 更新统计信息（安全处理None值）
        progress.last_studied = datetime.utcnow()
        if correct:
            progress.right_count = (progress.right_count or 0) + 1
            progress.mastery_level = min(2, (progress.mastery_level or 0) + 1)
            flash('全部回答正确！', 'success')
        else:
            progress.wrong_count = (progress.wrong_count or 0) + 1
            progress.mastery_level = max(0, (progress.mastery_level or 0) - 1)
            flash('部分回答错误，请继续努力！', 'error')

        # 创建学习记录
        record = VocabularyRecord(
            user_id=user_id,
            particle_id=current_particle.id,
            study_time=datetime.utcnow(),
            wrong_example_ids=wrong_example_ids,
            correct_answer_ids=correct_answer_ids,
            user_answers=user_answers
        )
        db.session.add(record)

        # 提交所有数据库更改
        db.session.commit()

        # 如果全部正确，移动到下一个词汇
        if correct:
            current_index = min(current_index + 1, total_unmastered - 1)
            return redirect(url_for('recite', index=current_index))
        else:
            # 显示答题详情
            return render_template('recite_result.html',
                                   details=details,
                                   current_index=current_index,
                                   total_words=total_unmastered,
                                   particle=current_particle)

    # 组织当前词汇数据（GET请求）
    parts = []
    examples_list = []

    for pos in current_particle.parts_of_speech:
        definitions = []
        for definition in pos.definitions:
            examples = []
            for example in definition.examples:
                examples.append({
                    'id': example.id,
                    'text': example.example
                })
                examples_list.append({
                    'id': example.id,
                    'text': example.example
                })
            definitions.append({
                'text': definition.definition,
                'examples': examples
            })

        parts.append({
            'category': pos.category,
            'sub_category': pos.sub_category,
            'definitions': definitions
        })

    # 收集所有可能的释义选项
    definitions_options = []
    for pos in current_particle.parts_of_speech:
        for definition in pos.definitions:
            definitions_options.append({
                'id': definition.id,
                'text': f"{definition.definition} ({pos.category})"
            })

    # 随机打乱选项
    random.shuffle(definitions_options)

    word_card = {
        'particle_id': current_particle.id,  # 添加ID用于标记功能
        'character': current_particle.character,
        'parts': sorted(parts, key=lambda x: x['category']),
        'examples': examples_list,
        'definitions_options': definitions_options
    }

    return render_template('recite.html',
                           word_card=word_card,
                           current_index=current_index,
                           total_words=total_unmastered,
                           progress=progress)

@app.route('/mark_as_mastered', methods=['POST'])
@login_required
def mark_as_mastered():
    try:
        data = request.get_json()
        particle_id = data.get('particle_id')
        user_id = session['user_id']

        # 查找或创建学习记录
        progress = RecitationProgress.query.filter_by(
            user_id=user_id,
            particle_id=particle_id
        ).first()

        if not progress:
            progress = RecitationProgress(
                user_id=user_id,
                particle_id=particle_id,
                last_studied=datetime.utcnow(),
                mastery_level=2,
                wrong_count=0,
                right_count=0
            )
            db.session.add(progress)
        else:
            # 更新为已掌握
            progress.mastery_level = 2
            progress.last_studied = datetime.utcnow()

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/vocabulary_records', methods=['GET'])
@login_required
def get_vocabulary_records():
    search_term = request.args.get('q', '').strip()
    user_id = session['user_id']

    # 基础查询
    base_query = VocabularyRecord.query.filter_by(user_id=user_id)

    # 添加搜索过滤
    if search_term:
        base_query = base_query.join(LexicalParticle).filter(
            LexicalParticle.character.like(f'%{search_term}%')
        )

    # 按时间排序
    records = base_query.order_by(VocabularyRecord.study_time.desc()).all()

    # 获取所有相关词汇的ID
    particle_ids = [record.particle_id for record in records]

    # 一次性查询所有相关词汇的学习进度
    progress_records = RecitationProgress.query.filter(
        RecitationProgress.user_id == user_id,
        RecitationProgress.particle_id.in_(particle_ids)
    ).all()

    # 创建进度映射字典：particle_id -> progress
    progress_map = {progress.particle_id: progress for progress in progress_records}

    # 处理记录
    records_data = []
    for record in records:
        particle = LexicalParticle.query.get(record.particle_id)

        # 获取该词汇的学习进度
        progress = progress_map.get(record.particle_id)

        # 获取错误题目详情
        wrong_items = []
        if record.wrong_example_ids and record.correct_answer_ids:
            for idx, example_id in enumerate(record.wrong_example_ids):
                example = Example.query.get(example_id)
                correct_answer = Definition.query.get(record.correct_answer_ids[idx])
                wrong_items.append({
                    'example': example.example,
                    'correct_answer': correct_answer.definition
                })

        records_data.append({
            'id': record.id,
            'study_time': record.study_time.strftime('%Y-%m-%d %H:%M'),
            'character': particle.character,
            'mastery_level': progress.mastery_level if progress else 0,
            'wrong_count': len(record.wrong_example_ids),
            'wrong_items': wrong_items
        })

    return jsonify(records_data)


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


# 查看收藏详情
@app.route('/favorite_detail/<int:favorite_id>')
@login_required
def favorite_detail(favorite_id):
    favorite = Favorite.query.filter_by(id=favorite_id, user_id=session['user_id']).first_or_404()
    return render_template('favorite_detail.html', favorite=favorite)


# 搜索收藏
@app.route('/search_favorites', methods=['GET'])
@login_required
def search_favorites():
    query = request.args.get('query', '')
    if query:
        favorites = Favorite.query.filter(
            and_(
                Favorite.user_id == session['user_id'],
                Favorite.title.like(f'%{query}%')
            )
        ).all()
    else:
        favorites = Favorite.query.filter_by(user_id=session['user_id']).all()

    return jsonify({
        'success': True,
        'favorites': [{
            'id': f.id,
            'title': f.title,
            'content': f.content[:100] + ('...' if len(f.content) > 100 else ''),
            'question': f.question,
            'created_at': f.created_at.strftime('%Y-%m-%d %H:%M')
        } for f in favorites]
    })


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