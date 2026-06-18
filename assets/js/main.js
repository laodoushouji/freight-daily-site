// Simple analytics and interaction
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            e.preventDefault();
            document.querySelector(a.getAttribute('href'))?.scrollIntoView({behavior: 'smooth'});
        });
    });

    // Reading progress bar on article pages
    const article = document.querySelector('.article-body');
    if (article) {
        const bar = document.createElement('div');
        bar.style.cssText = 'position:fixed;top:0;left:0;height:3px;background:#2980b9;z-index:999;transition:width 0.1s;width:0';
        document.body.appendChild(bar);
        window.addEventListener('scroll', () => {
            const pct = Math.min(window.scrollY / (document.body.scrollHeight - window.innerHeight) * 100, 100);
            bar.style.width = pct + '%';
        });
    }
});
