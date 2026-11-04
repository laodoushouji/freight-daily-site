// 货代日报 - 交互脚本
document.addEventListener('DOMContentLoaded', function() {
    // Reading progress
    const article = document.querySelector('.article-body');
    if (article) {
        const bar = document.createElement('div');
        bar.style.cssText = 'position:fixed;top:0;left:0;height:3px;background:var(--primary-light);z-index:999;transition:width 0.1s;width:0';
        document.body.appendChild(bar);
        window.addEventListener('scroll', () => {
            const pct = Math.min(window.scrollY / (document.body.scrollHeight - window.innerHeight) * 100, 100);
            bar.style.width = pct + '%';
        });
    }
});

// Feedback
function sendFeedback(type, filename) {
    // Store locally for now (can be sent to API later)
    const feedbacks = JSON.parse(localStorage.getItem('fd_feedback') || '{}');
    feedbacks[filename] = { type: type, time: new Date().toISOString() };
    localStorage.setItem('fd_feedback', JSON.stringify(feedbacks));

    const btn = event.target;
    if (type === 'useful') {
        btn.style.background = '#dcfce7';
        btn.style.borderColor = '#22c55e';
        btn.textContent = '✓ 感谢反馈';
    } else {
        btn.style.background = '#fef2f2';
        btn.style.borderColor = '#ef4444';
        btn.textContent = '✓ 已标记过时';
    }
    btn.disabled = true;
}
