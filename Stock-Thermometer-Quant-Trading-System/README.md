# Stock Thermometer

面向 A 股历史数据分析、因子筛选和虚拟交易实验的个人研究项目。系统结合多因子评分与 PCMCI 条件独立性检验，提供市场状态识别、预算适配、桌面可视化、历史回测及虚拟持仓跟踪。

## 功能模块

- **数据**：通过 AkShare 等数据源获取行情，清洗后缓存到本地 SQLite。
- **因子**：计算动量、估值、质量、低波动、流动性和市场情绪等因子。
- **因果筛选与评分**：使用 Tigramite/PCMCI 探索因子与未来收益之间的条件关联，并结合市场状态对候选标的评分。
- **界面与模拟**：Tkinter 桌面界面展示市场温度、因子、候选标的和虚拟交易结果。
- **实验报告**：[PDF](report/虚拟交易实验报告.pdf)、[Word](report/虚拟交易实验报告.docx)、[HTML](report/virtual_trading_report.html)。

## 运行

需要 Windows、Python 3.10+ 和 Tkinter。安装依赖后，从项目目录启动：

```powershell
python -m pip install -r requirements.txt
python launch_v4.py
```

首次运行需要网络获取行情数据；本地缓存会在 `cache/` 下生成。`python data/preloader.py` 可单独运行全市场数据预加载。

## 目录

```text
backtest/       回测引擎
data/           行情获取、清洗和缓存
factors/        因子计算与 PCMCI 筛选
gui/            Tkinter 界面与图表
model/          市场状态、评分和预算适配
simulation/     虚拟交易实验
report/         2026 年 6 月的实验报告和图表
```

## 实验说明

仓库中的报告记录一段已结束的虚拟交易实验，样本仅覆盖 13 个交易日。报告也讨论了样本偏差、回撤控制和策略容量等局限；其中结果属于历史模拟记录，不代表实盘业绩或未来表现，也不是投资建议。

仓库不包含行情数据库、缓存模型、虚拟账户运行状态、运行日志或个人桌面截图。上述缓存与状态文件会由本地运行生成，并由 `.gitignore` 排除。
