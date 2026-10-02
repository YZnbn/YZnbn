# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Stock Thermometer — onedir mode"""

import os, sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None
project_root = os.path.dirname(os.path.abspath(SPEC))

# 收集所有关键原生库
packages = ["akshare", "lxml", "scipy", "numpy", "pandas", "py_mini_racer"]
all_bins, all_datas, all_hidden = [], [], []

for pkg in packages:
    try:
        d, b, h = collect_all(pkg)
        all_datas.extend(d)
        all_bins.extend(b)
        all_hidden.extend(h)
    except Exception as e:
        print(f"WARNING: collect_all({pkg}) failed: {e}")

a = Analysis(
    [os.path.join(project_root, "launch_packaged.py")],
    pathex=[project_root],
    binaries=all_bins,
    datas=[
        (os.path.join(project_root, "config.yaml"), "."),
        *all_datas,
    ],
    hiddenimports=[
        *all_hidden,
        "akshare.stock",
        "akshare.index",
        "lxml.etree",
        "lxml._elementpath",
        "lxml.html",
        "py_mini_racer",
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backend_bases",
        "yaml",
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "PIL",
        "PIL.Image",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tigramite",
        "torch",
        "tensorflow",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="StockThermometer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="StockThermometer",
)
