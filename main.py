import os
import asyncio
from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import UseModel
import split

# 创建全局事件循环（仅创建不立即设置）
global_loop = asyncio.new_event_loop()

app = Flask(__name__)
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