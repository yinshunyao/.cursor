# `.cursor/tools` 工具台账

本目录存放 **可复用的系统命令包装与辅助脚本**（非业务产品代码）。  
规则见：`.cursor/rules/rules-cursor-tools.mdc`。

**硬性规定**：本目录下脚本或子目录有任何变动（新增、修改、删除、重命名），必须在同一回合更新本文件。只改工具、不改本台账，视为未完成。

## 使用约定

1. **先查本文件**再动手：已有工具 → 直接调用 / 原地小改，并在同一回合更新本表。
2. **没有合适工具** → 按分类新建到对应子目录，并在本文件对应分类下登记。
3. **禁止**每次对话新建一次性脚本后丢弃；同类能力应沉淀为工具。
4. 业务实现仍写在各子工程；本目录只收「助手侧可复用工具」。
5. **不必登记**：单次 `ls`/`cat`/`git status` 探查；应登记：会重复用的流程、新建的辅助脚本。
6. **按工程提炼**：只服务某一个工程、且会反复用的命令/脚本，放到 `<工程名>/`（与 workspace 子目录同名）。跨工程通用的仍按下面的类型目录放。
7. **脱敏**：源码、注释、本台账只写通用说明（用途、输入输出形态、依赖、调用方式）。禁止写入密钥、口令、令牌、内网地址、账号、客户名、合同报价、未公开数据路径、样本清单、训练机绝对路径。具体值调用时再用参数或环境变量传入；台账用 `<数据目录>` 这类占位符。

## 目录分类

| 分类目录 | 用途 |
|:---|:---|
| `shell/` | 跨工程可复用 shell / 一键命令包装 |
| `python/` | 跨工程可复用 Python 辅助脚本 |
| `media/` | 跨工程音视频、图片等处理 |
| `git/` | 跨工程仓库检查、批量 git 辅助 |
| `misc/` | 暂无法归类 |
| `<工程名>/` | 只服务该工程的常用工具（如 `scanly/`、`codiiy/`） |

新建类型分类时：先增上表一行，再建目录。新建工程目录时：目录名与工程根目录一致，并在下方按工程分节登记。

---

## shell/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `shell/deploy-dify-locations.sh` | 同步 Dify 的 `dify-locations.inc` 到远端 Nginx 并 `reload` | `HIPP_DEPLOY_HOST=root@<host> HIPP_DEPLOY_SSH_PASS=<pass> bash .cursor/tools/shell/deploy-dify-locations.sh`（可选 `HIPP_DEPLOY_LOCAL_INC` / `HIPP_DEPLOY_REMOTE_INC`） | 默认本地 `study/配置信息/生产-yin/dify/dify-locations.inc` → `/etc/nginx/conf.d/dify-locations.inc`；须含 `location /vs/`；密码走 expect，勿写入脚本 |
| `shell/disable-systemd-osc-context.sh` | 永久关掉 Ubuntu systemd OSC 3008 刷屏（`dpkg-divert` + stub） | 本机：`sudo bash .cursor/tools/shell/disable-systemd-osc-context.sh`；远程：`OSC_SSH=user@host OSC_SSH_PORT=<port> OSC_SSH_PASS=<pass> bash .cursor/tools/shell/disable-systemd-osc-context.sh` | 仅 `mv .disabled` 会在包装还原后复发；新版脚本常不读 `SYSTEMD_OSC_CONTEXT`；密码走 env，勿写入脚本 |

## python/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `python/zhaokaopu-business-cover.py` | 「怎么找到靠谱的软件开发」专栏商务密排封面（小红书3:4 + 头条16:9） | `/Users/shunyaoyin/miniconda310/miniconda3/bin/python .cursor/tools/python/zhaokaopu-business-cover.py`（cwd 任意；默认渲文案9～19，改 `__main__` 的 `ONLY`） | 依赖 Pillow + macOS 黑体；`render_article5`～`8` 仍在；9～19 走 `ARTICLE_PACKS`；输出到对应 `文案N_*/小红书|头条/` |
| `python/shibie-jiedan-cover.py` | 「图像识别智能体Web应用接单」配图（小红书深色3:4 + 微头条浅色16:9） | `/Users/shunyaoyin/miniconda310/miniconda3/bin/python .cursor/tools/python/shibie-jiedan-cover.py`（cwd 任意；改 `__main__` / 增 `render_YYYYMMDD`） | 依赖 Pillow + macOS 黑体；禁止署名；已有 `render_20260930`、`render_20261009`、`render_20261010`；`__main__` 当前跑 20261010 |
| `python/resume-md-to-docx.py` | 求职简历 Markdown 转 Word（沿用 202609 版式） | `/Users/shunyaoyin/miniconda310/miniconda3/bin/python .cursor/tools/python/resume-md-to-docx.py`（路径写在 `__main__`） | 依赖 python-docx；当前 `__main__` 指向 `法人相关信息/个人简历-项目经理-202610.md` → 同名 docx |
| `python/md-to-docx.py` | 通用 Markdown 转 Word（标题、列表、表格、加粗） | `/Users/shunyaoyin/miniconda310/miniconda3/bin/python .cursor/tools/python/md-to-docx.py`（改 `__main__` 的 `SRC`） | 依赖 python-docx；当前 `SRC` 为停车结果识别算法报价方案 |
| `python/labelstudio-to-voc.py` | Label Studio 矩形框导出转 Pascal VOC（LabelImg） | `LS_INPUT_DIR=<导出目录> LS_OUTPUT_DIR=<输出目录> python3 .cursor/tools/python/labelstudio-to-voc.py`（cwd 为仓库根；可选 `LS_CATEGORIES=<类别json>`） | 仅标准库；默认递归子目录，复制图像到 `JPEGImages/`，标注写入 `Annotations/`，类别写入 `predefined_classes.txt`；无框样本仍写出空 XML |
| `python/coco-cvat-to-voc.py` | CVAT 导出的 COCO 检测标注转 Pascal VOC（LabelImg） | `COCO_INPUT=<coco.json或数据集目录> VOC_OUTPUT_DIR=<输出目录> python3 .cursor/tools/python/coco-cvat-to-voc.py`（cwd 任意；可选 `COCO_IMAGE_DIR` / `COCO_COPY_IMAGES=0` / `COCO_MERGE_SPLITS=0` / `COCO_SKIP_MISSING=0` / `COCO_WRITE_EMPTY=0`） | 仅标准库；COCO `bbox=[x,y,w,h]`→VOC；默认合并多份 JSON 到同一 `Annotations/`+`JPEGImages/`，并写 `predefined_classes.txt`；CVAT `occluded`→truncated，有 `rotation`/`iscrowd`→difficult；无 env 时可改 `__main__` 变量 |
| `python/merge-voc-dirs.py` | 合并两个 Pascal VOC 目录，按图片 MD5 去重 | `VOC_SOURCE_A=<目录A> VOC_SOURCE_B=<目录B> VOC_OUTPUT_DIR=<新目录> python3 .cursor/tools/python/merge-voc-dirs.py`（cwd 任意） | 仅标准库；先保留 A 再写入 B，内容相同的图片不重复复制；重复清单写到目标目录 `duplicate_files.csv`；合并 `predefined_classes.txt`；目标目录须为空或不存在 |
| `python/stat-voc-annotations.py` | 统计 Pascal VOC 标注框类型与尺寸分布（单/多目录） | `VOC_DIRS=<目录1>,<目录2> python3 .cursor/tools/python/stat-voc-annotations.py`（或 `VOC_DIR=<单目录>`；可选 `VOC_CATEGORIES` / `VOC_STATS_OUTPUT` / `VOC_RECURSIVE=0` / `VOC_USE_DIAGONAL=0`） | 仅标准库；移植自 scanly `stat_annotation.py` 的 VOC 路径；自动识别 `Annotations`/`JPEGImages`；多目录聚合；报告打印并默认写到首目录 `annotation_stats_voc.txt`；无 env 时可改 `__main__` 的 `SAMPLE_DIRS` |
| `python/gen-wechat-pay-api-v3-key.py` | 生成微信支付 APIv3 密钥（32 位字母数字） | `python3 .cursor/tools/python/gen-wechat-pay-api-v3-key.py`（cwd 任意；改 `__main__` 的 `LENGTH`/`COUNT`） | 仅标准库 `secrets`；字符集 `A-Za-z0-9`；输出到终端，自行抄入商户平台与受控 env，勿提交仓库 |

## media/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `media/photo-remove-watermark-deai.py` | 去掉右下角半透明 AI 水印，并加轻度实拍感（曝光不均/颗粒/暗角） | 改 `__main__` 的 `INPUT_DIR`/`FILES` 后：`python .cursor/tools/media/photo-remove-watermark-deai.py` | 依赖 OpenCV+numpy；输出 `<目录>/处理后/*_去水印实拍感.png` 与 `*_仅去水印.png`；不改场景内容，强「去 AI 感」需另用生成重制 |
| `media/redact-image-words.py` | OCR 定位并涂盖图中品牌/敏感词，可选重绘顶栏标题 | `/Users/shunyaoyin/miniconda310/miniconda3/bin/python .cursor/tools/media/redact-image-words.py --input <图> --output <图> --word Veo --title-bar 140 --title-text <脱敏标题>` | 依赖 Pillow + 本机 `tesseract`（eng）；可重复 `--word`；`--crop l,t,r,b`；不写具体客户进脚本 |

## git/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `git/cursor-repo-status.sh` | 查看 `.cursor` 独立仓库 remote/分支/近期提交/脏文件 | `bash .cursor/tools/git/cursor-repo-status.sh`（cwd 任意） | 仓库根为 `.cursor/` |
| `git/cursor-repo-push.sh` | 将 `.cursor` 当前分支推到 `origin` | `bash .cursor/tools/git/cursor-repo-push.sh` | 需已有本地 commit；会访问网络 |

## misc/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| （暂无） | — | — | — |

## hipp-https/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `hipp-https/deploy-console.sh` | 同步证书控制台代码到远端并重启 supervisor 程序 | `HIPP_DEPLOY_HOST=root@<host> HIPP_DEPLOY_REMOTE=<远端目录> bash .cursor/tools/hipp-https/deploy-console.sh`（cwd 任意；可选 `HIPP_DEPLOY_ENV`、`HIPP_DEPLOY_SSH_PASS`、`HIPP_DEPLOY_BUILD=1`） | 须先有正确 `web/dist`（生产为 `VITE_BASE=/cert/`；根路径 `/assets/` 会拒绝部署）；`HIPP_DEPLOY_BUILD=1` 先本地 build；排除 `.env`/`.venv`/`var`/`node_modules`；无密钥时可设 `HIPP_DEPLOY_SSH_PASS`（走 expect，勿写入脚本） |

## hipp-manager/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `hipp-manager/deploy.sh` | 同步 hipp-manager、可选装 nginx/supervisor 片段并重启 | `HIPP_DEPLOY_HOST=root@<host> HIPP_DEPLOY_REMOTE=<远端目录> bash .cursor/tools/hipp-manager/deploy.sh`（可选 `HIPP_DEPLOY_ENV`、`HIPP_DEPLOY_BUILD=1`、`HIPP_DEPLOY_NGINX_INC`、`HIPP_DEPLOY_SUPERVISOR_PROG`、`HIPP_DEPLOY_SSH_PASS`） | 须有 `web/dist` 且资源为 `/mgr/assets/`；排除 `.env`/`.venv`/`data`/`certs`（支付密钥勿被 `--delete` 清掉）；密码用 expect 时远程收尾走临时脚本，勿把 `[[` 直接塞进 spawn 命令行 |
| （工程内）`hipp-manager` → `python -m manager.import_legacy` | 按手机号从 `hipp` + `voicefix` 合并导入 manager 用户/余额 | 远端：`cd /data/hipp-manager && PYTHONPATH=server .venv/bin/python -m manager.import_legacy` | 须已配置 MySQL `DATABASE_URL`；可选 `LEGACY_HIPP_URL` / `LEGACY_VOICE_URL` |

## hipp-or/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `hipp-or/deploy-api.sh` | 同步 hipp-api 到远端并重启 `or-api` | `HIPP_DEPLOY_HOST=root@<host> HIPP_DEPLOY_REMOTE=/data/or/hipp-api bash .cursor/tools/hipp-or/deploy-api.sh`（可选 `HIPP_DEPLOY_ENV`、`HIPP_DEPLOY_SSH_PASS`、`HIPP_DEPLOY_MIGRATE=1`） | 排除 `.env`/`.venv`/`static`；不碰 hipp.ink 的 `/home/hipp-or`；若 `HIPP_DEPLOY_ENV` 含 `MANAGER_*` 则拒绝（防误盖 manager.env）；`MIGRATE=1` 远端 `alembic … upgrade head`（不用 `main.py migrate`，防 autogenerate） |
| `hipp-or/deploy-admin.sh` | 同步 hipp-admin SPA `dist/` 到远端 | `HIPP_DEPLOY_HOST=root@<host> HIPP_DEPLOY_REMOTE=/data/or/hipp-admin bash .cursor/tools/hipp-or/deploy-admin.sh`（可选 `HIPP_DEPLOY_BUILD=1`、`HIPP_DEPLOY_SSH_PASS`） | 须 `dist` 含 `/or/manager/assets/`；`HIPP_DEPLOY_BUILD=1` 需本地 `.env.or`（`VITE_BASE_PATH=/or/manager/`）；只同步静态，不重启 API |
| `hipp-or/deploy-web.sh` | 同步 hipp-web SPA `dist/` 到远端 | `HIPP_DEPLOY_HOST=root@<host> HIPP_DEPLOY_REMOTE=/data/or/hipp-web bash .cursor/tools/hipp-or/deploy-web.sh`（可选 `HIPP_DEPLOY_BUILD=1`、`HIPP_DEPLOY_SSH_PASS`） | 须 `dist` 含 `/or/assets/`；`HIPP_DEPLOY_BUILD=1` 使用 `VITE_BASE_PATH=/or/` `VITE_API_BASE=/or/api` |

## VoiceFix/

| 路径 | 用途 | 调用 | 备注 |
|:---|:---|:---|:---|
| `VoiceFix/deploy-yin-gateway.sh` | 同步 VoiceFix 网关（server + web SPA），装 nginx/supervisor，migrate；**不起 Worker** | `HIPP_DEPLOY_HOST=root@<host> HIPP_DEPLOY_SSH_PASS=<pass> HIPP_DEPLOY_ENV=<vf.env> HIPP_DEPLOY_NGINX_INC=<vf-locations.inc> HIPP_DEPLOY_SUPERVISOR_PROG=<Svf-api> HIPP_DEPLOY_SEED=1 bash .cursor/tools/VoiceFix/deploy-yin-gateway.sh`（可选 `HIPP_DEPLOY_BUILD=1`） | 须 `web/dist` 含 `/vf/assets/`；远程已有 `.env` 不覆盖；密码走 expect；`vf-locations.inc` 只写入站点 server conf，禁止 include 进 `nginx.conf`（http 级会 location 报错） |
