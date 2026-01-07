"""
静态文件生成模块
负责生成最终的静态 HTML 文件和复制静态资源
"""
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import Config
from .theme import Theme
from .renderer import Renderer
from .markdown_processor import Post


class GenerationError(Exception):
    """生成错误"""
    pass


class StaticGenerator:
    """静态文件生成器"""
    
    def __init__(self, config: Config, theme: Theme, renderer: Renderer, posts: List[Post]):
        """
        初始化生成器
        
        Args:
            config: 配置管理器实例
            theme: 主题管理器实例
            renderer: 渲染器实例
            posts: 文章列表
        """
        self.config = config
        self.theme = theme
        self.renderer = renderer
        self.posts = posts
        
        # 获取输出目录
        output_dir = self.config.get('build.output_dir', 'public')
        self.output_dir = Path(output_dir)
    
    def generate(self) -> bool:
        """
        执行生成流程
        
        Returns:
            生成是否成功
            
        Raises:
            GenerationError: 生成过程中出现错误
        """
        try:
            print("开始生成静态文件...")
            
            # 1. 准备输出目录
            self._prepare_output_dir()
            
            # 2. 复制静态资源
            self._copy_static_assets()
            
            # 3. 生成所有页面
            self._generate_pages()
            
            print(f"✓ 静态文件生成完成，输出目录: {self.output_dir}")
            return True
            
        except Exception as e:
            raise GenerationError(f"生成失败: {e}")
    
    def _prepare_output_dir(self) -> None:
        """
        准备输出目录
        
        如果目录存在，清空内容；如果不存在，创建目录
        """
        if self.output_dir.exists():
            # 清空现有内容
            shutil.rmtree(self.output_dir)
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"✓ 输出目录已准备: {self.output_dir}")
    
    def _copy_static_assets(self) -> None:
        """
        复制静态资源（CSS、JS、图片等）
        
        从主题的 static 目录复制到输出目录的 static 目录
        """
        static_src = self.theme.get_static_dir()
        
        if not static_src or not Path(static_src).exists():
            print("  主题没有静态资源目录，跳过")
        else:
            static_dest = self.output_dir / 'static'
            
            try:
                shutil.copytree(static_src, static_dest)
                print(f"✓ 静态资源已复制: {static_src} -> {static_dest}")
            except Exception as e:
                raise GenerationError(f"复制静态资源失败: {e}")
        
        # 复制文章中引用的图片
        self._copy_post_images()
    
    def _generate_pages(self) -> None:
        """
        生成所有页面
        
        包括：
        - 首页和分页
        - 文章详情页
        - 标签页
        - 归档页（可选）
        - RSS 订阅（可选）
        - Sitemap（可选）
        - 搜索索引（可选）
        """
        print("开始生成页面...")
        
        # 生成首页和分页
        self._generate_index_pages()
        
        # 生成文章详情页
        self._generate_post_pages()
        
        # 生成标签相关页面
        self._generate_tag_pages()
        
        # 生成归档页（可选）
        self._generate_archive_page()
        
        # 生成 RSS 订阅（可选）
        if self.config.get('build.generate_rss', True):
            self._generate_rss()
        
        # 生成 Sitemap（可选）
        if self.config.get('build.generate_sitemap', True):
            self._generate_sitemap()
        
        # 生成搜索索引
        self._generate_search_index()
        
        print(f"✓ 所有页面生成完成")
    
    def _generate_index_pages(self) -> None:
        """
        生成首页和分页
        
        根据配置决定是否启用分页
        """
        # 获取分页配置
        posts_per_page = self.config.get('theme_config.posts_per_page')
        
        if posts_per_page is None or posts_per_page <= 0:
            # 不分页，生成单个首页
            html = self.renderer.render_index(self.posts)
            index_path = self.output_dir / 'index.html'
            self._write_file(index_path, html)
            print(f"  ✓ 首页: index.html")
        else:
            # 分页
            total_posts = len(self.posts)
            total_pages = (total_posts + posts_per_page - 1) // posts_per_page
            
            for page in range(1, total_pages + 1):
                html = self.renderer.render_index(
                    self.posts, 
                    page=page, 
                    posts_per_page=posts_per_page
                )
                
                if page == 1:
                    # 第一页作为首页
                    index_path = self.output_dir / 'index.html'
                else:
                    # 其他页面放在 page 目录下
                    page_dir = self.output_dir / 'page'
                    page_dir.mkdir(exist_ok=True)
                    index_path = page_dir / f'{page}.html'
                
                self._write_file(index_path, html)
            
            print(f"  ✓ 首页和分页: {total_pages} 页")
    
    def _generate_post_pages(self) -> None:
        """
        生成文章详情页
        
        每篇文章生成一个 HTML 文件，保留原始目录结构
        使用 relative_path 来确定输出路径
        """
        posts_dir = self.output_dir / 'posts'
        posts_dir.mkdir(exist_ok=True)
        
        for post in self.posts:
            html = self.renderer.render_post(post)
            # 使用 relative_path 保留目录结构
            post_path = posts_dir / f'{post.relative_path}.html'
            self._write_file(post_path, html)
        
        print(f"  ✓ 文章详情页: {len(self.posts)} 篇")
    
    def _generate_tag_pages(self) -> None:
        """
        生成标签相关页面
        
        包括：
        - 标签索引页（所有标签列表）
        - 每个标签的文章列表页
        """
        # 获取所有标签
        tags_map = self.renderer.get_all_tags(self.posts)
        
        if not tags_map:
            print("  没有标签，跳过标签页生成")
            return
        
        tags_dir = self.output_dir / 'tags'
        tags_dir.mkdir(exist_ok=True)
        
        # 生成标签索引页
        try:
            tags_index_html = self.renderer.render_tags_index(tags_map)
            tags_index_path = tags_dir / 'index.html'
            self._write_file(tags_index_path, tags_index_html)
        except Exception as e:
            # 如果没有标签索引模板，跳过
            print(f"  跳过标签索引页: {e}")
        
        # 生成每个标签的页面
        for tag, posts in tags_map.items():
            # 标签名转换为文件名（处理特殊字符）
            tag_filename = self._sanitize_filename(tag)
            
            html = self.renderer.render_tag_page(tag, posts)
            tag_path = tags_dir / f'{tag_filename}.html'
            self._write_file(tag_path, html)
        
        print(f"  ✓ 标签页: {len(tags_map)} 个标签")
    
    def _generate_archive_page(self) -> None:
        """
        生成归档页（可选）
        
        显示按时间组织的所有文章
        """
        try:
            html = self.renderer.render_archive(self.posts)
            archive_path = self.output_dir / 'archive.html'
            self._write_file(archive_path, html)
            print(f"  ✓ 归档页: archive.html")
        except Exception as e:
            # 如果没有归档模板，跳过
            print(f"  跳过归档页: {e}")
    
    def _write_file(self, filepath: Path, content: str) -> None:
        """
        写入文件
        
        Args:
            filepath: 文件路径
            content: 文件内容
            
        Raises:
            GenerationError: 写入失败
        """
        try:
            # 确保父目录存在
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise GenerationError(f"写入文件失败 {filepath}: {e}")
    
    def _copy_post_images(self) -> None:
        """
        复制文章中引用的图片到输出目录
        
        将所有文章中引用的相对路径图片复制到 assets/images 目录
        """
        images_dest = self.output_dir / 'assets' / 'images'
        images_dest.mkdir(parents=True, exist_ok=True)
        
        copied_count = 0
        
        for post in self.posts:
            if not post.images:
                continue
            
            for img_path in post.images:
                img_src = Path(img_path)
                
                if not img_src.exists():
                    print(f"  警告: 图片不存在: {img_path}")
                    continue
                
                # 获取图片相对于 md 目录的路径
                try:
                    # 假设 md_dir 是 'md'
                    md_dir = Path(self.config.get('build.md_dir', 'md')).resolve()
                    rel_path = img_src.relative_to(md_dir)
                    
                    # 目标路径
                    img_dest = images_dest / rel_path
                    
                    # 确保目标目录存在
                    img_dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(img_src, img_dest)
                    copied_count += 1
                    
                except ValueError:
                    # 图片不在 md_dir 下，跳过
                    print(f"  警告: 图片不在 md 目录下: {img_path}")
                    continue
                except Exception as e:
                    print(f"  警告: 复制图片失败 {img_path}: {e}")
                    continue
        
        if copied_count > 0:
            print(f"✓ 文章图片已复制: {copied_count} 个文件")
    
    def _sanitize_filename(self, name: str) -> str:
        """
        清理文件名，移除或替换不安全的字符
        
        Args:
            name: 原始名称
            
        Returns:
            安全的文件名
        """
        import re
        
        # 替换空格和特殊字符为连字符
        safe_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', name)
        safe_name = re.sub(r'[\s_]+', '-', safe_name)
        safe_name = safe_name.strip('-').lower()
        
        # 如果结果为空，使用默认名称
        if not safe_name:
            safe_name = 'tag'
        
        return safe_name
    
    def _generate_rss(self) -> None:
        """
        生成 RSS 订阅文件
        
        生成符合 RSS 2.0 标准的 XML 文件
        """
        try:
            from datetime import datetime
            import html
            
            site_config = self.config.get_site_config()
            site_url = site_config.get('url', 'https://example.com').rstrip('/')
            
            # RSS 头部
            rss_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
                '<channel>',
                f'  <title>{html.escape(site_config.get("title", "博客"))}</title>',
                f'  <link>{html.escape(site_url)}</link>',
                f'  <description>{html.escape(site_config.get("description", ""))}</description>',
                f'  <language>{site_config.get("language", "zh-CN")}</language>',
                f'  <atom:link href="{html.escape(site_url)}/rss.xml" rel="self" type="application/rss+xml" />',
            ]
            
            # 添加文章（最多 20 篇）
            for post in self.posts[:20]:
                post_url = f'{site_url}/posts/{post.relative_path}.html'
                pub_date = post.date.strftime('%a, %d %b %Y %H:%M:%S +0000')
                
                # 清理 HTML 内容作为描述
                description = post.description or post.html[:200]
                
                rss_lines.extend([
                    '  <item>',
                    f'    <title>{html.escape(post.title)}</title>',
                    f'    <link>{html.escape(post_url)}</link>',
                    f'    <description>{html.escape(description)}</description>',
                    f'    <pubDate>{pub_date}</pubDate>',
                    f'    <guid>{html.escape(post_url)}</guid>',
                ])
                
                # 添加分类（标签）
                for tag in post.tags:
                    rss_lines.append(f'    <category>{html.escape(tag)}</category>')
                
                rss_lines.append('  </item>')
            
            rss_lines.extend([
                '</channel>',
                '</rss>'
            ])
            
            # 写入文件
            rss_content = '\n'.join(rss_lines)
            rss_path = self.output_dir / 'rss.xml'
            self._write_file(rss_path, rss_content)
            
            print(f"  ✓ RSS 订阅: rss.xml")
        except Exception as e:
            print(f"  跳过 RSS 生成: {e}")
    
    def _generate_sitemap(self) -> None:
        """
        生成 Sitemap 文件
        
        生成符合 Sitemap 协议的 XML 文件
        """
        try:
            from datetime import datetime
            import html
            
            site_config = self.config.get_site_config()
            site_url = site_config.get('url', 'https://example.com').rstrip('/')
            
            # Sitemap 头部
            sitemap_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            ]
            
            # 首页
            sitemap_lines.extend([
                '  <url>',
                f'    <loc>{html.escape(site_url)}/</loc>',
                f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>',
                '    <changefreq>daily</changefreq>',
                '    <priority>1.0</priority>',
                '  </url>',
            ])
            
            # 归档页
            sitemap_lines.extend([
                '  <url>',
                f'    <loc>{html.escape(site_url)}/archive.html</loc>',
                f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.8</priority>',
                '  </url>',
            ])
            
            # 标签索引页
            sitemap_lines.extend([
                '  <url>',
                f'    <loc>{html.escape(site_url)}/tags/</loc>',
                f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.8</priority>',
                '  </url>',
            ])
            
            # 所有文章
            for post in self.posts:
                post_url = f'{site_url}/posts/{post.relative_path}.html'
                lastmod = post.date.strftime('%Y-%m-%d')
                
                sitemap_lines.extend([
                    '  <url>',
                    f'    <loc>{html.escape(post_url)}</loc>',
                    f'    <lastmod>{lastmod}</lastmod>',
                    '    <changefreq>monthly</changefreq>',
                    '    <priority>0.6</priority>',
                    '  </url>',
                ])
            
            # 所有标签页
            tags_map = self.renderer.get_all_tags(self.posts)
            for tag in tags_map.keys():
                tag_filename = self._sanitize_filename(tag)
                tag_url = f'{site_url}/tags/{tag_filename}.html'
                
                sitemap_lines.extend([
                    '  <url>',
                    f'    <loc>{html.escape(tag_url)}</loc>',
                    f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>',
                    '    <changefreq>weekly</changefreq>',
                    '    <priority>0.5</priority>',
                    '  </url>',
                ])
            
            sitemap_lines.append('</urlset>')
            
            # 写入文件
            sitemap_content = '\n'.join(sitemap_lines)
            sitemap_path = self.output_dir / 'sitemap.xml'
            self._write_file(sitemap_path, sitemap_content)
            
            print(f"  ✓ Sitemap: sitemap.xml")
        except Exception as e:
            print(f"  跳过 Sitemap 生成: {e}")
    
    def _generate_search_index(self) -> None:
        """
        生成搜索索引 JSON 文件
        
        创建包含所有文章元数据的 JSON 文件，用于客户端搜索功能
        """
        try:
            import json
            from datetime import datetime
            
            # 构建搜索索引数据
            posts_data = []
            for post in self.posts:
                post_data = {
                    'title': post.title,
                    'url': f'/posts/{post.relative_path}.html',
                    'date': post.date.isoformat(),
                    'tags': post.tags,
                    'description': post.description,
                    'relative_path': post.relative_path
                }
                posts_data.append(post_data)
            
            # 创建完整的索引对象
            search_index = {
                'posts': posts_data,
                'generated_at': datetime.now().isoformat(),
                'total_posts': len(posts_data)
            }
            
            # 写入 JSON 文件
            index_path = self.output_dir / 'search-index.json'
            json_content = json.dumps(search_index, ensure_ascii=False, indent=2)
            self._write_file(index_path, json_content)
            
            print(f"  ✓ 搜索索引: search-index.json ({len(posts_data)} 篇文章)")
        except Exception as e:
            print(f"  跳过搜索索引生成: {e}")
