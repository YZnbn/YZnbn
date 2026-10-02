"""Stock Thermometer v4 — 启动器（兼容 dev + frozen）"""
import sys, os, traceback


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def main():
    base = get_base_dir()
    res = get_resource_dir()
    os.chdir(base)
    sys.path.insert(0, base)

    os.makedirs(os.path.join(base, "cache"), exist_ok=True)

    try:
        import tkinter as tk
        import yaml

        from data import CacheDB, Fetcher, Cleaner
        from factors import FactorComputer, CausalSelector, Normalizer
        from model import RegimeDetector, Scorer, BudgetAdapter
        from gui.widgets import Thermometer, StrategySelector, FactorBar, MetricCards
        from gui.charts import HistoryChart, ReturnChart, FactorHeatmap

        config_path = os.path.join(res, "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if "data" in config:
            config["data"]["cache_dir"] = os.path.join(base, "cache")

        root = tk.Tk()
        from gui.app import App
        app = App(root, config)
        root.mainloop()

    except Exception as e:
        traceback.print_exc()
        input("\n按 Enter 退出...")


if __name__ == "__main__":
    main()
