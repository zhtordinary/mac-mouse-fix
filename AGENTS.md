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
   - 无论在 Mac mini 还是 MacBook Air 上，开发完成后统一使用：
     ```bash
     ./scripts/ai-deliver.sh --message '<type>: <describe change>' --files <changed-files>...
     ```
   - 源码先独立提交并推送 GitHub，再按变更路径执行交付：
     - 纯文档、规则或工作流脚本改动（`.md`, `scripts/*`, `docs/*`）：两端仅通过 GitHub fast-forward 对齐；跳过构建、产物提交、安装、签名和 App/Helper 重启。
     - 运行时改动：Mini 固定负责构建、实体安装及独立的 releases 产物提交；从 Air 发起时通过 SSH 调用 Mini 构建。产物经 GitHub 对齐后，在 Air 实体安装。
   - 正常交付和 `--resume` 使用相同的路径分类；续交付根据已发布源码提交判断，不重复生成源码 commit。
   - 对端同步前核对分支、remote、工作区干净及目标提交；离线、脏工作区或无法 fast-forward 时交付失败，保留现场并报告阻塞。
   - 修改交付流程后运行 `python3 scripts/test_ai_deliver.py`，用隔离 Git/SSH/构建夹具验证文档双向交付、续交付及运行时分支。

## 协作流程入口

修改源码、规则、文档、测试或配置前，必须先阅读 [项目协作流程](docs/collaboration.md)。该流程按 `github-repo-ops 2026.11.01.1` 实例化，详细说明任务 worktree、personal-use 分支、验证、交付和收尾边界。

当前仓库没有项目内 AOCI 资产、Guide、CLI 或 task-bound 服务；不得因为主机上存在其他项目的工具而创建 `.aoci/`、`aoci.txt` 等正式资产，或把当前 cwd 当成治理绑定证明。AOCI 的条件性使用和阻塞规则以 [项目协作流程](docs/collaboration.md) 为准。

## 安全与防劣化防护
   - **严禁覆盖个人版**：绝不执行 `brew upgrade mac-mouse-fix`，必须永久使用本地 `personal-use` 定制构建。
   - **严禁引入内核驱动劫持**：不使用 DriverKit / Karabiner 抓取鼠标，确保 Universal Control 跨屏鼠标漫游 100% 顺畅。
   - **源码与产物双 Commit**：源码修改与 releases app 产物必须拆分为两个独立 commit，严禁混合提交。
   - 发生中断时，使用 `./scripts/ai-deliver.sh --resume <source-sha>` 继续，绝不重复生成源码 commit。

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
