#!/usr/bin/env python3
"""
博客静态文件生成脚本
此脚本完全独立，不依赖 mblog 工具
"""
import sys
from pathlib import Path

# 将 _mblog 添加到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from _mblog.config import Config
from _mblog.markdown_processor import MarkdownProcessor
from _mblog.theme import Theme
from _mblog.renderer import Renderer
from _mblog.generator import StaticGenerator


def main():
    """主函数"""
    try:
        print("开始生成静态博客文件...")
        
        # 加载配置
        print("→ 加载配置文件...")
        config = Config("config.json")
        config.load()
        
        # 加载主题
        theme_name = config.get("build", {}).get("theme", "default")
        theme_dir = Path("theme")
        print(f"→ 加载主题: {theme_name}")
        theme = Theme(str(theme_dir))
        theme.load()
        
        # 处理 Markdown 文件
        print("→ 处理 Markdown 文章...")
        processor = MarkdownProcessor("md")
        posts = processor.load_posts()
        print(f"  找到 {len(posts)} 篇文章")
        
        # 初始化渲染器
        print("→ 初始化渲染器...")
        renderer = Renderer(theme, config)
        
        # 生成静态文件
        print("→ 生成静态文件...")
        generator = StaticGenerator(config, theme, renderer, posts)
        generator.generate()
        
        output_dir = config.get("build", {}).get("output_dir", "public")
        print(f"\n✓ 成功生成 {len(posts)} 篇文章")
        print(f"✓ 输出目录: {output_dir}")
        print("\n博客已生成完成！")
        
    except FileNotFoundError as e:
        print(f"\n✗ 文件未找到: {e}", file=sys.stderr)
        print("请确保配置文件和必要的目录存在", file=sys.stderr)
        sys.exit(1)
        
    except ValueError as e:
        print(f"\n✗ 配置错误: {e}", file=sys.stderr)
        print("请检查配置文件格式是否正确", file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        print(f"\n✗ 生成失败: {e}", file=sys.stderr)
        import traceback
        print("\n详细错误信息:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
