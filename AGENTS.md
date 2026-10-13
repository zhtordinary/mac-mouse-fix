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
   - 脚本自动识别当前设备：
     - 若在 Mini 发起：本地提交源码 → Mini 本地构建/更新 releases → 直接复制到 Mini `/Applications/` → push GitHub → SSH 触发 Air fast-forward pull 并自动安装至 Air `/Applications/`。
     - 若在 Air 发起：本地提交源码 → push GitHub → SSH 触发 Mini 远程构建产物并 push → Air 本地 fast-forward pull 并自动安装。
   - 纯文档、规则或脚本改动（`.md`, `scripts/*`）自动跳过构建。

4. **安全与防劣化防护**：
   - **严禁覆盖个人版**：绝不执行 `brew upgrade mac-mouse-fix`，必须永久使用本地 `personal-use` 定制构建。
   - **严禁引入内核驱动劫持**：不使用 DriverKit / Karabiner 抓取鼠标，确保 Universal Control 跨屏鼠标漫游 100% 顺畅。
   - **源码与产物双 Commit**：源码修改与 releases app 产物必须拆分为两个独立 commit，严禁混合提交。
   - 发生中断时，使用 `./scripts/ai-deliver.sh --resume <source-sha>` 继续，绝不重复生成源码 commit。
