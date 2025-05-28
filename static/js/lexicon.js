document.addEventListener('DOMContentLoaded', () => {
    // 分类配置
    const MAIN_CATEGORIES = ['连词', '助词', '语气词', '比况词', '代词', '副词', '介词', '形容词', '其他'];

    // DOM元素缓存
    const domElements = {
        contentArea: document.getElementById('contentArea'),
        searchInput: document.getElementById('searchInput'),
        posFilter: document.getElementById('posFilter'),
        pagination: document.getElementById('pagination')
    };

    // 初始化状态
    let currentData = [];
    let currentPage = 1;
    let totalPages = 1;

    // 初始化筛选器（无复选框版本）
    function initFilters() {
        domElements.posFilter.innerHTML = '';

        MAIN_CATEGORIES.forEach(category => {
            const li = document.createElement('li');
            li.className = 'filter-item';
            li.dataset.category = category;
            li.textContent = category;
            domElements.posFilter.appendChild(li);
        });
    }

    // 事件处理器：搜索
    function handleSearch(event) {
        const query = event.target.value.toLowerCase();
        const filtered = currentData.filter(char =>
            char.character.toLowerCase().includes(query) ||
            char.parts_of_speech.some(pos =>
                pos.definitions.some(def =>
                    def.definition.toLowerCase().includes(query)
                )
            )
        );
        renderCards(filtered);
    }

    // 事件处理器：分类筛选（新版）
    function handleFilterClick(event) {
        const li = event.target.closest('.filter-item');
        if (!li) return;

        // 切换选中状态
        li.classList.toggle('active');

        // 获取当前选中分类
        const selectedCategories = Array.from(
            document.querySelectorAll('.filter-item.active')
        ).map(item => item.dataset.category);

        // 执行筛选
        const filtered = selectedCategories.length === 0
            ? currentData
            : currentData.filter(char =>
                selectedCategories.some(cat =>
                    char.parts_of_speech.some(pos => pos.main_category === cat)
                )
            );

        renderCards(filtered);
    }

    // 辅助函数：显示加载状态
    function showLoading() {
        domElements.contentArea.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>正在加载数据...</p>
            </div>
        `;
    }

    // 辅助函数：隐藏加载状态
    function hideLoading() {
        const loading = document.querySelector('.loading');
        if (loading) loading.remove();
    }

    // 辅助函数：显示错误
    function showError(message) {
        domElements.contentArea.innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
            </div>
        `;
    }

    // 分页加载
    async function loadPage(page) {
        try {
            showLoading();
            const response = await fetch(`/api/lexicon?page=${page}`);
            const { data, pagination } = await response.json();

            currentData = data;
            currentPage = pagination.page;
            totalPages = pagination.total_pages;

            renderCards(data);
            updatePagination();
        } catch (error) {
            showError('数据加载失败');
        } finally {
            hideLoading();
        }
    }

    // 渲染卡片
    function renderCards(data) {
        domElements.contentArea.innerHTML = data.map(char => `
            <div class="character-card">
                <div class="card-header">
                    <h2>${char.character}</h2>
                    <div class="category-tags">
                        ${[...new Set(char.parts_of_speech.map(p => p.main_category))]
                            .map(cat => `<span class="tag">${cat}</span>`).join('')}
                    </div>
                </div>
                <div class="card-body">
                    ${char.parts_of_speech.map(pos => `
                        <section class="pos-group">
                            <h3 class="pos-title">${pos.display_category}</h3>
                            ${pos.definitions.map(def => `
                                <div class="definition">
                                    <p class="meaning">${def.definition}</p>
                                    ${def.examples.map(ex => `
                                        <div class="example">
                                            <i class="fas fa-quote-left"></i>
                                            ${ex}
                                        </div>
                                    `).join('')}
                                </div>
                            `).join('')}
                        </section>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    // 更新分页控件
    function updatePagination() {
        domElements.pagination.innerHTML = `
            <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} data-page="${currentPage - 1}">
                <i class="fas fa-chevron-left"></i>
            </button>
            <span class="page-info">第 ${currentPage} 页 / 共 ${totalPages} 页</span>
            <button class="page-btn" ${currentPage >= totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
    }

    // 分页事件处理
    function handlePagination(event) {
        const target = event.target.closest('.page-btn');
        if (!target) return;
        loadPage(parseInt(target.dataset.page));
    }

    // 事件绑定
    function bindEvents() {
        domElements.searchInput.addEventListener('input', handleSearch);
        domElements.posFilter.addEventListener('click', handleFilterClick);
        domElements.pagination.addEventListener('click', handlePagination);
    }

    // 初始化流程
    initFilters();
    bindEvents();
    loadPage(1);
});