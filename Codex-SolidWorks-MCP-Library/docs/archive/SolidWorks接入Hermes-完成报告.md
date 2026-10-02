# SolidWorks MCP 接入 Hermes — 完成报告

**日期**：2026-09-29
**结果**：✅ **全部打通，已实测验证**

---

## 一、验证结果（实测数据）

```
MCP initialize      ✅ 成功
  serverInfo        {"name": "SolidWorks MCP Server", "version": "4.0.10"}
  protocolVersion   2024-11-05

tools/list          ✅ 149 个工具
  前15个           open_model, create_part, create_assembly, create_drawing,
                   close_model, create_extrusion, create_revolve, get_dimension,
                   set_dimension, set_units, create_cut_extrude, add_fillet,
                   create_sweep, create_loft, insert_component

tools/call          ✅ 链路通
  调用              list_components → {"status":"error","message":"No active model"}
  说明              预期结果（SW 开着但无打开文档），证明 RPC→COM 全通

SolidWorks COM      ✅ RevisionNumber = 34.1.1
stdout 污染         ✅ 0 行非 JSON 输出
```

---

## 二、最终部署结构

| 组件 | 路径 | 说明 |
|---|---|---|
| Python 环境 | `D:\swmcp-env` | Python **3.13.15**（conda 创建） |
| 项目源码 | `<DEPLOYMENT_ROOT>` | 从 E 盘复制，含 SW2026 适配修改 |
| pip 缓存 | `D:\pip-cache` | 避免写 C 盘 |
| Hermes 配置 | `~/.hermes/config.yaml` | `mcp_servers.solidworks`，`enabled: true` |
| 配置备份 | `~/.hermes/config.yaml.bak-before-solidworks` | 修改前备份 |

**全程未占用 C 盘空间**（pip 内部临时目录除外，占用极小）。

---

## 三、对原项目做的修改（共 3 处）

### 修改 1：`src/utils/start_sw2020_stable.py` 第 11 行

放开年份限制，从只允许 2020 扩展为 2020–2026：

```python
# 原
parser.add_argument('--year', type=int, choices=[2020], required=True)
# 改
parser.add_argument('--year', type=int, choices=[2020, 2021, 2022, 2023, 2024, 2025, 2026], required=True)
```

### 修改 2：`src/utils/start_sw2020_stable.py` 第 21-45 行

注册表预检从**硬编码 SW2020** 改为**按 --year 推导 + 回退**：

```python
# 原（写死 2020）
import winreg
with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'SldWorks.Application.28\\CLSID') as key:
    winreg.QueryValueEx(key, None)

# 改（按年份推导，带回退和清晰报错）
import winreg
_progid_candidates = [
    'SldWorks.Application.%d' % (args.year - 1992),   # 2026 -> .34
    'SldWorks.Application',                            # 回退：版本无关 ProgID
]
_probe_error = None
for _progid in _progid_candidates:
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, _progid + '\\CLSID') as key:
            winreg.QueryValueEx(key, None)
        _probe_error = None
        break
    except OSError as exc:
        _probe_error = exc
if _probe_error is not None:
    raise RuntimeError(...)  # 带列出尝试过的 ProgID
```

### 修改 3：新增 `README.md`（补漏）

`pyproject.toml` 声明 `readme = "README.md"`，但**原打包文件中没有这个文件**（只有 `README.en.md` / `README.es-ES.md` / `README_CAE.md`），导致 `pip install` 在元数据生成阶段直接失败：

```
OSError: Readme file does not exist: README.md
error: metadata-generation-failed
```

**解决**：`cp README.en.md README.md`

> ⚠️ **建议反馈给上游**：这是打包疏漏，任何人在干净环境 `pip install -e .` 都会失败。

---

## 四、关键发现：SolidWorks 2026 的 ProgID 是 `.34`，不是 `.31`

实机注册表探测结果：

```
SldWorks.Application      → CLSID {666aaee2-...} → E:\...\SOLIDWORKS Corp2026\SLDWORKS.exe  ✅
SldWorks.Application.29   → E:\2021SW\SOLIDWORKS\sldworks.exe     (旧 SW2021)
SldWorks.Application.30   → D:\2022SW\SOLIDWORKS\SLDWORKS.exe     (旧 SW2022)
SldWorks.Application.31   → 无 CLSID 子键（空壳，陷阱！）
SldWorks.Application.34   → CLSID {666aaee2-...} → 2026 主程序  ✅
```

**验证**：`app.RevisionNumber` 返回 `34.1.1`，与 `.34` 对应，公式 `major = year - 1992` 成立（2026 − 1992 = 34）。

**好消息**：项目底层的 `pywin32_adapter.py` 和 `sw_type_info.py` **本来就用了这个公式**，无需修改。版本锁是人为加在入口脚本上的。

---

## 五、Hermes 配置

```yaml
mcp_servers:
  # ... 其他 MCP ...
  solidworks:
    command: /mnt/c/Windows/System32/cmd.exe
    args:
    - /c
    - D:\swmcp-env\python.exe
    - <DEPLOYMENT_ROOT>\src\utils\start_sw2020_stable.py
    - --real
    - --year
    - '2026'
    timeout: 300
    connect_timeout: 60
    enabled: true
```

**设计说明**：

- 用 `cmd.exe` 桥接 —— 与本机其他 MCP（filesystem / playwright / sequential-thinking / yahoo-finance）一致的既有模式
- `timeout: 300` —— SolidWorks COM 操作慢（建模、Simulation 求解可能数十秒）
- `connect_timeout: 60` —— 首次 COM 连接可能触发 SolidWorks 启动
- 路径必须用 Windows 格式（`D:\...`），因为实际执行者是 Windows 进程

---

## 六、使用前提与注意事项

### 前提条件

1. **SolidWorks 2026 必须处于运行状态** —— COM 是连接现有实例，不是无头启动
2. 需要有一个**打开的文档**才能调用建模类工具（否则报 `No active model`）

### 已知注意事项

| 项 | 说明 |
|---|---|
| 依赖版本漂移 | 实际装了 `fastmcp 4.0.10` / `mcp 2.2.0`，项目声明 `fastmcp>=3.2.2` / `mcp>=1.28.1`。实测协议兼容。 |
| PydanticAI agent | 启动时警告 `OPENAI_API_KEY is not configured` —— 该 agent 是可选功能，不影响 MCP 工具。 |
| 工具数 | `tools/list` 返回 **149**；启动日志打印 133（注册阶段计数），两者口径不同。 |
| `gen_py` 缓存 | 若遇到 `Member not found`，删除 `%TEMP%\gen_py\` 重启（见项目 CLAUDE.md 坑 #2）。 |
| 磁盘空间 | 本机清理记录已省略。**注意 pip 内部会写 `%TEMP%\pip-*`**，属正常行为。 |

---

## 七、未覆盖项

- **未做真实建模端到端测试**：只验证到「工具可调用」，未实际执行 `create_part` + `create_extrusion` 并回读特征树。建议首次使用时先跑一个简单建模流程确认。
- **Simulation 静态分析未验证**：需要 `SIMULATION` 模块的 Interop DLL，且 `simulation/build.ps1` 需针对 E 盘安装路径重新执行：

  ```powershell
  cd <DEPLOYMENT_ROOT>
  $env:SW2020_INSTALL_DIR = 'E:\Program Files\SOLIDWORKS Corp2026\SOLIDWORKS'
  powershell -NoProfile -File .\simulation\build.ps1 -InstallDir $env:SW2020_INSTALL_DIR
  ```

  > 注意环境变量名仍叫 `SW2020_INSTALL_DIR`（历史遗留），赋值为 2026 路径即可。

---

## 八、生效方式

Hermes 的 MCP 配置在 gateway 启动时加载，因此需要重启：

```bash
hermes gateway restart
```

重启后执行 `hermes mcp list` 应能看到 `solidworks` 及其 149 个工具。

---

*报告生成：Hermes · 2026-09-29 · 全部结论基于实机验证*
