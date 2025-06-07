document.addEventListener('DOMContentLoaded', function() {
    // 全局变量
    let currentChallenge = null;
    let timerInterval = null;
    let remainingTime = 0;
    let currentQuestions = [];
    let currentQuestionIndex = 0;
    let selectedOptionId = null;

    // DOM元素
    const createChallengeSection = document.querySelector('.create-challenge');
    const activeChallengeSection = document.querySelector('.active-challenge');
    const progressBar = document.querySelector('.progress');
    const completedCount = document.querySelector('.completed');
    const targetCount = document.querySelector('.target');
    const timeRemaining = document.querySelector('.time-remaining');
    const timerDisplay = document.querySelector('.timer');
    const wordCharacter = document.querySelector('.word-character');
    const questionExample = document.querySelector('.question-example .example-text');
    const optionsContainer = document.querySelector('.options-container');
    const submitButton = document.querySelector('.submit-answer');
    const giveUpButton = document.querySelector('.give-up');
    const historyList = document.querySelector('.history-list');

    // 初始化页面
    loadChallengeHistory();

    // 挑战类型选择
    document.querySelectorAll('.start-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const challengeType = this.closest('.challenge-type').dataset.type;
            const targetInput = challengeType === 'timed'
                ? document.querySelector('.time-input')
                : document.querySelector('.count-input');
            const target = parseInt(targetInput.value);

            if (isNaN(target) || target <= 0) {
                alert('请输入有效的目标值');
                return;
            }

            startChallenge(challengeType, target);
        });
    });

    // 提交答案
    submitButton.addEventListener('click', submitAnswer);

    // 放弃挑战
    giveUpButton.addEventListener('click', giveUpChallenge);

    // 开始挑战
    function startChallenge(type, target) {
    fetch('/api/challenges', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            type: type,
            target: target
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentChallenge = data.challenge;

            // 根据挑战类型显示/隐藏元素
            if (type === 'timed') {
                // 定时模式 - 显示时间，隐藏进度条
                timeRemaining.style.display = 'block';
                document.querySelector('.progress-container').style.display = 'none';

                // 启动计时器
                remainingTime = target * 60;
                updateTimerDisplay();
                timerInterval = setInterval(updateTimer, 1000);
            } else {
                // 定量模式 - 显示进度条，隐藏时间
                timeRemaining.style.display = 'none';
                document.querySelector('.progress-container').style.display = 'block';

                // 初始化进度条
                progressBar.style.width = '0%';
                completedCount.textContent = '0';
                targetCount.textContent = target;
            }

            // 获取题目列表
            getChallengeQuestions(type === 'timed' ? 50 : target);

            // 切换UI
            createChallengeSection.style.display = 'none';
            activeChallengeSection.style.display = 'block';
        } else {
            alert('创建挑战失败: ' + (data.error || '未知错误'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('创建挑战时出错' + error.message);
    });
}

    // 获取挑战题目
    function getChallengeQuestions(count) {
        fetch(`/api/challenge/words?count=${count}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentQuestions = data.words;
                currentQuestionIndex = 0;
                showCurrentQuestion();
            } else {
                alert('获取题目失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('获取题目时出错' + error.message);
        });
    }

    // 显示当前题目
    function showCurrentQuestion() {
        if (currentQuestionIndex < currentQuestions.length) {
            const question = currentQuestions[currentQuestionIndex];
            wordCharacter.textContent = question.character;
            questionExample.textContent = question.example;

            // 清空选项容器
            optionsContainer.innerHTML = '';
            selectedOptionId = null;
            submitButton.disabled = true;

            // 创建选项
            question.options.forEach(option => {
                const optionElement = document.createElement('div');
                optionElement.className = 'option';
                optionElement.dataset.id = option.id;
                optionElement.innerHTML = `
                    <input type="radio" name="answer" id="option-${option.id}" value="${option.id}">
                    <label for="option-${option.id}">${option.text}</label>
                `;

                // 添加选择事件
                optionElement.querySelector('input').addEventListener('change', function() {
                    selectedOptionId = this.value;
                    submitButton.disabled = false;
                });

                optionsContainer.appendChild(optionElement);
            });
        } else {
            // 如果没有更多题目，获取更多
            getChallengeQuestions(10);
        }
    }

    // 提交答案
    function submitAnswer() {
        if (!currentChallenge || !selectedOptionId) return;

        // 找到选中的选项
        const currentQuestion = currentQuestions[currentQuestionIndex];
        const selectedOption = currentQuestion.options.find(opt => opt.id == selectedOptionId);
        const isCorrect = selectedOption.is_correct;

        // 更新挑战进度
        updateChallengeProgress(isCorrect);

        // 显示反馈
        showAnswerFeedback(isCorrect, selectedOption, currentQuestion);
    }

    // 显示答案反馈
    function showAnswerFeedback(isCorrect, selectedOption, question) {
        // 高亮显示正确和错误答案
        const options = optionsContainer.querySelectorAll('.option');
        options.forEach(option => {
            const optionId = option.dataset.id;
            const optionData = question.options.find(opt => opt.id == optionId);

            if (optionData.is_correct) {
                option.classList.add('correct');
            } else if (optionId == selectedOption.id && !isCorrect) {
                option.classList.add('incorrect');
            }
        });

        // 禁用所有选项
        optionsContainer.querySelectorAll('input').forEach(input => {
            input.disabled = true;
        });

        // 更改提交按钮文本
        submitButton.textContent = isCorrect ? '回答正确！继续' : '回答错误！继续';
        submitButton.disabled = false;

        // 更改按钮点击事件
        submitButton.removeEventListener('click', submitAnswer);
        submitButton.addEventListener('click', nextQuestion);
    }

    // 下一题
    function nextQuestion() {
        // 恢复按钮状态
        submitButton.textContent = '提交答案';
        submitButton.removeEventListener('click', nextQuestion);
        submitButton.addEventListener('click', submitAnswer);
        submitButton.disabled = true;

        // 移动到下一题
        currentQuestionIndex++;
        showCurrentQuestion();
    }

    // 更新挑战进度
    function updateChallengeProgress(isCorrect) {
        if (!currentChallenge) return;

        fetch(`/api/challenge/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                challenge_id: currentChallenge.id,
                answers: [{
                    word_id: currentQuestions[currentQuestionIndex].id,
                    answer_id: selectedOptionId,
                    is_correct: isCorrect
                }]
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentChallenge.completed = data.completed;
                updateActiveChallengeUI();

                // 检查是否完成挑战
                if (data.is_completed) {
                    finishChallenge(true);
                }
            } else {
                alert('更新挑战进度失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('更新挑战进度时出错' + error.message);
        });
    }

    // 放弃挑战
    function giveUpChallenge() {
        if (!currentChallenge) return;

        if (confirm('确定要放弃当前挑战吗？')) {
            fetch(`/api/challenges/${currentChallenge.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action: 'fail'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    finishChallenge(false);
                } else {
                    alert('放弃挑战失败');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('放弃挑战时出错' + error.message);
            });
        }
    }

    // 更新进行中挑战的UI
    function updateActiveChallengeUI() {
    // 只在定量模式下更新进度条
    if (currentChallenge.type === 'quantitative') {
        targetCount.textContent = currentChallenge.target;
        completedCount.textContent = currentChallenge.completed || 0;
        const progressPercentage = (currentChallenge.completed / currentChallenge.target) * 100;
        progressBar.style.width = `${Math.min(progressPercentage, 100)}%`;
    }
}

    // 更新计时器
    function updateTimer() {
        remainingTime--;
        updateTimerDisplay();

        if (remainingTime <= 0) {
            clearInterval(timerInterval);
            timerInterval = null;
            finishChallenge(true);
        }
    }

    // 更新计时器显示
    function updateTimerDisplay() {
        const minutes = Math.floor(remainingTime / 60);
        const seconds = remainingTime % 60;
        timerDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    // 完成挑战
    function finishChallenge(success) {
        // 清除计时器
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }

        // 显示结果
        alert(success ? '恭喜完成挑战！' : '已放弃挑战');

        // 重置UI
        createChallengeSection.style.display = 'block';
        activeChallengeSection.style.display = 'none';

        // 重新加载历史记录
        loadChallengeHistory();

        // 重置状态
        currentChallenge = null;
        currentQuestions = [];
        currentQuestionIndex = 0;
        selectedOptionId = null;
    }

    // 加载挑战历史
    function loadChallengeHistory() {
        fetch('/api/challenges')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderChallengeHistory(data.challenges);
            } else {
                alert('加载挑战历史失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('加载挑战历史时出错' + error.message);
        });
    }

    // 渲染挑战历史
    function renderChallengeHistory(challenges) {
        historyList.innerHTML = '';

        if (challenges.length === 0) {
            historyList.innerHTML = '<p>暂无挑战历史</p>';
            return;
        }

        challenges.forEach(challenge => {
            const item = document.createElement('div');
            item.className = 'challenge-item';

            const typeClass = challenge.type === 'timed' ? 'timed-badge' : 'quantitative-badge';
            // 修改这里：定时模式下放弃的挑战也显示"失败"
            const resultText = (challenge.type === 'timed' && challenge.status !== 'failed') ? '结束' :
                         (challenge.status === 'completed' ? '完成' : '失败');
            // 修改这里：定时模式下放弃的挑战也使用红色样式
            const resultClass = (challenge.status === 'failed') ? 'failed-result' :
                         ((challenge.type === 'timed' && challenge.status !== 'failed') ? 'completed-result' :
                         (challenge.status === 'completed' ? 'completed-result' : 'failed-result'));

            item.innerHTML = `
            <div class="challenge-meta">
                <span class="challenge-type-badge ${typeClass}">${challenge.type === 'timed' ? '定时' : '定量'}</span>
                <span>目标: ${challenge.target}${challenge.type === 'timed' ? '分钟' : '题'}</span>
                <span>完成: ${challenge.completed}</span>
                <span class="challenge-result ${resultClass}">${resultText}</span>
            </div>
            <button class="delete-challenge" data-id="${challenge.id}">删除</button>
        `;

            historyList.appendChild(item);
        });

        // 添加删除事件
        document.querySelectorAll('.delete-challenge').forEach(btn => {
            btn.addEventListener('click', function() {
                const challengeId = this.dataset.id;
                deleteChallenge(challengeId);
            });
        });
    }

    // 删除挑战
    function deleteChallenge(challengeId) {
        if (confirm('确定要删除此挑战记录吗？')) {
            fetch(`/api/challenges/${challengeId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadChallengeHistory();
                } else {
                    alert('删除挑战失败');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('删除挑战时出错' + error.message);
            });
        }
    }
});