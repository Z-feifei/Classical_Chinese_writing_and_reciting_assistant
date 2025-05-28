import os
import asyncio
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_

import UseModel
import split


# 创建全局事件循环（仅创建不立即设置）
global_loop = asyncio.new_event_loop()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://feifei123:4RQl2C3Bzam1WGr4@mysql5.sqlpub.com:3310/classical_chinese'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)


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


limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# 全局信号量控制并发数（最大2个并行请求）
semaphore = asyncio.Semaphore(2, loop=global_loop)

async def limited_execute(task_func):
    """带事件循环检查的异步执行器"""
    async with semaphore:
        return await task_func()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/exercise')
def exercise():
    return render_template('exercise.html')

@app.route('/recite')
def recite():
    return render_template('recite.html')

@app.route('/familiar')
def familiar():
    file_path = os.path.join(app.static_folder, 'images', 'carousel2.png')
    if os.path.exists(file_path):
        os.remove(file_path)
    return render_template('next1.html')

@app.route('/next')
def next_page():
    return render_template('next.html')

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
        return jsonify({
            'article': article,
            'questions': result['questions'],
            'answers': result['answers']
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
    return render_template('personal.html')

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