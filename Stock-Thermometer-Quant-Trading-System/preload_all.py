#!/usr/bin/env python3
"""全 A 股预加载器启动脚本（双击运行）"""
import subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
cmd = [sys.executable, "data", "preloader.py"]

try:
    subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as e:
    print(f"\n错误：{e}")
except FileNotFoundError:
    print("Python 未找到，请确认已安装 Python 并加入 PATH")
except KeyboardInterrupt:
    print("\n已中断（可随时重新运行，断点续传）")

input("\n按 Enter 退出...")
