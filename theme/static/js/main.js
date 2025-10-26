/**
 * mblog 默认主题 JavaScript
 * 提供基础交互功能
 */

(function() {
    'use strict';

    /**
     * 初始化函数
     */
    function init() {
        // 添加平滑滚动
        initSmoothScroll();
        
        // 为外部链接添加 target="_blank"
        initExternalLinks();
        
        // 添加代码复制功能
        initCodeCopy();
        
        // 添加返回顶部按钮
        initBackToTop();
    }

    /**
     * 平滑滚动到锚点
     */
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * 为外部链接添加 target="_blank" 和 rel="noopener noreferrer"
     */
    function initExternalLinks() {
        const links = document.querySelectorAll('.post-content a');
        links.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (href.startsWith('http://') || href.startsWith('https://'))) {
                // 检查是否是外部链接
                if (!href.includes(window.location.hostname)) {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                }
            }
        });
    }

    /**
     * 为代码块添加复制按钮
     */
    function initCodeCopy() {
        const codeBlocks = document.querySelectorAll('.post-content pre');
        
        codeBlocks.forEach(block => {
            // 创建复制按钮
            const button = document.createElement('button');
            button.className = 'code-copy-btn';
            button.textContent = '复制';
            button.setAttribute('aria-label', '复制代码');
            
            // 创建包装容器
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper';
            
            // 插入包装容器
            block.parentNode.insertBefore(wrapper, block);
            wrapper.appendChild(block);
            wrapper.appendChild(button);
            
            // 添加点击事件
            button.addEventListener('click', async function() {
                const code = block.querySelector('code');
                const text = code ? code.textContent : block.textContent;
                
                try {
                    await navigator.clipboard.writeText(text);
                    button.textContent = '已复制!';
                    button.classList.add('copied');
                    
                    setTimeout(() => {
                        button.textContent = '复制';
                        button.classList.remove('copied');
                    }, 2000);
                } catch (err) {
                    console.error('复制失败:', err);
                    button.textContent = '复制失败';
                    setTimeout(() => {
                        button.textContent = '复制';
                    }, 2000);
                }
            });
        });
        
        // 添加样式
        if (codeBlocks.length > 0 && !document.getElementById('code-copy-styles')) {
            const style = document.createElement('style');
            style.id = 'code-copy-styles';
            style.textContent = `
                .code-block-wrapper {
                    position: relative;
                    margin: 1.5rem 0;
                }
                .code-copy-btn {
                    position: absolute;
                    top: 0.5rem;
                    right: 0.5rem;
                    padding: 0.25rem 0.75rem;
                    font-size: 0.75rem;
                    background-color: rgba(255, 255, 255, 0.9);
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    z-index: 10;
                }
                .code-copy-btn:hover {
                    background-color: #3498db;
                    color: white;
                    border-color: #3498db;
                }
                .code-copy-btn.copied {
                    background-color: #27ae60;
                    color: white;
                    border-color: #27ae60;
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * 返回顶部按钮
     */
    function initBackToTop() {
        // 创建按钮
        const button = document.createElement('button');
        button.className = 'back-to-top';
        button.innerHTML = '↑';
        button.setAttribute('aria-label', '返回顶部');
        button.style.display = 'none';
        document.body.appendChild(button);
        
        // 滚动时显示/隐藏按钮
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                if (window.pageYOffset > 300) {
                    button.style.display = 'block';
                } else {
                    button.style.display = 'none';
                }
            }, 100);
        });
        
        // 点击返回顶部
        button.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
        
        // 添加样式
        if (!document.getElementById('back-to-top-styles')) {
            const style = document.createElement('style');
            style.id = 'back-to-top-styles';
            style.textContent = `
                .back-to-top {
                    position: fixed;
                    bottom: 2rem;
                    right: 2rem;
                    width: 3rem;
                    height: 3rem;
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 50%;
                    font-size: 1.5rem;
                    cursor: pointer;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                    transition: all 0.3s ease;
                    z-index: 1000;
                }
                .back-to-top:hover {
                    background-color: #2980b9;
                    transform: translateY(-3px);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                }
                @media (max-width: 768px) {
                    .back-to-top {
                        bottom: 1rem;
                        right: 1rem;
                        width: 2.5rem;
                        height: 2.5rem;
                        font-size: 1.25rem;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // 当 DOM 加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
