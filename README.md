# Cursor 规则说明

本目录存放 **Cursor IDE** 在本 workspace 中使用的规则文档（`.mdc`），用于约束 AI 助手与开发者的协作方式：从需求到设计、编码、测试与运维的优先级与格式要求。

仓库根目录另有 `.cursorrules`（内容与 Project Rules 摘要对齐），供仍读取旧入口的客户端引用。全文以本目录 `rules/` 为准。

## 目录结构

| 路径 | 说明 |
|:---|:---|
| `rules/` | 全局与各子工程的规则文件（`.mdc`） |
| `tools/` | 可复用系统命令与辅助脚本；台账见 `tools/readme.md`（见 `rules-cursor-tools.mdc`） |
| `其他技巧.md` | 非强制的提示词/操作备忘（不注入对话上下文） |

规则文件为 Markdown Cursor（`.mdc`），通过 front matter 中的 `description`、`globs`、`alwaysApply` 控制适用范围。

### 若规则未出现在对话上下文中（Cursor 已更新配置）

1. **确认工作区根目录**：用 Cursor 打开的是本仓库根目录 `ai-company/`（而不是仅 `codiiy/` 等子文件夹），否则读不到根下的 `.cursor/rules/`。
2. **设置**：`Cursor Settings` → **Rules** → 确认 **Project Rules** 已开启；在 **Rules** 面板中应能看到各条规则及 “Always” 等标记。
3. **重载窗口**：命令面板执行 `Developer: Reload Window`。
4. **规则注入**：全局规则在 front matter 中同时配置了 `globs: ["**/*"]` 与 `alwaysApply: true`（规避部分 Cursor 版本对「仅 alwaysApply」不注入上下文的已知问题）。子工程细则用对应路径 glob（如 `codiiy/**/*`、`AutoCore/**`）。
5. **兜底**：仓库根目录 `.cursorrules` 与上述 Project Rules 对齐。

新增子工程时，可在 `rules/<工程名>/` 下追加 `rules-develop.mdc` 等与全局规则配合使用。

## `rules/` 中的文件

### 全局工作流与文档

适用于维护 `doc/01-or`～`99-ops` 标准目录树的子项目。

| 文件 | 作用概要 |
|:---|:---|
| `rules-workflow.mdc` | 端到端工作流：需求 → 设计/测试设计 → 实现 → 归档 |
| `rules-or.mdc` | 原始需求（`01-or`）文档结构与命名规范 |
| `rules-dr.mdc` | 开发设计（`02-dr`）文档结构与可追溯性 |
| `rules-test-design.mdc` | 测试设计及 91-qa 质量文档约定 |
| `rules-test.mdc` | 测试代码目录镜像与 E2E（Playwright）组织 |
| `rules-design-dir-agents.mdc` | 规划类目录须维护 `AGENTS.md` |
| `external-projects-readonly.mdc` | 外部只读引用工程，禁止在仓库内改需求/实现 |

### 全局编码

| 文件 | 作用概要 |
|:---|:---|
| `rules-develop-common.mdc` | 通用编码纪律：设计先行、变更顺序、调试权限 |
| `rules-cursor-tools.mdc` | 系统命令/辅助脚本沉淀到 `.cursor/tools`；先查台账再调用，禁止每次新建 |
| `python-demo-entry-no-cli.mdc` | Python demo 入口默认不用 CLI；参数放在 `__main__` |
| `rules-frontend-design.mdc` | 前端界面：高完成度、有辨识度；避免通用「AI 审美」（按 `*.vue` / `*.tsx` 等触发） |

### 子工程与路径规则

| 文件 | 作用概要 |
|:---|:---|
| `codiiy/rules-develop.mdc` | **codiiy**：Python、路径基准、组件调用等 |
| `AutoCore/rules-wait-for-execute.mdc` | **AutoCore** 默认只梳理；须明确「执行」指令后才写文档/代码 |
| `AutoCore/rules-supervisor-locked.mdc` | **AutoCore** `supervisor/` 锁死；自更新不得改外层 |
| `AutoCore/rules-llm-plan.mdc` | **AutoCore** 差遣由大模型规划；禁止关键词跳过模型直接执行 |
| `AutoCore/rules-orchestrator-decoupled.mdc` | **AutoCore** 编排器不得写通道/工具特例剧本 |
| `insect/rules-train-ba.mdc` | **insect/train_ba**：对外开放训练代码，最小可见、独立可运行 |
| `insect/rules-no-redundant-edits.mdc` | **insect**：大文件改动禁止冗余膨胀，复用已有函数 |
| `数学问题/rules-structure.mdc` | 每个数学问题拆成 `概念/`、`已有证明/`、`我的证明/` |
| `识别问题/rules-structure.mdc` | 每个识别问题一个目录，其下拆成 `问题/`、`讨论/`、`结论/` |
| `xiaohongshu-copy-one-file.mdc` | 介绍案例/小红书宣传文案一文一文件，禁止往同一 md 堆叠 |

自动化测试代码默认不强制同步编写；仅在用户明确要求（或任务指定交付包含测试）时再补充。

## 与业务代码的关系

规则中提到的 `{工程}`（如 `codiiy`、`ls`、`AutoCore`、`insect`）指 workspace 下的子项目根目录；文档树 `doc/01-or`、`02-dr` 等位于各子项目内，不由本目录替代，本目录只定义**如何写文档与写代码**的约束。
