function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    const queryParams = {};
    for (const [key, value] of params.entries()) {
        try {
            // 尝试解析JSON格式的数据
            queryParams[key] = JSON.parse(decodeURIComponent(value));
        } catch {
            // 如果解析失败，保留原始字符串值
            queryParams[key] = value;
        }
    }
    return queryParams;
}
function handleSubmit() {
    const article = document.getElementById('article').value;
    const ratings = {
        first: document.querySelector('input[name="first"]:checked')?.value || '3',
        second: document.querySelector('input[name="second"]:checked')?.value || '3',
        third: document.querySelector('input[name="third"]:checked')?.value || '3',
        fourth: document.querySelector('input[name="fourth"]:checked')?.value || '3',
        fifth: document.querySelector('input[name="fifth"]:checked')?.value || '3'
    };

    const data = {
        article: article,
        ratings: ratings,
    };

    // 使用 AJAX 提交数据
    fetch('/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
        .then(response => {
            if (!response.ok) {
                // 如果服务器返回了非 2xx 的状态码，抛出错误
                return response.text().then(text => {
                    throw new Error(`服务器响应错误: ${response.status} - ${text}`);
                });
            }
            return response.json();
        })
        .then(result => {
            console.log("服务器返回的数据：", result);
            // 将结果传递给 exercise.html
            const params = new URLSearchParams();
            for (const key in result) {
                if (typeof result[key] === 'object') {
                    params.append(key, JSON.stringify(result[key]));
                } else {
                    params.append(key, result[key]);
                }
            }
            window.location.href = `/exercise?${params.toString()}`;
        })
        .catch(error => {
            console.error('提交过程中发生错误:', error);
            alert(`提交过程中发生错误: ${error.message}`);
        });
}


function toggleText1(type) {
    let content = document.getElementById("text1-content");
    if (!content) return;

    // 使用全局变量中的文本内容
    if (window.text1Content[type]) {
        content.innerText = window.text1Content[type].trim();
    }

    // 更新指示器位置
    let indicator = document.getElementById("indicator1");
    if (indicator) {
        indicator.style.left = type === 'article' ? '0' : '50%';
    }
}

function toggleText2(type, num) {
    let questionElement = document.getElementById(`${num}-content`);
    let answerElement = document.getElementById(`${num.replace('question', 'answer')}-content`);

    if (text2Content[type][num]) {
        questionElement.innerText = text2Content['questions'][num].trim();
        answerElement.innerText = text2Content['answers'][num.replace('question', 'answer')].trim();
        answerElement.style.display = 'none';

    }
}

document.addEventListener("DOMContentLoaded", function () {
    // Initialize indicators position
    //document.getElementById("indicator1").style.width = "50%";
    //document.getElementById("indicator1").style.left = "0";

    const params = getQueryParams();

    text1Content = {
        article: params.article || '',
        translation: params.translation || ''
    };

    text2Content = {
        questions: params.questions || {},
        answers: params.answers || {}
    };

    // 默认显示原文和题目
    toggleText1('article');
    let questionNums = [
        'question1',
        'question2',
        'question3',
        'question4',
        'question5'
    ];
    for (let i = 0; i < 5; i++) {
        toggleText2('questions', questionNums[i]);
    }
});