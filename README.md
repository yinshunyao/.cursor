# Cursor 规则说明

本目录存放 **Cursor IDE** 在本 workspace 中使用的规则文档（`.mdc`），用于约束 AI 助手与开发者的协作方式：从需求到设计、编码、测试与运维的优先级与格式要求。

## 目录结构

| 路径 | 说明 |
|:---|:---|
| `rules/` | 全局与各子工程的规则文件 |

规则文件为 Markdown Cursor（`.mdc`），通过 front matter 中的 `description`、`globs`、`alwaysApply` 控制适用范围。

### 若规则未出现在对话上下文中（Cursor 已更新配置）

1. **确认工作区根目录**：用 Cursor 打开的是本仓库根目录 `ai-company/`（而不是仅 `codiiy/` 等子文件夹），否则读不到根下的 `.cursor/rules/`。
2. **设置**：`Cursor Settings` → **Rules** → 确认 **Project Rules** 已开启；在 **Rules** 面板中应能看到各条规则及 “Always” 等标记。
3. **重载窗口**：命令面板执行 `Developer: Reload Window`。
4. **规则注入**：全局规则在 front matter 中同时配置了 `globs: ["**/*"]` 与 `alwaysApply: true`（规避部分 Cursor 版本对「仅 alwaysApply」不注入上下文的已知问题）。`codiiy` 细则使用 `globs: ["codiiy/**/*"]`。
5. **兜底**：仓库根目录另有 `.cursorrules`，内容与上述 Project Rules 对齐，供仍读取旧入口的客户端引用。

## `rules/` 中的主要文件

| 文件 | 作用概要 |
|:---|:---|
| `rules-workflow.mdc` | 端到端工作流：需求 → 设计/测试设计 → 实现与自动化测试 → 归档 |
| `rules-or.mdc` | 原始需求（`01-or`）文档结构与命名规范 |
| `rules-dr.mdc` | 开发设计（`02-dr`）文档结构与可追溯性 |
| `rules-test-design.mdc` | 测试设计及 91-qa 质量文档约定 |
| `rules-test.mdc` | 测试代码目录镜像与 E2E（Playwright）组织 |
| `rules-design-dir-agents.mdc` | 规划类目录须维护 `AGENTS.md` |
| `rules-develop-common.mdc` | 通用编码纪律：设计先行、变更顺序 |
| `external-projects-readonly.mdc` | 外部只读引用工程，禁止在仓库内改需求/实现 |
| `codiiy/rules-develop.mdc` | **codiiy** 子项目编码细则（Python、路径、组件调用等） |

新增子工程时，可在 `rules/<工程名>/` 下追加 `rules-develop.mdc` 等与全局规则配合使用。

## 与业务代码的关系

规则中提到的 `{工程}`（如 `codiiy`、`ls`）指 workspace 下的子项目根目录；文档树 `doc/01-or`、`02-dr` 等位于各子项目内，不由本目录替代，本目录只定义**如何写文档与写代码**的约束。
