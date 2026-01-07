"""
模板渲染模块
负责使用 Jinja2 模板引擎渲染各种页面
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from copy import copy
import base64
import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .config import Config
from .theme import Theme
from .markdown_processor import Post

# AES-GCM Encryption Constants
PBKDF2_ITERATIONS = 100_000  # OWASP recommended minimum
KEY_SIZE = 32  # 256 bits
SALT_SIZE = 16  # 128 bits
NONCE_SIZE = 12  # 96 bits (recommended for GCM)


class RendererError(Exception):
    """渲染器错误"""
    pass


class Renderer:
    """模板渲染器"""
    
    def __init__(self, theme: Theme, config: Config):
        """
        初始化渲染器
        
        Args:
            theme: 主题管理器实例
            config: 配置管理器实例
        """
        self.theme = theme
        self.config = config
        
        # 初始化 Jinja2 环境
        templates_dir = theme.get_templates_dir()
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True,  # 自动转义 HTML，防止 XSS
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 注册自定义过滤器
        self._register_filters()
        
        # 注册全局变量
        self._register_globals()
    
    def _register_filters(self) -> None:
        """注册自定义 Jinja2 过滤器"""
        
        def format_date(date: datetime, format_str: Optional[str] = None) -> str:
            """格式化日期"""
            if format_str is None:
                format_str = self.config.get('theme_config.date_format', '%Y-%m-%d')
            return date.strftime(format_str)
        
        def truncate_html(html: str, length: int = 200) -> str:
            """截断 HTML 内容（简单实现）"""
            # 移除 HTML 标签
            import re
            text = re.sub(r'<[^>]+>', '', html)
            if len(text) <= length:
                return text
            return text[:length].rsplit(' ', 1)[0] + '...'
        
        self.env.filters['format_date'] = format_date
        self.env.filters['truncate_html'] = truncate_html
    
    def _register_globals(self) -> None:
        """注册全局变量"""
        # 站点配置
        site_config = self.config.get_site_config()
        self.env.globals['site'] = site_config
        
        # 获取 base_path（用于子目录部署）
        base_path = site_config.get('base_path', '').strip()
        if base_path and not base_path.startswith('/'):
            base_path = '/' + base_path
        if base_path.endswith('/'):
            base_path = base_path[:-1]
        
        # 完整配置（供高级使用）
        self.env.globals['config'] = self.config.data
        
        # 主题信息
        self.env.globals['theme'] = {
            'name': self.theme.name,
            'version': self.theme.version
        }
        
        # 当前年份（用于版权信息等）
        self.env.globals['current_year'] = datetime.now().year
        
        # URL 生成函数
        def url_for(path: str) -> str:
            """生成页面 URL（支持 base_path）"""
            if not path.startswith('/'):
                path = '/' + path
            return f'{base_path}{path}'
        
        def url_for_static(path: str) -> str:
            """生成静态资源 URL"""
            # 确保路径以 static/ 开头
            if not path.startswith('static/'):
                path = f'static/{path}'
            return url_for(path)
        
        self.env.globals['url_for'] = url_for
        self.env.globals['url_for_static'] = url_for_static
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive a 256-bit encryption key from password using PBKDF2.
        
        Args:
            password: User's password (any length)
            salt: Random salt (16 bytes)
        
        Returns:
            256-bit (32-byte) encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode('utf-8'))
    
    def _encrypt_content(self, content: str, password: str) -> str:
        """
        Encrypt content using AES-GCM-256.
        
        Args:
            content: Plaintext content (HTML)
            password: User's password
        
        Returns:
            Encrypted data in format: "salt:nonce:ciphertext" (Base64 encoded)
        """
        # Generate random salt and nonce
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        
        # Derive key from password
        key = self._derive_key(password, salt)
        
        # Encrypt using AES-GCM
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(content.encode('utf-8')) + encryptor.finalize()
        
        # GCM mode automatically includes authentication tag
        # Tag is appended to ciphertext by the library
        ciphertext_with_tag = ciphertext + encryptor.tag
        
        # Encode components as Base64
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        nonce_b64 = base64.b64encode(nonce).decode('utf-8')
        ciphertext_b64 = base64.b64encode(ciphertext_with_tag).decode('utf-8')
        
        return f"{salt_b64}:{nonce_b64}:{ciphertext_b64}"
    
    def render_index(self, posts: List[Post], page: int = 1, 
                    posts_per_page: Optional[int] = None) -> str:
        """
        渲染首页
        
        Args:
            posts: 文章列表（已排序）
            page: 当前页码（从 1 开始）
            posts_per_page: 每页文章数，None 表示不分页
            
        Returns:
            渲染后的 HTML 字符串
            
        Raises:
            RendererError: 渲染失败
        """
        try:
            template_path = self.theme.get_template('index')
            template = self.env.get_template(Path(template_path).name)
        except Exception as e:
            raise RendererError(f"无法加载首页模板: {e}")
        
        # 处理分页
        pagination = None
        if posts_per_page is not None and posts_per_page > 0:
            total_posts = len(posts)
            total_pages = (total_posts + posts_per_page - 1) // posts_per_page
            
            start_idx = (page - 1) * posts_per_page
            end_idx = start_idx + posts_per_page
            posts = posts[start_idx:end_idx]
            
            # 获取 base_path
            site_config = self.config.get_site_config()
            base_path = site_config.get('base_path', '').strip()
            if base_path and not base_path.startswith('/'):
                base_path = '/' + base_path
            if base_path.endswith('/'):
                base_path = base_path[:-1]
            
            # 生成分页 URL
            prev_url = f'{base_path}/' if page == 2 else f'{base_path}/page/{page - 1}.html' if page > 1 else None
            next_url = f'{base_path}/page/{page + 1}.html' if page < total_pages else None
            
            pagination = {
                'page': page,
                'total_pages': total_pages,
                'total_posts': total_posts,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_page': page - 1 if page > 1 else None,
                'next_page': page + 1 if page < total_pages else None,
                'prev_url': prev_url,
                'next_url': next_url
            }
        
        try:
            html = template.render(
                posts=posts,
                pagination=pagination
            )
            return html
        except Exception as e:
            raise RendererError(f"渲染首页失败: {e}")
    
    def render_post(self, post: Post) -> str:
        """
        渲染文章详情页
        
        Args:
            post: 文章对象
            
        Returns:
            渲染后的 HTML 字符串
            
        Raises:
            RendererError: 渲染失败
        """
        # 检查文章是否加密
        if post.encrypted and post.password:
            # 检查主题是否支持加密模板
            if self.theme.has_template('encrypted_post'):
                # 主题支持加密 - 加密内容并使用加密模板
                try:
                    encrypted_html = self._encrypt_content(post.html, post.password)
                    
                    # 使用加密模板渲染，传递加密后的内容
                    template_path = self.theme.get_template('encrypted_post')
                    template = self.env.get_template(Path(template_path).name)
                    
                    # 创建一个包含加密内容的上下文
                    context = {
                        'post': post,
                        'encrypted_html': encrypted_html
                    }
                    
                    # 临时替换 post.html 为加密内容
                    original_html = post.html
                    post.html = encrypted_html
                    html = template.render(post=post)
                    post.html = original_html  # 恢复原始内容
                    
                    return html
                except Exception as e:
                    raise RendererError(f"渲染加密文章失败: {e}")
            else:
                # 主题不支持加密 - 显示提示信息
                try:
                    template_path = self.theme.get_template('post')
                    template = self.env.get_template(Path(template_path).name)
                    
                    # 临时替换内容为提示信息
                    original_html = post.html
                    post.html = '<div class="encrypted-notice"><p>⚠️ 当前主题不支持加密文章功能</p><p>请更换支持加密的主题或联系主题开发者添加加密模板支持。</p></div>'
                    html = template.render(post=post)
                    post.html = original_html  # 恢复原始内容
                    
                    return html
                except Exception as e:
                    raise RendererError(f"渲染文章页失败: {e}")
        
        # 普通文章 - 正常渲染
        try:
            template_path = self.theme.get_template('post')
            template = self.env.get_template(Path(template_path).name)
            html = template.render(post=post)
            return html
        except Exception as e:
            raise RendererError(f"渲染文章页失败: {e}")

    def render_archive(self, posts: List[Post]) -> str:
        """
        渲染归档页
        
        归档页按年份和月份组织文章列表
        
        Args:
            posts: 文章列表（已排序）
            
        Returns:
            渲染后的 HTML 字符串
            
        Raises:
            RendererError: 渲染失败
        """
        # 尝试使用归档模板，如果不存在则使用首页模板
        try:
            if self.theme.has_template('archive'):
                template_path = self.theme.get_template('archive')
            else:
                template_path = self.theme.get_template('index')
            template = self.env.get_template(Path(template_path).name)
        except Exception as e:
            raise RendererError(f"无法加载归档模板: {e}")
        
        # 按年份和月份组织文章
        archive_data = self._organize_posts_by_date(posts)
        
        try:
            html = template.render(
                posts=posts,
                archive=archive_data,
                is_archive=True
            )
            return html
        except Exception as e:
            raise RendererError(f"渲染归档页失败: {e}")
    
    def render_tag_page(self, tag: str, posts: List[Post]) -> str:
        """
        渲染标签页
        
        显示特定标签下的所有文章
        
        Args:
            tag: 标签名称
            posts: 该标签下的文章列表
            
        Returns:
            渲染后的 HTML 字符串
            
        Raises:
            RendererError: 渲染失败
        """
        # 尝试使用标签模板，如果不存在则使用首页模板
        try:
            if self.theme.has_template('tag'):
                template_path = self.theme.get_template('tag')
            else:
                template_path = self.theme.get_template('index')
            template = self.env.get_template(Path(template_path).name)
        except Exception as e:
            raise RendererError(f"无法加载标签模板: {e}")
        
        try:
            html = template.render(
                tag=tag,
                posts=posts,
                is_tag_page=True
            )
            return html
        except Exception as e:
            raise RendererError(f"渲染标签页失败: {e}")
    
    def render_tags_index(self, tags_data: Dict[str, List[Post]]) -> str:
        """
        渲染标签索引页
        
        显示所有标签及其文章数量
        
        Args:
            tags_data: 标签到文章列表的映射
            
        Returns:
            渲染后的 HTML 字符串
            
        Raises:
            RendererError: 渲染失败
        """
        # 尝试使用标签索引模板，如果不存在则使用首页模板
        try:
            if self.theme.has_template('tags'):
                template_path = self.theme.get_template('tags')
            else:
                template_path = self.theme.get_template('index')
            template = self.env.get_template(Path(template_path).name)
        except Exception as e:
            raise RendererError(f"无法加载标签索引模板: {e}")
        
        # 准备标签统计数据
        tags_stats = [
            {
                'name': tag,
                'count': len(posts),
                'posts': posts
            }
            for tag, posts in sorted(tags_data.items())
        ]
        
        try:
            html = template.render(
                tags=tags_stats,
                is_tags_index=True
            )
            return html
        except Exception as e:
            raise RendererError(f"渲染标签索引页失败: {e}")
    
    def _organize_posts_by_date(self, posts: List[Post]) -> Dict[int, Dict[int, List[Post]]]:
        """
        按年份和月份组织文章
        
        Args:
            posts: 文章列表
            
        Returns:
            嵌套字典: {year: {month: [posts]}}
        """
        archive: Dict[int, Dict[int, List[Post]]] = {}
        
        for post in posts:
            year = post.date.year
            month = post.date.month
            
            if year not in archive:
                archive[year] = {}
            
            if month not in archive[year]:
                archive[year][month] = []
            
            archive[year][month].append(post)
        
        return archive
    
    def get_all_tags(self, posts: List[Post]) -> Dict[str, List[Post]]:
        """
        从文章列表中提取所有标签
        
        Args:
            posts: 文章列表
            
        Returns:
            标签到文章列表的映射
        """
        tags_map: Dict[str, List[Post]] = {}
        
        for post in posts:
            for tag in post.tags:
                if tag not in tags_map:
                    tags_map[tag] = []
                tags_map[tag].append(post)
        
        return tags_map
