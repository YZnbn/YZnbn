"""Diagnostic: check Python environment and imports"""
import sys
print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print()

# Check working dir
import os
print(f"cwd: {os.getcwd()}")
print(f"project root in path: {os.path.dirname(os.path.abspath(__file__))}")
print()

# Check packages
packages = ["akshare", "pandas", "numpy", "scipy", "matplotlib", "yaml", "tkinter",
            "threading", "sqlite3"]
for pkg in packages:
    try:
        __import__(pkg)
        print(f"  {pkg}: OK")
    except ImportError as e:
        print(f"  {pkg}: MISSING - {e}")

print()

# Check project imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from data import CacheDB, Fetcher, Cleaner
    print("  data.* : OK")
except Exception as e:
    print(f"  data.* : FAIL - {e}")

try:
    from factors import FactorComputer, CausalSelector, Normalizer
    print("  factors.* : OK")
except Exception as e:
    print(f"  factors.* : FAIL - {e}")

try:
    from model import RegimeDetector, Scorer, BudgetAdapter
    print("  model.* : OK")
except Exception as e:
    print(f"  model.* : FAIL - {e}")

try:
    from gui.widgets import Thermometer, FactorBar
    print("  gui.widgets : OK")
except Exception as e:
    print(f"  gui.widgets : FAIL - {e}")

try:
    from gui.charts import HistoryChart, PerformanceChart
    print("  gui.charts : OK")
except Exception as e:
    print(f"  gui.charts : FAIL - {e}")

print()
print("Diagnostic complete.")
