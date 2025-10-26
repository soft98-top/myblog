"""
主题管理模块
负责加载、验证和管理博客主题
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ThemeError(Exception):
    """主题错误"""
    pass


class Theme:
    """主题管理器"""
    
    def __init__(self, theme_dir: str):
        """
        初始化主题管理器
        
        Args:
            theme_dir: 主题目录路径
        """
        self.theme_dir = Path(theme_dir)
        self._metadata: Dict[str, Any] = {}
        self._loaded = False
    
    def load(self) -> bool:
        """
        加载主题
        
        Returns:
            加载是否成功
            
        Raises:
            ThemeError: 主题目录不存在或主题结构无效
        """
        if not self.theme_dir.exists():
            raise ThemeError(f"主题目录不存在: {self.theme_dir}")
        
        if not self.theme_dir.is_dir():
            raise ThemeError(f"主题路径不是目录: {self.theme_dir}")
        
        # 加载主题元数据
        theme_json_path = self.theme_dir / 'theme.json'
        if theme_json_path.exists():
            try:
                with open(theme_json_path, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
            except json.JSONDecodeError as e:
                raise ThemeError(f"主题元数据文件格式错误: {e}")
            except Exception as e:
                raise ThemeError(f"无法读取主题元数据: {e}")
        else:
            # 如果没有 theme.json，使用默认元数据
            self._metadata = {
                'name': self.theme_dir.name,
                'version': '1.0.0',
                'templates': {}
            }
        
        # 验证主题结构
        if not self.validate_structure():
            raise ThemeError("主题结构验证失败")
        
        self._loaded = True
        return True
    
    def validate_structure(self) -> bool:
        """
        验证主题结构是否符合规范
        
        Returns:
            验证是否通过
            
        Raises:
            ThemeError: 主题结构不符合规范
        """
        # 检查必需的目录
        templates_dir = self.theme_dir / 'templates'
        if not templates_dir.exists() or not templates_dir.is_dir():
            raise ThemeError(f"主题缺少 templates 目录: {templates_dir}")
        
        # 检查必需的模板文件
        required_templates = ['base.html', 'index.html', 'post.html']
        for template_name in required_templates:
            template_path = templates_dir / template_name
            if not template_path.exists():
                raise ThemeError(f"主题缺少必需的模板文件: {template_name}")
        
        # static 目录是可选的，但如果存在应该是目录
        static_dir = self.theme_dir / 'static'
        if static_dir.exists() and not static_dir.is_dir():
            raise ThemeError(f"static 路径存在但不是目录: {static_dir}")
        
        return True
    
    def has_template(self, template_name: str) -> bool:
        """
        检查主题是否配置了指定的模板
        
        Args:
            template_name: 模板名称（如 'index', 'post', 'encrypted_post'）
            
        Returns:
            是否配置了该模板
        """
        if not self._loaded:
            return False
        
        templates_config = self._metadata.get('templates', {})
        return template_name in templates_config
    
    def get_template(self, template_name: str) -> str:
        """
        获取模板文件路径
        
        Args:
            template_name: 模板名称（如 'index', 'post', 'encrypted_post'）
            
        Returns:
            模板文件的绝对路径字符串
            
        Raises:
            ThemeError: 主题未加载或模板文件不存在
        """
        if not self._loaded:
            raise ThemeError("主题尚未加载，请先调用 load() 方法")
        
        # 检查元数据中是否有模板映射
        templates_config = self._metadata.get('templates', {})
        
        # 必须在配置中定义
        if template_name not in templates_config:
            raise ThemeError(f"主题未配置模板: {template_name}")
        
        actual_filename = templates_config[template_name]
        
        # 确保文件名有 .html 扩展名
        if not actual_filename.endswith('.html'):
            actual_filename += '.html'
        
        template_path = self.theme_dir / 'templates' / actual_filename
        
        if not template_path.exists():
            raise ThemeError(f"模板文件不存在: {actual_filename}")
        
        return str(template_path)
    
    def get_static_dir(self) -> str:
        """
        获取静态资源目录路径
        
        Returns:
            静态资源目录的绝对路径字符串，如果不存在返回空字符串
            
        Raises:
            ThemeError: 主题未加载
        """
        if not self._loaded:
            raise ThemeError("主题尚未加载，请先调用 load() 方法")
        
        static_dir = self.theme_dir / 'static'
        
        if static_dir.exists() and static_dir.is_dir():
            return str(static_dir)
        
        return ""
    
    def get_templates_dir(self) -> str:
        """
        获取模板目录路径
        
        Returns:
            模板目录的绝对路径字符串
            
        Raises:
            ThemeError: 主题未加载
        """
        if not self._loaded:
            raise ThemeError("主题尚未加载，请先调用 load() 方法")
        
        return str(self.theme_dir / 'templates')
    
    @property
    def name(self) -> str:
        """
        获取主题名称
        
        Returns:
            主题名称
        """
        if not self._loaded:
            return ""
        return self._metadata.get('name', self.theme_dir.name)
    
    @property
    def version(self) -> str:
        """
        获取主题版本
        
        Returns:
            主题版本
        """
        if not self._loaded:
            return ""
        return self._metadata.get('version', '1.0.0')
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """
        获取主题元数据
        
        Returns:
            主题元数据字典
        """
        if not self._loaded:
            raise ThemeError("主题尚未加载，请先调用 load() 方法")
        return self._metadata.copy()
