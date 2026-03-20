# Cursor 规则说明

本目录存放 **Cursor IDE** 在本 workspace 中使用的规则文档（`.mdc`），用于约束 AI 助手与开发者的协作方式：从需求到设计、编码、测试与运维的优先级与格式要求。

## 目录结构

| 路径 | 说明 |
|:---|:---|
| `rules/` | 全局与各子工程的规则文件 |

规则文件为 Markdown Cursor（`.mdc`），可通过 front matter 中的 `description`、`alwaysApply` 等字段控制适用范围。

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
