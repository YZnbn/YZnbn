# Hermes 接入 CAD-CAE-Agent（SolidWorks MCP）配置说明

**生成日期**：2026-09-29
**目标**：把 `SolidworksMCP-python`（SW 2026）作为 MCP server 接入 Hermes
**环境**：WSL 中的 Hermes ↔ Windows 上的 SolidWorks 2026

---

## 一、环境实测结论

| 项目 | 实测值 |
|---|---|
| SolidWorks 版本 | **2026** |
| 安装目录 | `E:\Program Files\SOLIDWORKS Corp2026\SOLIDWORKS\`（注意「Corp」与「2026」之间无空格） |
| 主程序 | `SLDWORKS.exe` ✅ 存在 |
| COM ProgID | `SldWorks.Application.31`（`.29`/`.30` 也有注册；`.28` = 2020，**本机无**） |
| Windows Python | 3.11.4（**不满足项目要求 3.13+**） |
| 磁盘 | C: 满（0 GB 可用）；E: 100 GB 可用；D: 371 GB 可用 |
| Hermes 位置 | WSL（Linux），通过 `/mnt/c/Windows/System32/cmd.exe` 桥接到 Windows |

**结论：必须把 Python 3.13 和项目 venv 放在 E 盘或 D 盘，绝不能放 C 盘。**

---

## 二、必须修改的代码（关键！）

`src/utils/start_sw2020_stable.py` 中**硬编码了 SolidWorks 2020 的注册表键**：

```python
import winreg
with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'SldWorks.Application.28\\CLSID') as key:
    winreg.QueryValueEx(key, None)
```

`.28` 对应 **SolidWorks 2020**，本机装的是 **2026（`.31`）**，**直接运行会抛 `FileNotFoundError`**。

### 修改方案

将版本号改为从命令行参数推导：

```python
# 原代码（硬编码 2020）
with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'SldWorks.Application.28\\CLSID') as key:
    winreg.QueryValueEx(key, None)

# 修改后（按 --year 推导，SW 版本号 = 年份 - 1992）
progid = f'SldWorks.Application.{args.year - 1992}'   # 2026 -> .34
# 若该键不存在，回退到无版本号 ProgID
try:
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f'{progid}\\CLSID') as key:
        winreg.QueryValueEx(key, None)
except FileNotFoundError:
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'SldWorks.Application\\CLSID') as key:
        winreg.QueryValueEx(key, None)
```

> ⚠️ **版本号映射需实测确认**。本机注册表同时存在 `.29` / `.30` / `.31` / `.34`，其中哪一个是 SW2026 的**主** ProgID 需通过启动 SolidWorks 后实测（见 §5 验证步骤）。
>
> SolidWorks ProgID 版本号规律并非严格等于「年份 − 1992」——SW2020 = `.28` 符合，但 SW2026 实测有 `.31` 和 `.34` 同时注册。**以实测为准。**

同时 `argparse` 的 `choices` 只有 2020：

```python
parser.add_argument('--year', type=int, choices=[2020], required=True)
```

需扩展为包含 2026：

```python
parser.add_argument('--year', type=int, choices=[2020, 2026], required=True)
```

---

## 三、安装步骤（全部避开 C 盘）

### 3.1 安装 Python 3.13 到 E 盘

```powershell
# 下载到 D 盘（C 盘满了）
cd D:\
curl.exe -L -o python-3.13.7-amd64.exe https://www.python.org/ftp/python/3.13.7/python-3.13.7-amd64.exe

# 安装到 E:\Python313，全用户安装（需要 UAC 提权）
Start-Process -FilePath 'D:\python-3.13.7-amd64.exe' `
  -ArgumentList '/quiet','InstallAllUsers=1','TargetDir=E:\Python313',`
                'PrependPath=1','Include_test=0','Include_launcher=1' `
  -Wait -Verb RunAs
```

验证：

```powershell
E:\Python313\python.exe -V    # 应输出 Python 3.13.x
```

### 3.2 建立项目环境（venv 放 D 盘，避开 C 盘）

```powershell
$proj = '<DEPLOYMENT_ROOT>'
# 假设项目已复制到此处（源：<SOURCE_ROOT>\SolidworksMCP-python）

cd $proj
E:\Python313\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

# 把 pip 缓存也移到 D 盘，避免撑爆 C 盘
$env:PIP_CACHE_DIR = 'D:\pip-cache'
.\.venv\Scripts\python.exe -m pip install -e .
```

> 仅安装**核心依赖**（22 个包）。**不要**装 `[dev,test,docs,vision,rag]` 这些可选组——它们会拉入 `torch`、`faiss-cpu`、`sentence-transformers` 等重量级包，占用数 GB 且对本任务无用。

### 3.3 验证 MCP server 能启动

```powershell
cd <DEPLOYMENT_ROOT>
# 先测 mock 模式（不需要 SolidWorks）
.\.venv\Scripts\python.exe -m solidworks_mcp.server --help
```

---

## 四、Hermes 配置

编辑 `~/.hermes/config.yaml`，在 `mcp_servers:` 段下添加：

```yaml
mcp_servers:
  # ... 现有配置 ...
  
  solidworks:
    command: /mnt/c/Windows/System32/cmd.exe
    args:
    - /c
    - <DEPLOYMENT_ROOT>\.venv\Scripts\python.exe
    - <DEPLOYMENT_ROOT>\src\utils\start_sw2020_stable.py
    - --real
    - --year
    - '2026'
    timeout: 300
```

**配置要点说明**：

- `command` 用 `cmd.exe` 桥接——这是本机 Hermes 接入 Windows 程序的既有模式（与 `filesystem`、`playwright`、`sequential-thinking` 一致）
- `timeout: 300` —— SolidWorks COM 操作较慢（建模、求解可能数十秒），比默认值放宽
- 路径必须用 **Windows 格式**（`D:\...`），因为实际执行者是 Windows 进程
- 用 `start_sw2020_stable.py` 而非 `server.py`——它是生产入口，有 COM 懒连接和串行化处理

---

## 五、验证清单

按顺序执行，每步确认后再进行下一步：

| # | 检查 | 命令 | 预期 |
|---|---|---|---|
| 1 | Python 3.13 可用 | `E:\Python313\python.exe -V` | `Python 3.13.x` |
| 2 | 依赖装好 | `<DEPLOYMENT_ROOT>\.venv\Scripts\python.exe -c "import fastmcp, mcp, pydantic_ai"` | 无报错 |
| 3 | 项目可导入 | `...python.exe -c "import solidworks_mcp; print(solidworks_mcp.__file__)"` | 输出路径 |
| 4 | **SolidWorks 已启动** | 手动打开 SolidWorks 2026 | 界面出现 |
| 5 | 确认 ProgID | 见下方 PS 脚本 | 输出可用 ProgID |
| 6 | MCP 工具列表 | Hermes 中执行 `hermes mcp list` 或查看工具加载 | 出现 solidworks 工具 |
| 7 | 端到端 | 让 Hermes 调一个只读工具（如列文档） | 返回真实 SolidWorks 状态 |

**第 5 步的 ProgID 探测脚本**：

```powershell
Get-ChildItem 'Registry::HKEY_CLASSES_ROOT' |
  Where-Object { $_.PSChildName -like 'SldWorks.Application*' } |
  Select-Object -ExpandProperty PSChildName
```

启动 SolidWorks 后，再检查哪个 ProgID 的 `LocalServer32` 有值——那个就是当前版本的正确 ProgID。

---

## 六、已知风险与限制

1. **`start_sw2020_stable.py` 是为 SW2020 写的**，虽然逻辑通用，但版本耦合点需要逐一排查（注册表键、`--year` choices、可能的 API 差异）。
2. **C 盘满**。必须彻底清理。否则 Windows 本身会出现异常（临时文件写不进、程序崩溃），任何安装都会失败。
3. **WSL 无法直接跑 SolidWorks COM**。必须通过 `cmd.exe` 桥接，这意味着：
   - 每次工具调用都有进程间开销
   - 路径必须写 Windows 格式
   - WSL 侧的 `/mnt/` 路径不能直接传给 MCP 工具
4. **模型/目录名异常**。`E:\Program Files\SOLIDWORKS Corp2026\SOLIDWORKS` 中「Corp2026」缺空格，这是安装时的既成事实，任何脚本若拼写为 `SOLIDWORKS Corp 2026` 都会失败。

---

## 七、备选方案（如果 SW2026 兼容性排查成本过高）

如果修改 `start_sw2020_stable.py` 适配 SW2026 的代价太大，可考虑：

**方案 A**：以 mock 模式接入，验证 Hermes ↔ MCP 协议链路正确性，真实建模在队友（装有 SW2020）的机器上执行。

**方案 B**：使用上游 `SolidworksMCP-python` 的通用入口 `server.py`，它支持 `SOLIDWORKS_VERSION` 环境变量：

```yaml
  solidworks:
    command: /mnt/c/Windows/System32/cmd.exe
    args: [/c, <DEPLOYMENT_ROOT>\.venv\Scripts\python.exe, -m, solidworks_mcp.server]
    env:
      SOLIDWORKS_VERSION: '2026'
      SOLIDWORKS_PATH: 'E:\Program Files\SOLIDWORKS Corp2026\SOLIDWORKS'
    timeout: 300
```

---

*本文档由 Hermes 生成于 2026-09-29，基于实机探测结果。*
