"""Stock Thermometer v3 — 打包版入口（兼容 dev + frozen）"""
import sys, os, traceback


def get_base_dir():
    """exe 所在目录（缓存/历史文件存这里）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """资源目录：打包后在 sys._MEIPASS，开发时在脚本目录"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def main():
    base = get_base_dir()
    res = get_resource_dir()

    os.chdir(base)
    sys.path.insert(0, base)

    # 确保缓存目录存在
    cache_dir = os.path.join(base, "cache")
    os.makedirs(cache_dir, exist_ok=True)

    try:
        import tkinter as tk
        import yaml

        from data import CacheDB, Fetcher, Cleaner
        from factors import FactorComputer, CausalSelector, Normalizer
        from model import RegimeDetector, Scorer, BudgetAdapter
        from gui.widgets import Thermometer, FactorBar
        from gui.charts import HistoryChart, ReturnChart

        # 加载配置（打包后从 MEIPASS 读，开发模式从项目根读）
        config_path = os.path.join(res, "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 把 cache_dir 写回 config 让后续模块使用相对路径
        if "data" in config:
            config["data"]["cache_dir"] = cache_dir

        root = tk.Tk()

        from gui.app import App
        app = App(root, config)
        root.mainloop()

    except Exception as e:
        traceback.print_exc()
        input("\n程序出错，按 Enter 退出...")


if __name__ == "__main__":
    main()
