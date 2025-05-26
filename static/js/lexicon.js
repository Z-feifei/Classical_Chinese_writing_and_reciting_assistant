// 修复版lexical.js
document.addEventListener('DOMContentLoaded', function() {
    // 模拟数据（实际应从后端API获取）
    const mockData = [
        {
            character: "安",
            parts_of_speech: [
                {
                    category: "动词",
                    definitions: [
                        {
                            definition: "安置，安排",
                            examples: ["安民告示"]
                        },
                        {
                            definition: "安定，平安",
                            examples: ["安之若素"]
                        }
                    ]
                },
                {
                    category: "形容词",
                    definitions: [
                        {
                            definition: "安心，安然",
                            examples: ["安然处之"]
                        }
                    ]
                }
            ]
        }
    ];

    // DOM元素缓存
    const domElements = {
        contentArea: document.getElementById('contentArea'),
        searchInput: document.getElementById('searchInput'),
        posFilter: document.querySelector('.pos-filter')
    }

    // 元素存在性检查
    if (!domElements.contentArea) {
        console.error('关键元素contentArea不存在，请检查HTML结构');
        return;
    }

    // 渲染卡片
    function renderCards(data) {
        console.log('收到数据:', data); // 新增
        if (!data || data.length === 0) {
            console.warn('无有效数据');
            return;
        }
        try {
            domElements.contentArea.innerHTML = '';

            data.forEach(char => {
                const card = document.createElement('div');
                card.className = 'character-card';

                card.innerHTML = `
                    <h2 class="character-header">${char.character}</h2>
                    <div class="pos-tags">
                        ${char.parts_of_speech.map(pos => 
                            `<span class="pos-tag">${pos.category}</span>`
                        ).join('')}
                    </div>
                    ${char.parts_of_speech.map(pos => `
                        <div class="pos-section">
                            <h3>${pos.category}</h3>
                            <ul class="definition-list">
                                ${pos.definitions.map(def => `
                                    <li>
                                        <p>${def.definition}</p>
                                        ${def.examples.map(ex => `
                                            <div class="example-item">${ex}</div>
                                        `).join('')}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    `).join('')}
                `;

                domElements.contentArea.appendChild(card);
            });

            // 绑定新卡片事件
            bindCardHover();
        } catch (error) {
            console.error('渲染卡片时发生错误:', error);
        }
    }

    // 搜索功能
    domElements.searchInput?.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const filtered = mockData.filter(char =>
            char.character.toLowerCase().includes(searchTerm)
        );
        renderCards(filtered);
    });

    // 词性过滤（事件委托）
    domElements.posFilter?.addEventListener('click', function(e) {
        const target = e.target.closest('.pos-item');
        if (!target) return;

        const selectedPos = target.textContent.split(' ')[0];
        const filtered = mockData.filter(char =>
            char.parts_of_speech.some(pos => pos.category === selectedPos)
        );
        renderCards(filtered);
    });

    // 卡片悬停效果
    function bindCardHover() {
        domElements.contentArea.querySelectorAll('.character-card').forEach(card => {
            card.style.transition = 'transform 0.2s';
            card.addEventListener('mouseenter', () =>
                card.style.transform = 'translateY(-5px)');
            card.addEventListener('mouseleave', () =>
                card.style.transform = 'none');
        });
    }

    // 初始化加载
    renderCards(mockData);
});