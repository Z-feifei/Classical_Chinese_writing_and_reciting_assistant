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

    // 应用状态管理
    const state = {
        currentPage: 1,
        totalPages: 1,
        searchQuery: '',
        selectedCategories: new Set(),
        isLoading: false
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
            <li class="filter-item" data-category="${category}">
                ${category}
                <span class="checkmark"></span>
            </li>
        `).join('');
    }

    // API请求封装（带分类参数）
    async function fetchData(page = 1) {
        try {
            if(state.isLoading) return;
            state.isLoading = true;
            showLoading();

            const params = new URLSearchParams({
                page: page,
                ...(state.searchQuery && { q: state.searchQuery }),
                ...(state.selectedCategories.size > 0 && {
                    categories: Array.from(state.selectedCategories).join(',')
                })
            });

            const response = await fetch(`/api/lexicon?${params}`);
            if (!response.ok) throw new Error(`HTTP错误! 状态码: ${response.status}`);

            const { data, pagination } = await response.json();

            state.currentPage = pagination.page;
            state.totalPages = pagination.total_pages;

            renderCards(data);
            updatePagination();
        } catch (error) {
            console.error('请求失败:', error);
            showError('数据加载失败，请稍后重试');
        } finally {
            state.isLoading = false;
            hideLoading();
        }
    }

    // 渲染卡片列表
    function renderCards(data) {
        DOM.contentArea.innerHTML = data.length > 0
            ? data.map(renderCard).join('')
            : `<div class="empty-state">
                <i class="fas fa-search"></i>
                <p>没有找到匹配的结果</p>
               </div>`;
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

    // 更新分页控件
    function updatePagination() {
        DOM.pagination.innerHTML = `
            <button class="page-btn" 
                ${state.currentPage === 1 ? 'disabled' : ''} 
                data-page="${state.currentPage - 1}">
                <i class="fas fa-chevron-left"></i>
            </button>
            
            <div class="page-status">
                第 <strong>${state.currentPage}</strong> 页 / 共 ${state.totalPages} 页
            </div>
            
            <button class="page-btn" 
                ${state.currentPage >= state.totalPages ? 'disabled' : ''} 
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

        // 更新选中分类
        if (category) {
            state.selectedCategories[target.classList.contains('active') ? 'add' : 'delete'](category);
        }

        // 重置页码并重新加载
        state.currentPage = 1;
        fetchData(1);
    }

    // 事件处理：分页
    function handlePagination(event) {
        const target = event.target.closest('.page-btn');
        if (!target || state.isLoading) return;

        const page = parseInt(target.dataset.page);
        if (page !== state.currentPage) {
            state.currentPage = page;
            fetchData(page);
        }
    }

    // 显示加载状态
    function showLoading() {
        DOM.contentArea.innerHTML = `
            <div class="loading">
                <div class="spinner dual-ring"></div>
                <p>正在加载数据...</p>
            </div>
        `;
    }

    // 隐藏加载状态
    function hideLoading() {
        const loading = document.querySelector('.loading');
        loading?.remove();
    }

    // 显示错误信息
    function showError(message) {
        DOM.contentArea.innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
                <button class="retry-btn" onclick="fetchData(${state.currentPage})">重试</button>
            </div>
        `;
    }

    // 初始化事件监听
    function initEventListeners() {
        DOM.searchInput.addEventListener('input', handleSearch);
        DOM.posFilter.addEventListener('click', handleFilterClick);
        DOM.pagination.addEventListener('click', handlePagination);

        // 回车键触发搜索
        DOM.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') fetchData(1);
        });
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