"""Launch actual Stock Thermometer GUI with full debug output"""
import sys, os, traceback

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

print("=== Stock Thermometer Debug Launcher ===", flush=True)

try:
    print("1. Importing tkinter...", flush=True)
    import tkinter as tk

    print("2. Importing yaml...", flush=True)
    import yaml

    print("3. Importing data...", flush=True)
    from data import CacheDB, Fetcher, Cleaner

    print("4. Importing factors...", flush=True)
    from factors import FactorComputer, CausalSelector, Normalizer

    print("5. Importing model...", flush=True)
    from model import RegimeDetector, Scorer, BudgetAdapter

    print("6. Importing gui widgets...", flush=True)
    from gui.widgets import Thermometer, FactorBar

    print("7. Importing gui charts...", flush=True)
    from gui.charts import HistoryChart, ReturnChart

    print("8. All imports OK!", flush=True)

    print("9. Loading config...", flush=True)
    config_path = os.path.join(PROJECT_DIR, "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print("10. Creating Tk root...", flush=True)
    root = tk.Tk()
    root.title("Stock Thermometer v3 - Debug")

    print("11. Creating App...", flush=True)
    from gui.app import App
    app = App(root, config)

    print("12. Starting mainloop...", flush=True)
    root.mainloop()

    print("13. Mainloop ended.", flush=True)

except Exception as e:
    print(f"\nERROR: {e}", flush=True)
    traceback.print_exc()
    input("\nPress Enter to exit...")

input("Press Enter to close...")
