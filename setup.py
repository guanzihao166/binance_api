#!/usr/bin/env python3
"""
币安仓位监控系统 - 安装脚本
"""

import subprocess
import sys
import os

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 11):
        print("❌ Python版本过低，需要Python 3.11或更高")
        print(f"当前版本: {sys.version}")
        sys.exit(1)
    print(f"✓ Python版本 {sys.version.split()[0]} 符合要求")

def install_dependencies():
    """安装依赖"""
    print("\n📦 正在安装依赖包...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("✓ 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        sys.exit(1)

def verify_config():
    """验证配置文件"""
    print("\n⚙️ 正在验证配置文件...")
    
    if not os.path.exists('config.py'):
        print("❌ 未找到 config.py 文件")
        sys.exit(1)
    
    # 尝试导入config
    try:
        import config
        print("✓ 配置文件加载成功")
        print(f"  API密钥长度: {len(config.API_KEY)} 字符")
        return True
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False

def verify_installation():
    """验证安装"""
    print("\n🔍 正在验证安装...")
    
    required_modules = [
        'streamlit',
        'requests',
        'plotly',
        'pytz'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            missing.append(module)
    
    if missing:
        print(f"\n❌ 缺少依赖: {', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("币安仓位监控系统 - 安装向导")
    print("=" * 50)
    
    # 检查Python版本
    check_python_version()
    
    # 安装依赖
    install_dependencies()
    
    # 验证配置
    verify_config()
    
    # 验证安装
    if not verify_installation():
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✓ 安装完成！")
    print("=" * 50)
    print("\n使用方法:")
    print("  Windows: run.bat")
    print("  Linux/Mac: bash run.sh")
    print("  手动启动: streamlit run main.py")
    print("\n祝您使用愉快！")

if __name__ == '__main__':
    main()
