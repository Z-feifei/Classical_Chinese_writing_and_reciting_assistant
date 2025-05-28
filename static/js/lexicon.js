document.addEventListener('DOMContentLoaded', () => {
    // 配置参数
    const CONFIG = {
        debounceTime: 300,    // 防抖延迟(ms)
        mainCategories: ['连词', '助词', '语气词', '比况词', '代词', '副词', '介词', '形容词', '其他']
    };

    // DOM元素缓存
    const DOM = {
        contentArea: document.getElementById('contentArea'),
        searchInput: document.getElementById('searchInput'),
        posFilter: document.getElementById('posFilter'),
        pagination: document.getElementById('pagination')
    };

    // 应用状态
    let state = {
        currentPage: 1,
        totalPages: 1,
        searchQuery: '',
        selectedCategories: new Set(),
        data: []
    };

    // 防抖函数
    const debounce = (func, delay) => {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    };

    // 初始化分类筛选器
    function initFilters() {
        DOM.posFilter.innerHTML = CONFIG.mainCategories.map(category => `
            <li class="filter-item" data-category="${category}">${category}</li>
        `).join('');
    }

    // API请求封装
    async function fetchData(page = 1) {
        try {
            showLoading();

            const params = new URLSearchParams({
                page: page,
                ...(state.searchQuery && { q: state.searchQuery })
            });

            const response = await fetch(`/api/lexicon?${params}`);
            if (!response.ok) throw new Error('网络响应异常');

            const { data, pagination } = await response.json();

            state.data = data;
            state.currentPage = pagination.page;
            state.totalPages = pagination.total_pages;

            renderCards();
            updatePagination();
        } catch (error) {
            showError('数据加载失败，请稍后重试');
        } finally {
            hideLoading();
        }
    }

    // 渲染卡片列表
    function renderCards() {
        const filteredData = filterByCategory(state.data);

        DOM.contentArea.innerHTML = filteredData.length > 0
            ? filteredData.map(renderCard).join('')
            : `<div class="empty-state">未找到匹配的结果</div>`;
    }

    // 单个卡片渲染
    function renderCard(char) {
        return `
            <div class="character-card">
                <div class="card-header">
                    <h2>${char.character}</h2>
                    <div class="category-tags">
                        ${[...new Set(char.parts_of_speech.map(p => p.main_category))]
                            .map(cat => `<span class="tag">${cat}</span>`).join('')}
                    </div>
                </div>
                <div class="card-body">
                    ${char.parts_of_speech.map(renderPartOfSpeech).join('')}
                </div>
            </div>
        `;
    }

    // 渲染词性部分
    function renderPartOfSpeech(pos) {
        return `
            <section class="pos-group">
                <h3 class="pos-title">${pos.display_category}</h3>
                ${pos.definitions.map(renderDefinition).join('')}
            </section>
        `;
    }

    // 渲染定义部分
    function renderDefinition(def) {
        return `
            <div class="definition">
                <p class="meaning">${def.definition}</p>
                ${def.examples.map(ex => `
                    <div class="example">
                        <i class="fas fa-quote-left"></i>
                        ${ex}
                    </div>
                `).join('')}
            </div>
        `;
    }

    // 分类筛选逻辑
    function filterByCategory(data) {
        if (state.selectedCategories.size === 0) return data;

        return data.filter(char =>
            char.parts_of_speech.some(pos =>
                state.selectedCategories.has(pos.main_category)
            )
        );
    }

    // 更新分页控件
    function updatePagination() {
        DOM.pagination.innerHTML = `
            <button class="page-btn" ${state.currentPage === 1 ? 'disabled' : ''} 
                data-page="${state.currentPage - 1}">
                <i class="fas fa-chevron-left"></i>
            </button>
            <span class="page-info">
                第 ${state.currentPage} 页 / 共 ${state.totalPages} 页
            </span>
            <button class="page-btn" ${state.currentPage >= state.totalPages ? 'disabled' : ''} 
                data-page="${state.currentPage + 1}">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
    }

    // 事件处理：搜索输入
    const handleSearch = debounce(function(event) {
        state.searchQuery = event.target.value.trim();
        state.currentPage = 1;
        fetchData(1);
    }, CONFIG.debounceTime);

    // 事件处理：分类筛选
    function handleFilterClick(event) {
        const target = event.target.closest('.filter-item');
        if (!target) return;

        const category = target.dataset.category;
        target.classList.toggle('active');

        category && state.selectedCategories[target.classList.contains('active') ? 'add' : 'delete'](category);
        renderCards();
    }

    // 事件处理：分页
    function handlePagination(event) {
        const target = event.target.closest('.page-btn');
        if (!target) return;

        const page = parseInt(target.dataset.page);
        if (page !== state.currentPage) {
            fetchData(page);
        }
    }

    // 显示加载状态
    function showLoading() {
        DOM.contentArea.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>正在加载数据...</p>
            </div>
        `;
    }

    // 隐藏加载状态
    function hideLoading() {
        const loading = document.querySelector('.loading');
        loading && loading.remove();
    }

    // 显示错误信息
    function showError(message) {
        DOM.contentArea.innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
            </div>
        `;
    }

    // 初始化事件监听
    function initEventListeners() {
        DOM.searchInput.addEventListener('input', handleSearch);
        DOM.posFilter.addEventListener('click', handleFilterClick);
        DOM.pagination.addEventListener('click', handlePagination);
    }

    // 初始化应用
    function initialize() {
        initFilters();
        initEventListeners();
        fetchData(1);
    }

    // 启动应用
    initialize();
});