#!/usr/bin/env python3
"""
Markdown 处理模块
负责解析 Markdown 文件、提取 frontmatter 元数据、转换为 HTML
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import frontmatter
import markdown


@dataclass
class Post:
    """文章数据模型"""
    filepath: str              # 源文件路径
    slug: str                  # URL slug
    relative_path: str         # 相对于 md 目录的路径（不含扩展名）
    title: str                 # 标题
    date: datetime             # 发布日期
    author: str                # 作者
    description: str           # 描述/摘要
    tags: List[str]            # 标签
    content: str               # 原始 Markdown
    html: str                  # 转换后的 HTML
    encrypted: bool = False    # 是否加密
    password: str = ""         # 加密密码
    metadata: Dict[str, Any] = field(default_factory=dict)  # 其他元数据
    images: List[str] = field(default_factory=list)  # 文章中引用的图片路径


class MarkdownProcessor:
    """Markdown 处理器"""
    
    def __init__(self, md_dir: str):
        """
        初始化 Markdown 处理器
        
        Args:
            md_dir: Markdown 文件目录路径
        """
        self.md_dir = Path(md_dir).resolve()
        self.md_converter = markdown.Markdown(
            extensions=[
                'extra',           # 支持表格、代码块等扩展语法
                'codehilite',      # 代码高亮
                'toc',             # 目录生成
                'meta',            # 元数据支持
                'nl2br',           # 换行转 <br>
                'sane_lists'       # 更好的列表处理
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'linenums': False
                }
            }
        )
    
    def load_posts(self) -> List[Post]:
        """
        加载所有文章（递归扫描子目录）
        
        Returns:
            文章列表，按日期降序排序
        """
        if not self.md_dir.exists():
            return []
        
        posts = []
        # 递归查找所有 .md 文件
        for md_file in self.md_dir.rglob('*.md'):
            try:
                post = self.parse_post(str(md_file))
                posts.append(post)
            except Exception as e:
                print(f"警告: 无法解析文件 {md_file}: {e}")
                continue
        
        # 按日期降序排序（最新的在前）
        posts.sort(key=lambda p: p.date, reverse=True)
        return posts
    
    def parse_post(self, filepath: str) -> Post:
        """
        解析单个文章文件
        
        Args:
            filepath: 文章文件路径
            
        Returns:
            Post 对象
            
        Raises:
            ValueError: 如果文件格式错误或缺少必需字段
        """
        filepath_obj = Path(filepath)
        
        # 读取文件内容
        with open(filepath_obj, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # 提取 frontmatter 和内容
        metadata, content = self._extract_frontmatter(file_content)
        
        # 验证必需字段
        if 'title' not in metadata:
            raise ValueError(f"文章缺少必需的 frontmatter 字段: title")
        
        # 提取字段
        title = metadata['title']
        
        # 处理日期
        if 'date' in metadata:
            date = self._parse_date(metadata['date'])
        else:
            # 如果没有日期，使用文件修改时间
            date = datetime.fromtimestamp(filepath_obj.stat().st_mtime)
        
        # 提取其他字段
        author = metadata.get('author', '')
        description = metadata.get('description', '')
        tags = metadata.get('tags', [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',')]
        
        # 提取图片路径并转换 Markdown 到 HTML
        images, html = self._process_markdown_with_images(content, filepath_obj)
        
        # 生成 slug
        slug = self._generate_slug(title, date)
        
        # 计算相对路径（相对于 md 目录，不含扩展名）
        relative_path = self._get_relative_path(filepath_obj)
        
        # 提取加密相关字段
        encrypted = metadata.get('encrypted', False)
        password = metadata.get('password', '')
        
        # 创建 Post 对象
        post = Post(
            filepath=str(filepath_obj),
            slug=slug,
            relative_path=relative_path,
            title=title,
            date=date,
            author=author,
            description=description,
            tags=tags,
            content=content,
            html=html,
            encrypted=encrypted,
            password=password,
            metadata=metadata,
            images=images
        )
        
        return post
    
    def _extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        提取 YAML frontmatter
        
        Args:
            content: 文件内容
            
        Returns:
            (元数据字典, Markdown 内容)
        """
        try:
            post = frontmatter.loads(content)
            return dict(post.metadata), post.content
        except Exception as e:
            # 如果没有 frontmatter，返回空元数据
            return {}, content
    
    def _convert_to_html(self, markdown_text: str) -> str:
        """
        转换 Markdown 到 HTML
        
        Args:
            markdown_text: Markdown 文本
            
        Returns:
            HTML 字符串
        """
        # 重置转换器状态
        self.md_converter.reset()
        
        # 转换
        html = self.md_converter.convert(markdown_text)
        
        return html
    
    def _generate_slug(self, title: str, date: datetime) -> str:
        """
        生成 URL slug
        
        格式: YYYY-MM-DD-title-in-lowercase
        
        Args:
            title: 文章标题
            date: 发布日期
            
        Returns:
            slug 字符串
        """
        # 日期部分
        date_str = date.strftime('%Y-%m-%d')
        
        # 标题部分：转小写，替换空格和特殊字符为连字符
        title_slug = title.lower()
        
        # 移除或替换特殊字符
        # 保留字母、数字、中文字符，其他替换为连字符
        title_slug = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', title_slug)
        title_slug = re.sub(r'[\s_]+', '-', title_slug)
        title_slug = title_slug.strip('-')
        
        # 组合
        slug = f"{date_str}-{title_slug}"
        
        return slug
    
    def _parse_date(self, date_value: Any) -> datetime:
        """
        解析日期值
        
        Args:
            date_value: 日期值（可能是字符串、datetime 对象等）
            
        Returns:
            datetime 对象
        """
        if isinstance(date_value, datetime):
            return date_value
        
        # 处理 date 对象（转换为 datetime）
        from datetime import date
        if isinstance(date_value, date):
            return datetime.combine(date_value, datetime.min.time())
        
        if isinstance(date_value, str):
            # 尝试多种日期格式
            formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
            
            # 如果都失败，抛出异常
            raise ValueError(f"无法解析日期格式: {date_value}")
        
        raise ValueError(f"不支持的日期类型: {type(date_value)}")
    
    def _get_relative_path(self, filepath: Path) -> str:
        """
        获取相对于 md 目录的路径（不含扩展名）
        
        Args:
            filepath: 文件的完整路径
            
        Returns:
            相对路径字符串，例如: "welcome" 或 "tech/python-tips"
        """
        try:
            # 获取相对于 md_dir 的路径
            rel_path = filepath.relative_to(self.md_dir)
            # 移除 .md 扩展名
            return str(rel_path.with_suffix(''))
        except ValueError:
            # 如果文件不在 md_dir 下，使用文件名（不含扩展名）
            return filepath.stem
    
    def _process_markdown_with_images(self, markdown_text: str, md_filepath: Path) -> Tuple[List[str], str]:
        """
        处理 Markdown 中的图片引用，提取图片路径并转换路径
        
        Args:
            markdown_text: Markdown 文本
            md_filepath: Markdown 文件的路径
            
        Returns:
            (图片文件路径列表, 转换后的 HTML)
        """
        images = []
        
        # 查找所有图片引用: ![alt](path)
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image(match):
            alt_text = match.group(1)
            img_path = match.group(2)
            
            # 跳过外部链接（http:// 或 https://）
            if img_path.startswith(('http://', 'https://', '//')):
                return match.group(0)
            
            # 跳过绝对路径
            if img_path.startswith('/'):
                return match.group(0)
            
            # 处理相对路径
            # 解析图片的绝对路径
            md_dir = md_filepath.parent
            img_abs_path = (md_dir / img_path).resolve()
            
            # 检查图片文件是否存在
            if img_abs_path.exists() and img_abs_path.is_file():
                # 记录图片路径（相对于 md_dir 的父目录）
                try:
                    # 获取相对于 markdown 文件所在目录的路径
                    rel_to_md = img_abs_path.relative_to(self.md_dir)
                    images.append(str(img_abs_path))
                    
                    # 生成新的图片路径（在输出目录中的路径）
                    # 格式: /assets/images/{relative_path}
                    new_img_path = f'/assets/images/{rel_to_md}'
                    
                    return f'![{alt_text}]({new_img_path})'
                except ValueError:
                    # 图片不在 md_dir 下，保持原样
                    pass
            
            # 如果图片不存在或无法处理，保持原样
            return match.group(0)
        
        # 替换所有图片引用
        processed_markdown = re.sub(img_pattern, replace_image, markdown_text)
        
        # 转换为 HTML
        html = self._convert_to_html(processed_markdown)
        
        return images, html
