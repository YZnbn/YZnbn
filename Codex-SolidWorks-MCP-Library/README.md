# Codex SolidWorks MCP Library

整理自本机 `Codex-SolidWorks-MCP-当前源码与配置` 便携包，供 SolidWorks MCP、Codex 配置和配套 skills 统一归档。MCP 源码沿用随包附带的 MIT License；归档时保留了原项目的许可和版权文件。

## 目录

- `SolidworksMCP-python/`：MCP 源码、部署脚本、依赖声明、测试和项目文档。
- `skills/solidworks-2020-modeling/`：SolidWorks 2020 建模 skill。
- `skills/solidworks-mcp-development/`：SolidWorks MCP 开发 skill。
- `integrations/codex/`：当前与历史 Codex MCP 配置示例；路径中的 `<REPO_ROOT>` 需要替换成实际源码目录。
- `docs/archive/`：原便携包中的接入说明、安全扫描报告和完成报告。

## 本机运行

源码目录的 `.mcp.json` 使用相对部署脚本路径。将此库放到目标位置后，先安装项目依赖并检查 `SolidworksMCP-python/README.en.md` 或本地化文档，再按 `integrations/codex/solidworks-mcp.toml.example` 配置 Codex。运行 SolidWorks COM 自动化前，应打开并确认目标 SolidWorks 版本。

配置模板不含可直接使用的个人绝对路径。归档报告中的机器路径已替换为占位符，示例中的用户目录也已改为 `%USERPROFILE%` 或 `Path.home()`。

## 来源与完整性

原便携包未带 Git 历史；本目录保留其源码、测试、skills、两份 Codex 配置示例和随包文档。没有复制 Python 虚拟环境、模型产物或 Git 历史。
