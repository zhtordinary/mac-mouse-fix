# 项目规则：Mac Mouse Fix (多 Mac 协同桌面应用)

## 核心边界与架构准则

1. **源码与产物由 GitHub 管理**：
   - 官方 private remote：`git@github.com:zhtordinary/mac-mouse-fix.git`
   - 主力开发分支：`personal-use`（永久无试用期、无限期自用版）
   - Mac mini 本地 checkout：`/Users/zibuyu/Projects/mac-mouse-fix`
   - MacBook Air 本地 checkout：`/Volumes/19821669854/移动扩展盘/Projects/mac-mouse-fix`
   - **Syncthing 绝对隔离**：两台 Mac 的 `Projects/_stignore.shared` 必须严格包含 `/mac-mouse-fix` 和 `/mac-mouse-fix/**`，严禁 Syncthing 隐式同步本目录，所有源码与产物一律通过 Git 传递。

2. **桌面应用产物与直接实体安装规范**：
   - 本项目统一管理桌面客户端：
     - `Mac Mouse Fix.app`：负责滚轮平滑滚动、中键手势，并原生内置 **“微信语音输入”** 动作（支持在中键连按/双击时以 ~200ms 极速唤醒微信输入法语音录入，天然消除拖拽误触与底层抢键冲突）。
     - （注：历史独立的 `WeTypeVoiceTrigger.app` 已彻底废弃并卸载，能力全面由 Mac Mouse Fix 接管）。
   - 编译产物统一存放在仓库内 `releases/Mac Mouse Fix.app`（在 Git 中单独 commit 跟踪）。
   - **安装方式（铁律）**：系统 `/Applications/*.app` 采用**直接实体拷贝模式（Direct Copy Install）**，杜绝软链接（Symlink），以确保 macOS 辅助功能 TCC 权限持久稳定，且跨卷 Universal Control 与登录项不丢失。

3. **双机对偶交付流程 (`./scripts/ai-deliver.sh`)**：
   - 源码交付必须从 Git 登记的独立任务 worktree 发起，任务 worktree 以当前 `origin/personal-use` 为唯一父基线；显式 `--files` 之外的修改、分支漂移、候选多父或远端并发变化都必须失败关闭。
   - 不因缺少远端 verifier 阻断本地开发：按项目契约核验基线后可在独立任务 worktree 编辑和做定向检查；这不授予提交或交付授权。
   - 当前没有可信的真实项目副作用 verifier，首次、恢复和内部交付入口均在 fetch、锁、hook、提交、对端、构建、安装或 push 前硬阻塞；不会保存源码候选。`--request-push-effects` 只是请求，任何旗标或伪造 HANDOFF 均不构成授权或平台证明。
   - 将来恢复交付须先核验真实平台状态及明确授权，提交前固定显式文件集合对应的 index tree，提交后核对 tree、单一父 SHA、分支和工作树；现有保护仅供未来审阅，不代表当前可执行交付。
   - `--with-app` 不构成构建、安装或 Helper 服务重启的一揽子授权；每项必须分别明确授权。当前 `setup-app.sh` 无条件拒绝，不执行文件或进程操作；恢复须独立可信地验证产物与目标身份、可恢复替换、权限及竞态，不能仅凭旗标放行。
   - `--resume SOURCE_SHA` 须先核验真实外部未决状态；不得从旧回执或同 SHA 推断授权。当前恢复同样阻塞。
   - 对端同步前核对分支、remote、工作区干净及固定目标提交；离线、脏工作区、无法 fast-forward 或结果未知时交付失败，保留现场并报告阻塞。
   - 修改交付流程后运行 `python3 scripts/test_ai_deliver.py`，用隔离 Git/SSH/build/install/hook 夹具验证真实入口在任何副作用前阻塞，以及隔离替身中的候选 tree/父 SHA 防漂移；另运行 `python3 -B Tests/test_setup_app_safety.py`、`python3 -B Tests/test_button_release_routing.py`、`python3 -B Tests/test_keyboard_event_safety.py` 和 `python3 -B Tests/test_personal_use_actions.py`。fixture 只证明本地控制流，不证明真实托管平台安全。

## 协作流程入口

修改源码、规则、文档、测试或配置前，必须先阅读 [项目协作流程](docs/collaboration.md)。该流程按 `github-repo-ops 2026.11.03.3` 实例化，详细说明任务 worktree、personal-use 分支、验证、交付和收尾边界。

当前仓库没有项目内 AOCI 资产、Guide、CLI 或 task-bound 服务；不得因为主机上存在其他项目的工具而创建 `.aoci/`、`aoci.txt` 等正式资产，或把当前 cwd 当成治理绑定证明。AOCI 的条件性使用和阻塞规则以 [项目协作流程](docs/collaboration.md) 为准。

## 安全与防劣化防护
   - **严禁覆盖个人版**：绝不执行 `brew upgrade mac-mouse-fix`，必须永久使用本地 `personal-use` 定制构建。
   - **严禁引入内核驱动劫持**：不使用 DriverKit / Karabiner 抓取鼠标，确保 Universal Control 跨屏鼠标漫游 100% 顺畅。
   - **源码与产物双 Commit**：源码修改与 releases app 产物必须拆分为两个独立 commit，严禁混合提交。
   - 发生中断时，只有真实项目守卫已核验同 SHA 外部未决状态后，才使用 `./scripts/ai-deliver.sh --request-push-effects --resume <完整 source-sha>` 继续；构建、安装及 Helper 服务重启必须分别明确授权并通过独立验证，绝不重复生成源码 commit；当前入口无条件阻塞。守卫缺失或结果未知时保留现场。

## 任务临时资源清理

- 创建时登记本任务临时文件、目录和进程的精确路径或身份、用途、归属依据及清理条件；覆盖项目内外、系统临时目录、本机状态目录、独立浏览器测试配置及已授权远端，位置不改变责任，也不扩大访问授权。
- 已确认属于本任务、用途结束且可丢弃的临时资源纳入正常收尾：不再需要时及时清理，完成前逐项核对。先核验当前身份、内容和无正在使用者，正常停止自有进程并确认退出，再按精确路径处理；不跟随链接扩大范围，工作树仍用 Git 原生命令。
- 用户数据、WIP、日常浏览器配置、已有依赖环境、共享缓存及其他任务资源保持原样；归属、用途或使用状态不明时保留并报告。禁止通配符批量删除、按名称/年龄/体积判废或全盘搜删。
- 正式回归测试、最小必要验收证据、发布回执及恢复材料按项目规则保留，临时试验脚本、重复截图和导出副本失去用途后清理。受阻或中止需保留的最小现场，写明原因、精确位置与后续清理条件。
- 清理后回读路径不存在、对应进程退出，分别报告“已清理／按规则保留／待确认”；工作树或 Git 已干净不代表外部临时资源已收尾。

## 提交前与交付后核验

- 接手时记录根层候选、Git 状态和 worktree 登记基线。提交/交付前，对主 checkout 执行 `python3 "$HOME/.agents/skills/github-repo-ops/scripts/scan-root-empty.py" "<本机主checkout绝对路径>"`；不同于主 checkout 的本任务工作树另扫根层。
- 扫描只发现根目录直接子项中的物理空目录和零字节普通文件，不递归、不读取文件内容、不跟随符号链接；非空目录只检查首条目。隐藏和 ignored 对象同样列出；发现阶段不运行 Git、构建或全仓哈希。
- 将完整 `candidates` 清单交给 AI 逐项判断用途、归属及是否误创建；不按名称、正则、命令名黑名单或是否新增过滤候选，也不凭名字或空状态删除。合法的零字节 `.gitkeep`、约定占位目录等说明用途后保留；存疑项保留并报告待确认信息。
- 仅处理 AI 确认且在本任务授权范围内的错误产物。操作前重新确认路径身份、类型、空状态及无有效引用；有并发写入或类型变化时停止。普通空目录只用 `rmdir`，零字节普通文件使用废纸篓或项目已有可恢复方式；工作树用 Git 原生命令。保护 WIP、用户数据和符号链接，不用强删、prune、覆盖或新增 ignore 掩盖问题。
- 清理后及交付脚本结束后重跑同一扫描，报告“已清理／合法保留／待确认”。扫描 `errors` 非空或非零退出时报告阻塞，不能把部分结果当完整检查；没有候选只表示这一层未发现目标空对象。
- 原有 Git 与交付门禁照常执行：`git status --porcelain=v1 --untracked-files=all`、`git diff --check`、暂存区/显式文件清单及 `git worktree list --porcelain`。有副作用的命令先核对 cwd、argv 和精确路径，失败后先回读实际状态；既有验证、合入及发布授权不变。
