/**
 * SearchEngine - Client-side search functionality for mblog
 * 
 * Provides real-time search across blog posts with support for:
 * - Multi-keyword matching (all keywords must match)
 * - Tag filtering (using #tag syntax)
 * - Combined tag and keyword filtering
 * - Unicode/Chinese character support
 */

class SearchEngine {
    /**
     * Initialize the search engine
     * @param {string} indexUrl - URL to the search index JSON file
     */
    constructor(indexUrl) {
        this.indexUrl = indexUrl;
        this.posts = [];
        this.loaded = false;
    }

    /**
     * Load the search index from the server
     * @returns {Promise<void>}
     * @throws {Error} If the index fails to load or parse
     */
    async loadIndex() {
        try {
            const response = await fetch(this.indexUrl);
            if (!response.ok) {
                throw new Error(`Failed to load search index: ${response.status}`);
            }
            
            const data = await response.json();
            this.posts = data.posts || [];
            this.loaded = true;
        } catch (error) {
            console.error('Error loading search index:', error);
            throw error;
        }
    }

    /**
     * Parse a search query into tags and keywords
     * 
     * Tags are identified by # prefix (e.g., #python)
     * Keywords are all other non-empty tokens
     * Consecutive spaces are treated as single separators
     * 
     * @param {string} queryString - The raw search query
     * @returns {{tags: string[], keywords: string[]}} Parsed query object
     * 
     * Examples:
     *   "python tutorial" -> {tags: [], keywords: ["python", "tutorial"]}
     *   "#python tutorial" -> {tags: ["python"], keywords: ["tutorial"]}
     *   "#web #python api" -> {tags: ["web", "python"], keywords: ["api"]}
     *   "  multiple   spaces  " -> {tags: [], keywords: ["multiple", "spaces"]}
     */
    parseQuery(queryString) {
        if (!queryString || typeof queryString !== 'string') {
            return { tags: [], keywords: [] };
        }

        const tags = [];
        const keywords = [];

        // Split by whitespace and filter empty strings
        const tokens = queryString.trim().split(/\s+/).filter(token => token.length > 0);

        for (const token of tokens) {
            if (token.startsWith('#') && token.length > 1) {
                // Extract tag name (everything after #)
                const tagName = token.substring(1);
                tags.push(tagName);
            } else if (token !== '#') {
                // Regular keyword (ignore standalone #)
                keywords.push(token);
            }
        }

        return { tags, keywords };
    }

    /**
     * Search posts by query string
     * 
     * Filters posts based on:
     * - All specified tags must partially match post.tags (支持部分匹配)
     * - All specified keywords must be present in post.title (case-insensitive)
     * 
     * Empty query returns all posts
     * Results maintain original date ordering
     * 
     * @param {string} queryString - The search query
     * @returns {Array} Filtered array of posts matching the query
     */
    search(queryString) {
        if (!this.loaded) {
            console.warn('Search index not loaded yet');
            return [];
        }

        // Empty or whitespace-only query returns all posts
        if (!queryString || queryString.trim().length === 0) {
            return [...this.posts];
        }

        // Truncate very long queries (max 200 characters)
        const MAX_QUERY_LENGTH = 200;
        if (queryString.length > MAX_QUERY_LENGTH) {
            queryString = queryString.substring(0, MAX_QUERY_LENGTH);
            console.warn(`Query truncated to ${MAX_QUERY_LENGTH} characters`);
        }

        const { tags, keywords } = this.parseQuery(queryString);

        // If no valid tags or keywords, return all posts
        if (tags.length === 0 && keywords.length === 0) {
            return [...this.posts];
        }

        return this.posts.filter(post => {
            // Check tag matching - all specified tags must partially match at least one post tag
            // 标签部分匹配：#逆 可以匹配 "逆向破解"、"逆向工程" 等
            const tagMatch = tags.length === 0 || tags.every(searchTag => {
                const searchTagLower = searchTag.toLowerCase();
                const postTags = (post.tags || []).map(t => t.toLowerCase());
                // 检查是否有任何文章标签包含搜索标签（部分匹配）
                return postTags.some(postTag => postTag.includes(searchTagLower));
            });

            // Check keyword matching - all keywords must be in title
            const keywordMatch = keywords.length === 0 || keywords.every(keyword => {
                // Case-insensitive, Unicode-aware matching
                const title = (post.title || '').toLowerCase();
                const kw = keyword.toLowerCase();
                return title.includes(kw);
            });

            return tagMatch && keywordMatch;
        });
    }

    /**
     * Format date string to YYYY-MM-DD format
     * @param {string} dateString - ISO date string (e.g., "2024-01-11T00:00:00")
     * @returns {string} Formatted date (e.g., "2024-01-11")
     */
    formatDate(dateString) {
        if (!dateString) return '';
        
        // If already in YYYY-MM-DD format, return as is
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
            return dateString;
        }
        
        // Parse ISO date and extract YYYY-MM-DD
        try {
            const date = new Date(dateString);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        } catch (e) {
            // If parsing fails, try to extract YYYY-MM-DD from string
            const match = dateString.match(/^(\d{4}-\d{2}-\d{2})/);
            return match ? match[1] : dateString;
        }
    }

    /**
     * Display search results in the DOM
     * @param {Array} results - Array of post objects to display
     * @param {string} containerSelector - CSS selector for results container
     * @param {string} queryString - Original query for highlighting
     */
    displayResults(results, containerSelector, queryString = '') {
        const container = document.querySelector(containerSelector);
        if (!container) {
            console.error(`Results container not found: ${containerSelector}`);
            return;
        }

        // Clear previous results
        container.innerHTML = '';

        // Handle no results case
        if (results.length === 0) {
            container.innerHTML = '<div class="search-no-results">没有找到匹配的文章</div>';
            container.style.display = 'block';
            return;
        }

        const { keywords } = this.parseQuery(queryString);

        // Create result items
        const resultItems = results.map(post => {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'search-result-item';

            // Highlight keywords in title
            const highlightedTitle = this.highlightMatch(post.title, keywords);
            
            // Format date to YYYY-MM-DD
            const formattedDate = this.formatDate(post.date);

            resultDiv.innerHTML = `
                <a href="${post.url}" class="result-link" target="_blank" rel="noopener noreferrer">
                    <h3 class="result-title">${highlightedTitle}</h3>
                    <div class="result-meta">
                        <span class="result-date">${formattedDate}</span>
                        ${post.tags && post.tags.length > 0 ? 
                            `<span class="result-tags">${post.tags.map(tag => `#${tag}`).join(' ')}</span>` 
                            : ''}
                    </div>
                    ${post.description ? `<p class="result-description">${post.description}</p>` : ''}
                </a>
            `;

            return resultDiv;
        });

        // Append all results
        resultItems.forEach(item => container.appendChild(item));
        container.style.display = 'block';
    }

    /**
     * Highlight matching keywords in text
     * @param {string} text - The text to highlight
     * @param {Array<string>} keywords - Keywords to highlight
     * @returns {string} HTML string with highlighted keywords
     */
    highlightMatch(text, keywords) {
        if (!text || !keywords || keywords.length === 0) {
            return text || '';
        }

        let result = text;

        // Sort keywords by length (longest first) to avoid partial replacements
        const sortedKeywords = [...keywords].sort((a, b) => b.length - a.length);

        for (const keyword of sortedKeywords) {
            if (!keyword) continue;

            // Escape special regex characters
            const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            
            // Create case-insensitive regex with Unicode support
            const regex = new RegExp(`(${escapedKeyword})`, 'gi');
            
            result = result.replace(regex, '<mark>$1</mark>');
        }

        return result;
    }

    /**
     * Display an error message in the search results container
     * @param {string} containerSelector - CSS selector for results container
     * @param {string} message - Error message to display
     */
    displayError(containerSelector, message = '搜索索引加载失败，请刷新页面重试') {
        const container = document.querySelector(containerSelector);
        if (!container) {
            console.error(`Results container not found: ${containerSelector}`);
            return;
        }

        container.innerHTML = `<div class="search-error">${message}</div>`;
        container.style.display = 'block';
    }
}

// Export for use in other modules (if using module system)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchEngine;
}
