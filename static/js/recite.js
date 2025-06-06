// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {

    // 标记为已掌握按钮
    document.getElementById('mark-mastered-btn').addEventListener('click', function() {
        const particleId = wordCardParticleId;

        // 禁用按钮防止重复点击
        this.disabled = true;
        this.textContent = '标记中...';

        fetch('/mark_as_mastered', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ particle_id: particleId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 显示成功消息
                const successMsg = document.createElement('div');
                successMsg.textContent = '已标记为已掌握！该词汇将不会再出现。';
                successMsg.style.cssText = `
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background-color: #4CAF50;
                    color: white;
                    padding: 15px 25px;
                    border-radius: 5px;
                    z-index: 1000;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                `;
                document.body.appendChild(successMsg);

                // 2秒后刷新页面
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                // 恢复按钮状态
                this.disabled = false;
                this.textContent = '标记为已掌握';

                alert('标记失败: ' + data.error);
            }
        })
        .catch(error => {
            // 恢复按钮状态
            this.disabled = false;
            this.textContent = '标记为已掌握';

            console.error('标记错误:', error);
            alert('请求失败，请检查网络连接');
        });
    });

    // 选项选择效果
    document.querySelectorAll('.option-item').forEach(item => {
        item.addEventListener('click', function() {
            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;

            // 清除所有选中状态
            document.querySelectorAll('.option-item').forEach(el => {
                el.classList.remove('selected');
            });

            // 设置当前选中状态
            this.classList.add('selected');
        });
    });
});