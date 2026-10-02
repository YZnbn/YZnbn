"""Test GUI step by step"""
import sys, os, traceback

# Resolve the project root from this file so the test works from any checkout path.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

log = open("gui_debug.log", "w", encoding="utf-8")

def logprint(msg):
    print(msg, flush=True)
    log.write(msg + "\n")
    log.flush()

try:
    logprint("Step 1: importing tkinter...")
    import tkinter as tk
    from tkinter import ttk
    logprint("  OK")

    logprint("Step 2: creating Tk root...")
    root = tk.Tk()
    logprint("  OK")

    logprint("Step 3: setting title...")
    root.title("Stock Thermometer v3")
    root.geometry("800x600")
    logprint("  OK")

    logprint("Step 4: adding label...")
    label = tk.Label(root, text="GUI is working! Close this window.", font=("Arial", 14))
    label.pack(pady=50)
    logprint("  OK")

    logprint("Step 5: importing project modules...")
    import yaml
    from data import CacheDB, Fetcher, Cleaner
    from factors import FactorComputer, CausalSelector, Normalizer
    from model import RegimeDetector, Scorer, BudgetAdapter
    logprint("  OK - all imports pass")

    logprint("Step 6: starting mainloop...")
    root.after(0, lambda: logprint("Mainloop started, window should be visible"))
    root.mainloop()
    logprint("Mainloop ended")

except Exception as e:
    logprint(f"ERROR: {e}")
    traceback.print_exc(file=log)
    traceback.print_exc()
    input("Press Enter to close...")
finally:
    log.close()
