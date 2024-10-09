function redirect() {
    window.location.href = `/`;
}

function refreshQuestion(questionId) {
    const questionNum = questionId.replace('question', '').replace('-content', '');

    // 使用 AJAX 提交数据
    fetch(`/regenerate/${questionNum}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            article: "这是一个示例文章内容",
            ratings: [5, 4, 3, 2, 1] // 示例评分数据
        })
    })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(`服务器响应错误: ${response.status} - ${text}`);
                });
            }
            return response.json();
        })
        .then(result => {
            const question = document.getElementById(questionId);
            question.innerText = result.questions[`question${questionNum}`];

            const answerId = questionId.replace('question', 'answer');
            const answer = document.getElementById(answerId);
            answer.innerText = result.answers[`answer${questionNum}`];
            answer.style.display = 'none';

            const icon = answer.previousElementSibling.querySelector('.icon i');
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        })
        .catch(error => {
            console.error('提交过程中发生错误:', error);
            alert(`提交过程中发生错误: ${error.message}`);
        });
}

function toggleAnswer(answerId) {
    const answer = document.getElementById(answerId);
    const icon = answer.previousElementSibling.querySelector('.icon i');

    // 切换答案的显示状态
    if (answer.style.display === 'none') {
        answer.style.display = 'block';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    } else {
        answer.style.display = 'none';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    }
}

function reloadQuestions() {

    // 使用 AJAX 提交数据
    fetch(`/regenerate/1,2,3,4,5`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
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
            for (let i = 1; i <= 5; i++) {
                const questionId = `question${i}-content`; // 使用模板字符串
                const question = document.getElementById(questionId);
                if (question) { // 检查元素是否存在
                    question.innerText = result.questions[`question${i}`];
                }

                const answerId = questionId.replace('question', 'answer');
                const answer = document.getElementById(answerId);
                if (answer) { // 检查元素是否存在
                    answer.innerText = result.answers[`answer${i}`];
                    answer.style.display = 'none';

                    const icon = answer.previousElementSibling.querySelector('.icon i');
                    if (icon) { // 检查图标元素是否存在
                        icon.classList.remove('fa-eye');
                        icon.classList.add('fa-eye-slash');
                    }
                }
            }

        })
        .catch(error => {
            console.error('提交过程中发生错误:', error);
            alert(`提交过程中发生错误: ${error.message}`);
        });
}
