# Cursor 规则说明

本目录存放 **Cursor IDE** 在本 workspace 中使用的规则文档（`.mdc`），以及可复用助手工具（`tools/`）。  
索引同步规则见 `rules/rules-cursor-readme-sync.mdc`：**改 `rules/` 或 `tools/` 结构时须同回合更新本文**。

仓库根目录另有 `.cursorrules`（内容与 Project Rules 摘要对齐），供仍读取旧入口的客户端引用。全文以本目录 `rules/` 为准。

## 目录结构

| 路径 | 说明 |
|:---|:---|
| `rules/` | 全局与各子工程的规则文件（`.mdc`） |
| `tools/` | 可复用系统命令与辅助脚本；跨工程按类型，单工程按工程名；**台账**见 `tools/readme.md`（见 `rules-cursor-tools.mdc`） |
| `其他技巧.md` | 非强制的提示词/操作备忘（不注入对话上下文） |

规则文件为 Markdown Cursor（`.mdc`），通过 front matter 中的 `description`、`globs`、`alwaysApply` 控制适用范围。

### 若规则未出现在对话上下文中（Cursor 已更新配置）

1. **确认工作区根目录**：用 Cursor 打开的是本仓库根目录 `ai-company/`（而不是仅 `codiiy/` 等子文件夹），否则读不到根下的 `.cursor/rules/`。
2. **设置**：`Cursor Settings` → **Rules** → 确认 **Project Rules** 已开启；在 **Rules** 面板中应能看到各条规则及 “Always” 等标记。
3. **重载窗口**：命令面板执行 `Developer: Reload Window`（若无此命令：`Cmd+Q` 完全退出后重开）。
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
| `archive-dirs-skip.mdc` | `mybak/`、`other3rd/` 为归档目录；无特别指令时不检索、不改动 |

### 全局编码与索引

| 文件 | 作用概要 |
|:---|:---|
| `rules-develop-common.mdc` | 通用编码纪律：设计先行、变更顺序、调试权限 |
| `rules-cursor-tools.mdc` | 系统命令/辅助脚本沉淀到 `.cursor/tools`（跨工程按类型，单工程按工程名）；先查台账再调用；工具任何变动必须同回合更新 `tools/readme.md`；工具内不得写入项目敏感信息 |
| `rules-cursor-readme-sync.mdc` | `.cursor/README.md` / `.cursorrules` 须与 `rules/`、`tools/` 同回合同步 |
| `rules-config-handbook-stepbystep.mdc` | 配置/申请类帮助手册须 step-by-step；每步含在哪(URL)、准备、完成、保存 |
| `python-demo-entry-no-cli.mdc` | Python demo 入口默认不用 CLI；参数放在 `__main__` |
| `rules-frontend-design.mdc` | 前端界面：高完成度、有辨识度；内容少的表单/充值勿横向撑满；支付二维码须弹窗展示；用户端清理常识性/设计思路类提示；紧凑处用图标加悬停提示代替长按钮文字；小图标按钮成组、间距让出标题；避免通用「AI 审美」（按 `*.vue` / `*.tsx` 等触发） |
| `rules-hipp-product-codes.mdc` | hipp 产品码仅 `mgr`/`or`/`vf`/`cert`；管理后台统一 `/{product}/manager/`；资金须 `product`+`biz_type`；资金运营在 `/mgr/manager/`，业务审批留各产品 |
| `rules-api-error-codes.mdc` | 业务失败须稳定 `code`+`message`；前端按码分支处理；禁止只靠文案关键词猜原因 |
| `rules-i18n-enum-labels.mdc` | 中文界面枚举字段须映射中文展示，禁止直接露 `bound`/`manual` 等英文码 |
| `rules-plan-archive.mdc` | 实施方案/Plan 须归档到所属产品 `doc/`（建议 `02-dr`），禁止只留在 `.cursor/plans/` 或聊天 |

### 子工程与路径规则

| 文件 | 作用概要 |
|:---|:---|
| `codiiy/rules-develop.mdc` | **codiiy**：Python、路径基准、组件调用等 |
| `AutoCore/rules-wait-for-execute.mdc` | **AutoCore** 默认只梳理；须明确「执行」指令后才写文档/代码 |
| `AutoCore/rules-supervisor-locked.mdc` | **AutoCore** `supervisor/` 锁死；自更新不得改外层 |
| `AutoCore/rules-llm-plan.mdc` | **AutoCore** 差遣由大模型规划；禁止关键词跳过模型直接执行 |
| `AutoCore/rules-orchestrator-decoupled.mdc` | **AutoCore** 编排器不得写通道/工具特例剧本 |
| `insect/rules-train-ba.mdc` | **insect/train_ba**：对外开放训练代码，最小可见、独立可运行 |
| `FgBgAug/rules-preprocess-version.mdc` | **FgBgAug**：预处理 `DATA_PREPROCESS_VERSION`；改旋钮须 bump，版本失配自动重建 dump/split |
| `insect/rules-no-redundant-edits.mdc` | **insect**：大文件改动禁止冗余膨胀，复用已有函数 |
| `insect/rules-cls-3131-test-only.mdc` | **insect**：分类 3.13.1 仅测试参考，禁止推荐上场/实战 |
| `数学问题/rules-structure.mdc` | 每个数学问题拆成 `概念/`、`已有证明/`、`我的证明/` |
| `识别问题/rules-structure.mdc` | 每个识别问题一个目录，其下拆成 `问题/`、`讨论/`、`结论/`；`基础知识/` 不套三层 |
| `识别问题/rules-illustrated-knowledge.mdc` | 原理性基础知识须图文并茂；结构图只用文内 mermaid，禁止独立 SVG（写入易损坏、预览常空白） |
| `识别问题/rules-discuss-writeback.mdc` | 讨论中澄清的术语/机制须回写对应文档，禁止只留在聊天 |
| `识别问题/rules-fgbg-aug-experiment-docs-only.mdc` | 前景背景解耦选题下 `实验/` 只留思路说明，禁止写代码 |
| `音乐歌词/rules-structure.mdc` | 灵感与歌词分层；素材转为简洁、朗朗上口的歌词 |
| `写作随笔/rules-yunchili.mdc` | **云池里**：先读设定约束再动笔；虚构的地名、时间和人物不必与现实对齐 |
| `写作随笔/rules-yunchili-interview.mdc` | **云池里访谈**：原话先存 `素材/`，再回写世界观、人物和大纲 |
| `项目管理/rules-quant-crypto.mdc` | 50U 小仓炒币否决为商业项目；结论写入 `study/项目管理/` |
| `xiaohongshu-copy-one-file.mdc` | 介绍案例宣传文案一文一文件；**统一 `文案N_YYYYMMDD_` 篇序**；**小红书长文只出文字、平台模板出图**；标签无小标题；**标题选型方法**（冲突→选族→填槽） |
| `介绍案例/rules-shishi-discussion.mdc` | **时事讨论**：一篇一个目录；原因说透目的；配图文字要讲清谁做了什么；改文章或配图须全文核对并同步；个人首评要写作者认为这件事说明什么；小红书正文不超过 1000 字；头条文章正文不少于 350 字 |
| `介绍案例/rules-jiedan-baseline.mdc` | **图像识别接单线**：新增文案对齐优势和目标客户；广告贴配图直白呈现客户和优势；量级数字不进广告正文 |
| `介绍案例/rules-xuqiu-fenxi.mdc` | **需求分析宣传线**：引流有软件需求的人；入口免费评估；案例/判断写法；禁欢迎咨询硬广；短笔记可同回合出图；**长文只出文字**；未指定行为思路时短笔记默认精简口语 |

## `tools/` 说明

- **台账唯一来源**：`tools/readme.md`（跨工程按 `shell/` / `python/` / `media/` / `git/` / `misc/`；单工程按工程名目录）
- **复用纪律**：`rules/rules-cursor-tools.mdc`（工具任何变动必须同回合更新 `tools/readme.md`；代码与备注只写通用信息，不写密钥、客户、未公开路径等敏感内容）
- 本 README **不**重复罗列每个脚本；分类增减时须同步改本页「目录结构」表

自动化测试代码默认不强制同步编写；仅在用户明确要求（或任务指定交付包含测试）时再补充。

## 与业务代码的关系

规则中提到的 `{工程}`（如 `codiiy`、`ls`、`AutoCore`、`insect`）指 workspace 下的子项目根目录；文档树 `doc/01-or`、`02-dr` 等位于各子项目内，不由本目录替代，本目录只定义**如何写文档与写代码**的约束。
