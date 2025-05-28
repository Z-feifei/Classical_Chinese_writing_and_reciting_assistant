// 处理验证码发送
function sendVerificationCode() {
    const emailInput = document.getElementById('email');
    const email = emailInput.value.trim();
    
    if (!email) {
        alert('请输入邮箱地址');
        return;
    }
    
    // 禁用发送按钮
    const sendButton = document.querySelector('.send-code-btn');
    sendButton.disabled = true;
    sendButton.textContent = '发送中...';
    
    // 发送请求
    fetch('/send_verification', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `email=${encodeURIComponent(email)}`,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 倒计时60秒
            let countdown = 60;
            const timer = setInterval(() => {
                countdown--;
                sendButton.textContent = `${countdown}秒后重新发送`;
                
                if (countdown <= 0) {
                    clearInterval(timer);
                    sendButton.disabled = false;
                    sendButton.textContent = '发送验证码';
                }
            }, 1000);
            
            alert(data.message);
        } else {
            alert(data.message);
            sendButton.disabled = false;
            sendButton.textContent = '发送验证码';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('发送失败，请稍后重试');
        sendButton.disabled = false;
        sendButton.textContent = '发送验证码';
    });
}

// 处理退出确认
function confirmLogout() {
    if (confirm('是否确定退出当前账号？')) {
        window.location.href = '/logout';
    }
}