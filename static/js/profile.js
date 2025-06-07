// 导航切换
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();

        // 移除所有active类
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));

        // 添加active类
        this.classList.add('active');
        const targetId = this.getAttribute('data-target');
        document.getElementById(targetId).classList.add('active');

        // 如果是学习记录标签，加载背词记录
        if (targetId === 'study-records') {
            loadVocabularyRecords();
        }
        // 如果是学习进度标签，加载学习进度
        if (targetId === 'study-progress') {
            loadStudyProgress();
        }
    });
});

// 编辑字段
function editField(fieldId) {
    const field = document.getElementById(fieldId);
    const isEditing = field.classList.contains('editing');

    if (isEditing) {
        // 保存
        const input = field.querySelector('input');
        const span = field.querySelector('span');
        const newValue = input.value;

        // 这里可以添加AJAX请求保存到服务器
        fetch('/update_profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `field=personal_tag&value=${encodeURIComponent(newValue)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                span.textContent = newValue || '暂无个性标签';
                field.classList.remove('editing');
                field.querySelector('button').textContent = '修改';
            }
        });
    } else {
        // 编辑
        field.classList.add('editing');
        field.querySelector('button').textContent = '保存';
        field.querySelector('input').focus();
    }
}

// 更换头像
function changeAvatar() {
    const avatars = ['😊', '🎓', '📚', '✏️', '🌟', '🎯', '💡', '🔥'];
    const current = document.querySelector('.profile-avatar').textContent.trim();
    let next = avatars[Math.floor(Math.random() * avatars.length)];

    // 确保不是同一个头像
    while (next === current) {
        next = avatars[Math.floor(Math.random() * avatars.length)];
    }

    document.querySelector('.profile-avatar').textContent = next;

    // 保存到服务器
    fetch('/update_profile', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `field=avatar&value=${encodeURIComponent(next)}`
    });
}

// 显示退出模态框
function showLogoutModal() {
    document.getElementById('logoutModal').style.display = 'block';
}

// 关闭模态框
function closeModal() {
    document.getElementById('logoutModal').style.display = 'none';
}

// 确认退出
function confirmLogout() {
    window.location.href = '/logout';
}

// 查看收藏详情
function viewFavorite(id) {
    // 这里可以打开详情页面或模态框
    window.location.href = `/favorite_detail/${id}`;
}

// 删除收藏
function deleteFavorite(id) {
    if (confirm('确定要删除这个收藏吗？')) {
        fetch(`/delete_favorite/${id}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            }
        });
    }
}

// 搜索收藏
function searchFavorites() {
    const query = document.getElementById('favorite-search').value;

    fetch(`/search_favorites?query=${encodeURIComponent(query)}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateFavoritesList(data.favorites);
        }
    });
}

// 显示所有收藏
function showAllFavorites() {
    document.getElementById('favorite-search').value = '';

    // 使用API获取所有收藏
    fetch('/search_favorites')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateFavoritesList(data.favorites);
        }
    });
}

// 更新收藏列表
function updateFavoritesList(favorites) {
    const favoritesList = document.getElementById('favorites-list');
    favoritesList.innerHTML = '';

    if (favorites.length > 0) {
        favorites.forEach(favorite => {
            favoritesList.innerHTML += `
                <div class="favorite-item">
                    <h4>${favorite.title}</h4>
                    <p>${favorite.content}</p>
                    <p><small>收藏时间：${favorite.created_at}</small></p>
                    <div class="actions">
                        <button class="btn-small view" onclick="viewFavorite('${favorite.id}')">查看详情</button>
                        <button class="btn-small delete" onclick="deleteFavorite('${favorite.id}')">删除</button>
                    </div>
                </div>
            `;
        });
    } else {
        favoritesList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <p>未找到相关收藏</p>
            </div>
        `;
    }
}

// 加载背词记录
function loadVocabularyRecords() {
    const searchTerm = document.getElementById('vocabulary-search').value || '';
    const container = document.getElementById('vocabulary-records');

    container.innerHTML = '<div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>正在加载背词记录...</p></div>';

    fetch(`/api/vocabulary_records?q=${encodeURIComponent(searchTerm)}`)
        .then(response => response.json())
        .then(data => {
            container.innerHTML = '';

            if (data.length > 0) {
                data.forEach(record => {
                    // 生成错误题目列表
                    let wrongItemsHtml = '';
                    if (record.wrong_items && record.wrong_items.length > 0) {
                        wrongItemsHtml = '<ul class="wrong-items">';
                        record.wrong_items.forEach(item => {
                            wrongItemsHtml += `
                                <li>
                                    <div class="wrong-example">${item.example}</div>
                                    <div class="correct-answer">正确答案: ${item.correct_answer}</div>
                                </li>
                            `;
                        });
                        wrongItemsHtml += '</ul>';
                    }

                    // 掌握度文本和样式
                    const masteryText = ['陌生', '熟悉', '掌握'][record.mastery_level] || '未知';
                    const masteryClass = `mastery mastery-${record.mastery_level}`;

                    container.innerHTML += `
                        <div class="vocabulary-record">
                            <div class="record-header">
                                <span class="character">${record.character}</span>
                                <span class="study-time">${record.study_time}</span>
                                <span class="${masteryClass}">${masteryText}</span>
                            </div>
                            <div class="record-details">
                                <div class="wrong-count">
                                    错误: ${record.wrong_count}题
                                </div>
                                ${wrongItemsHtml}
                            </div>
                        </div>
                    `;
                });
            } else {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-book"></i>
                        <p>${searchTerm ? '未找到相关背词记录' : '暂无背词记录'}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>加载背词记录失败，请重试</p>
                </div>
            `;
            console.error('加载背词记录失败:', error);
        });
}

// 加载学习进度
function loadStudyProgress() {
    fetch('/api/study_progress')
        .then(response => response.json())
        .then(data => {
            // 更新统计数据
            document.getElementById('total-words-count').textContent = data.stats.total;
            document.getElementById('mastered-count').textContent = data.stats.mastered;
            document.getElementById('familiar-count').textContent = data.stats.familiar;
            document.getElementById('unfamiliar-count').textContent = data.stats.unfamiliar;

            // 渲染词汇列表
            renderWordList('mastered-words', data.mastered_words, 'mastered');
            renderWordList('unfamiliar-words', data.unfamiliar_words, 'unfamiliar');

            // 绘制燃尽图
            renderBurndownChart(data.burndown_data, data.stats.total);
        });
}

// 渲染词汇列表
function renderWordList(containerId, words, type) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (words.length === 0) {
        container.innerHTML = `<div class="empty-list">暂无${type === 'mastered' ? '已掌握' : '未掌握'}词汇</div>`;
        return;
    }

    words.forEach(word => {
        const wordEl = document.createElement('div');
        wordEl.className = 'word-item';
        wordEl.textContent = word;
        container.appendChild(wordEl);
    });
}

// 绘制燃尽图
function renderBurndownChart(data, totalWords) {
    const ctx = document.getElementById('burndown-chart').getContext('2d');

    // 准备图表数据
    const dates = data.map(item => item.date);
    const masteredData = data.map(item => item.mastered);

    // 理想进度线（线性减少）
    const idealData = [];
    const days = data.length;
    for (let i = 0; i < days; i++) {
        idealData.push(totalWords - (totalWords / days) * i);
    }

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: '实际掌握量',
                    data: masteredData,
                    borderColor: '#6d4427',
                    backgroundColor: 'rgba(109, 68, 39, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: '理想进度',
                    data: idealData,
                    borderColor: '#28a745',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: '词汇掌握进度'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: totalWords,
                    title: {
                        display: true,
                        text: '已掌握词汇量'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '日期'
                    }
                }
            }
        }
    });
}

// 页面加载时初始化背词记录
document.addEventListener('DOMContentLoaded', function() {
    // 如果当前是学习记录页面，加载数据
    if (document.querySelector('.nav-link.active')?.getAttribute('data-target') === 'study-records') {
        loadVocabularyRecords();
    }
});

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('logoutModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}