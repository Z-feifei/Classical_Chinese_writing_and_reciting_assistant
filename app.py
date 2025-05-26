import os

from flask import Flask, request, jsonify, render_template

import UseModel
import split

app = Flask(__name__)


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
async def generate():
    try:
        data = request.get_json()
        article = data.get('article')
        ratings = data.get('ratings')
        print("收到请求")

        # 将 ratings 字典转换为整数列表
        rating_keys = ['first', 'second', 'third', 'fourth', 'fifth']
        ratings_list = [int(ratings[key]) for key in rating_keys]

        # 设置 UseModel.py 中的全局变量
        UseModel.content = article
        UseModel.DiffofQ1, UseModel.DiffofQ2, UseModel.DiffofQ3, UseModel.DiffofQ4, UseModel.DiffofQ5 = ratings_list


        # 调用 UseModel.py 的方法
        OutofQ1 = await UseModel.Q1()
        OutofQ2 = await UseModel.Q2()
        OutofQ3 = await UseModel.Q3()
        OutofQ4 = await UseModel.Q4()
        OutofQ5 = await UseModel.Q5()

        # 将输出写入 generate.txt
        file_path = os.path.join(app.static_folder, 'text', 'generate.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(OutofQ1.content + '\n')
            f.write(OutofQ2.content + '\n')
            f.write(OutofQ3.content + '\n')
            f.write(OutofQ4.content + '\n')
            f.write(OutofQ5.content + '\n')

        # 调用 generate_model 函数生成结果
        result = generate_model('generate.txt')

        return jsonify({
            'article': article,
            'questions': result.get('questions'),
            'answers': result.get('answers')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def generate_model(filename):
    questions = {}
    answers = {}
    nums = [1, 2, 3, 4, 5]
    file_path = os.path.join(app.static_folder, 'text', filename)
    result = split.read_and_parse_file(file_path, nums)
    print(result)
    for num in nums:
        questions[f'question{num}'] = result['questions'][f'question{num}']
        answers[f'answer{num}'] = result['answers'][f'answer{num}']
    return {
        'questions': questions,
        'answers': answers
    }


@app.route('/regenerate/<nums>', methods=['POST'])
async def regenerate(nums):
    try:
        nums = list(map(int, nums.split(',')))

        # 调用相应的 UseModel.py 方法
        results = []
        for num in nums:
            if num == 1:
                result = await UseModel.Q1()
            elif num == 2:
                result = await UseModel.Q2()
            elif num == 3:
                result = await UseModel.Q3()
            elif num == 4:
                result = await UseModel.Q4()
            elif num == 5:
                result = await UseModel.Q5()
            results.append(result)

        # 将输出写入 regenerate.txt
        file_path = os.path.join(app.static_folder, 'text', 'regenerate.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(result.content + '\n')

        if nums == [1, 2, 3, 4, 5]:
            result1 = generate_model('regenerate.txt')
        else:
            # 调用 regenerate_model 函数生成结果
            result1 = regenerate_model(nums)
        return jsonify(result1)
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
    return {
        'questions': questions,
        'answers': answers
    }


if __name__ == '__main__':
    app.run(debug=True)
