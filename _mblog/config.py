"""
配置管理模块
负责加载、验证和管理博客配置文件
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigError(Exception):
    """配置文件错误"""
    pass


class Config:
    """配置管理器"""
    
    def __init__(self, config_path: str):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._config_data: Dict[str, Any] = {}
        self._loaded = False
    
    def load(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置数据字典
            
        Raises:
            ConfigError: 配置文件不存在或格式错误
        """
        if not self.config_path.exists():
            raise ConfigError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigError(f"无法读取配置文件: {e}")
        
        # 验证配置
        if not self.validate():
            raise ConfigError("配置文件验证失败")
        
        self._loaded = True
        return self._config_data
    
    def validate(self) -> bool:
        """
        验证配置文件格式
        
        Returns:
            验证是否通过
            
        Raises:
            ConfigError: 配置缺少必需字段
        """
        # 检查必需的顶级字段
        required_sections = ['site', 'build']
        for section in required_sections:
            if section not in self._config_data:
                raise ConfigError(f"配置缺少必需的部分: {section}")
        
        # 验证 site 配置
        site_config = self._config_data.get('site', {})
        required_site_fields = ['title', 'description', 'author']
        for field in required_site_fields:
            if field not in site_config:
                raise ConfigError(f"site 配置缺少必需字段: {field}")
        
        # 验证 build 配置
        build_config = self._config_data.get('build', {})
        required_build_fields = ['output_dir', 'theme']
        for field in required_build_fields:
            if field not in build_config:
                raise ConfigError(f"build 配置缺少必需字段: {field}")
        
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项（支持点号分隔的嵌套键）
        
        Args:
            key: 配置键，支持 'site.title' 这样的嵌套访问
            default: 默认值
            
        Returns:
            配置值
        """
        if not self._loaded:
            raise ConfigError("配置尚未加载，请先调用 load() 方法")
        
        # 支持嵌套键访问
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_theme_config(self) -> Dict[str, Any]:
        """
        获取主题相关配置
        
        Returns:
            主题配置字典
        """
        return self.get('theme_config', {})
    
    def get_site_config(self) -> Dict[str, Any]:
        """
        获取站点配置
        
        Returns:
            站点配置字典
        """
        return self.get('site', {})
    
    def get_build_config(self) -> Dict[str, Any]:
        """
        获取构建配置
        
        Returns:
            构建配置字典
        """
        return self.get('build', {})
    
    @property
    def data(self) -> Dict[str, Any]:
        """
        获取完整的配置数据
        
        Returns:
            配置数据字典
        """
        if not self._loaded:
            raise ConfigError("配置尚未加载，请先调用 load() 方法")
        return self._config_data
