# 结构化计划与结果比对

本机现有 MCP 的 `sw2020-plan/1` 使用原 SW2020 COM 执行层。适用于新建未保存、无实体的零件，支持矩形、圆、多边形草图和凸台拉伸/切除，草图支撑为已有基准面。修改现有模型、方程关联、曲面、装配等需求继续选择对应真实 API，不强行转换成此计划。

先检查当前工具目录是否有 `sw2020_validate_plan`、`sw2020_execute_plan`、`sw2020_capture_result`、`sw2020_compare_results`。旧服务进程需要重新连接才能加载新代码；不要因缺少工具而重装或覆盖 MCP 配置。

## 使用

- 计划使用 `schema_version: sw2020-plan/1`、`target_year: 2020`、`units: mm`。`nodes` 各含 `id`、`depends_on` 和 `operation`；operation 沿用 `sw2020_build_batch` 的 Group 结构。校验工具返回确定的依赖顺序、编译结果和计划 SHA-256，且不连接 SolidWorks。
- `expected.volume_mm3` 必填，从图纸、解析计算或可信参考取得；不要用本次执行后的结果反填预期。可补面积、重心、实体及面/边/顶点数量。容差按设计精度选择；无可信体积预期时使用原工作流，不编造验收值。
- 执行前通过 preflight 确认当前文档。创建独立零件后再次读取真实名称，将其作为 `expected_document`；输出选择全新的绝对 `.SLDPRT` 路径。请求 ID 在此逻辑请求期间保持不变。
- execute_plan 复用原串行锁与批量建模，并在比对通过后验证保存。保存不等于磁盘重开验证。需要检验持久化时，capture_result 获取快照，仅关闭自己刚保存且 dirty=false 的测试/交付文档，再打开文件捕获快照，用 compare_results 对比。

## 结果边界

- `success`：本次执行、指标比对和保存完成；`disk_reopen_verified` 仍为 false，除非另有实际重开证据。
- `partial`：可能已生成几何，预期不符时不自动保存。读取比较条目、请求日志及现场再处理，不换 ID 盲目重试。
- `started`：调用中断后结果不明；检查现场。相同 ID 的响应是历史记录，不是重新建模或实时验证。
- 快照比较返回 `matched`/`mismatch` 和逐项差异。面/边/顶点数量相同不证明 BREP 完全一致，体积等指标也不证明约束、材料或工程图合格。Snapshot 的重心来自质量属性，不能当作真实材料已赋值的证据。
- 计划中的数值是建模配方参数，不会自动生成 SolidWorks 全局变量、尺寸方程或几何约束。要求联动的参数仍需实际建立并验证关联。

本机实现：`C:/Users/28699/Documents/Codex/SolidWorksMCP/SolidworksMCP-python/src/solidworks_mcp/sw2020_plan.py`。
示例：同仓库 `examples/sw2020/four_hole_plan.json`。
计划请求日志：同仓库 `local_state/sw2020/plan_requests/`；底层批量日志继续保留在 `requests/`。
