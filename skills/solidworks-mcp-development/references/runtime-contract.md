# 当前实现与运行契约

2026-09-13 检查的实现仓库：`C:/Users/28699/Documents/Codex/SolidWorksMCP/SolidworksMCP-python`。
实际 Codex 注册位于 `C:/Users/28699/.codex/config.toml` 的 `[mcp_servers.solidworks]`，使用仓库 `.venv/Scripts/python.exe` 和 `src/utils/start_sw2020_stable.py --real --year 2020`，cwd 为该仓库。
旧 `.mcp.json` 含 2026 入口；只有相关配置变更获得授权时才处理，不作为普通开发附带修改。

## 按症状定位
- 初始化、版本注册、意外启动：`src/utils/start_sw2020_stable.py`。
- 串行、批量建模、请求状态：`src/solidworks_mcp/sw2020_workflow.py`。
- 边/孔检查、圆角和螺纹等细节：`src/solidworks_mcp/sw2020_details.py`。
- 已有工作流和历史验收：`SW2020_WORKFLOW.md`。
- COM 特定问题：`docs/agents/com-api-pitfalls.md`。

这些文件中部分当前未被 Git 跟踪，修改前重新检查状态，保留内容；历史验收不能替代修改后的受影响检查。

## 必须保持的行为
初始化只检查注册信息并注册工具，不能激活 COM；现有启动器检查 SW2020 ProgID 注册项。需要真实 SW 的 tools/call 才在串行保护下连接。所有修改同一文档的路径应遵守并发约束；旧入口或手工调用可能不遵守当前锁。

stdout 必须保持 JSON-RPC；错误日志使用 stderr。参数和文档身份错误应尽可能在第一处修改前返回。暂时改变图形、AddToDB 或显示状态后必须恢复；恢复失败应显式报告。

批量请求记录位于 `local_state/sw2020/requests/`；时序日志位于 `local_state/sw2020/timings.jsonl`。保留请求日志以支持重放保护，不当作可随意清理的缓存。
相同 ID 与相同参数返回历史状态，不同参数重用 ID 应拒绝；历史成功不是本次现场验证。`partial` 或悬停 `started` 需要先检查文档，不能自动重复修改。原生 COM 卡住时不另起写入会话或强杀进程。

## 受影响验证
- 启动逻辑：以 stdio 客户端完成 initialize 和 tools/list，观察 SW 进程集合没有因发现工具而变化。
- 参数/文档守卫：在隔离测试副本验证拒绝输入未产生额外特征。
- 重放/异常恢复：验证请求状态、无重复副作用和显示状态恢复。
- 建模实现：检查实际特征与几何、保存及关键参数；不以进程零退出码代替结果。
只运行与改动有关的检查，记录限制，不把普通文档改动扩大为完整 COM 回归。
