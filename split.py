import re


def separate_questions_answers(text, nums):
    # 使用正则表达式提取题目和答案
    questions = re.findall(r'(?<=\*\*题目\*\*：\n)[\s\S]*?(?=\*\*答案\*\*：)', text)
    answers_with_explanations = re.findall(r'(?<=\*\*答案\*\*：\n)[\s\S]*?(?=\*\*题目\*\*：|\Z)', text)

    # 创建字典
    questions_dict = {}
    answers_dict = {}

    for i, num in enumerate(nums):
        index = int(num) - 1  # 计算索引
        if index >= len(questions):  # 检查索引是否超出范围
            index = 0  # 超出范围时赋值为数组的第一个元素

        questions_dict[f'question{num}'] = questions[index].strip()

        # 再次检查 answers_with_explanations 的索引
        if index >= len(answers_with_explanations):
            index = 0  # 如果 answers_with_explanations 也超出范围，赋值为第一个元素

        parts = re.split(r'(?<=\*)\*\*解析\*\*：\n', answers_with_explanations[index], maxsplit=1)
        if len(parts) > 1:
            # 存在解析部分，将解析拼接到答案后
            answers_dict[f'answer{num}'] = f"{parts[0].strip()}\n\n**解析**：\n{parts[1].strip()}"
        else:
            # 不存在解析部分
            answers_dict[f'answer{num}'] = parts[0].strip()

    result = {
        "questions": questions_dict,
        "answers": answers_dict
    }

    return result


def read_and_parse_file(file_path, nums):
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()

    result = separate_questions_answers(text, nums)
    return result
