# SW2020 环境与接口

以下路径在 2026-09-13 落地时检查存在；执行时核对实时配置、目标文档和实际工具 schema。

- 实现仓库：`C:/Users/28699/Documents/Codex/SolidWorksMCP/SolidworksMCP-python`
- Python：仓库内 `.venv/Scripts/python.exe`
- Codex 配置：`C:/Users/28699/.codex/config.toml` 的 `[mcp_servers.solidworks]`
- 启动参数：`src/utils/start_sw2020_stable.py --real --year 2020`，cwd 为实现仓库。
- 现有说明：仓库 `SW2020_WORKFLOW.md`；仅在相关调用或恢复时读取。
- 仓库 `.mcp.json` 仍含旧的 2026 入口，不等同于当前 Codex 实际配置。不要直接拿它启动，也不要因建模任务自动修改配置。

连接前先检查已注册工具和目标实例；连接测试可能启动 SolidWorks，应限于已授权的建模或连接诊断任务。普通聊天、服务发现与注册检查不应激活 COM。
真实连接可使用 `sw2020_preflight`，核对返回版本、文档身份和草图编辑状态；不能把历史版本记录当作本次验证。

现有 `sw2020_build_batch` 支持部分草图及凸台/切除组合，`sw2020_verify_save` 用于相关验证与保存，`sw2020_details` 提供部分细节操作。以实际工具 schema 和代码为准，不假设任意特征、方程或装配都已被封装。
遇到封装缺口可使用直接 COM 或经过检查的脚本；不把真实参数关联简化为多处填写常数。必要时读取仓库 `docs/agents/com-api-pitfalls.md`。

直接 SolidWorks API 长度采用米；自定义 MCP 可能使用 mm，逐项以字段说明为准。转换只在清楚的接口边界进行。
COM 连接失败时先核查会话、进程权限与版本；不得用可能创建实例的 Dispatch 调用作为被动探测。
