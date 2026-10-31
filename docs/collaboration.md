# Mac Mouse Fix 项目协作流程

本文件是 Mac Mouse Fix 的详细协作契约。根目录 `AGENTS.md` 是入口；修改源码、规则、文档、测试或配置前必须先阅读本文件。本契约按 `github-repo-ops 2026.11.01.1` 实例化并随项目版本控制，不依赖全局 Skill 安装目录。

## 项目适配结果

| 内容 | 本项目约定 |
| --- | --- |
| 规则来源版本 | `github-repo-ops 2026.11.01.1` |
| 无凭据 remote | `origin`: `git@github.com:zhtordinary/mac-mouse-fix.git`；`upstream` 仅作上游参考 |
| 主线 | `personal-use`；不得改用 `master` 或覆盖个人版规则 |
| 主 checkout | Mac mini: `/Users/zibuyu/Projects/mac-mouse-fix`；MacBook Air: `/Volumes/19821669854/移动扩展盘/Projects/mac-mouse-fix` |
| 任务 worktree | 由 Git 登记的单写者任务树；当前 Agent 管理树使用 `/Users/zibuyu/Projects/worktrees/mac-mouse-fix/<任务名>`。以 `git worktree list --porcelain` 为准，不凭目录名判断归属 |
| 允许编辑 | 本任务 worktree；主 checkout 只用于按项目入口对齐已验证结果 |
| 定向检查 | 规则/文档/测试/配置改动：`python3 -B Tests/test_collaboration_contract.py`、`python3 -B scripts/test_ai_deliver.py`、`python3 scripts/verify-personal-use-build.py`（适用时） |
| 最终检查 | `git diff --check`、显式文件清单、`git status --porcelain=v1 --untracked-files=all`、worktree 登记及两棵树的根层扫描 |
| 交付入口 | 既有 `./scripts/ai-deliver.sh`；它只允许批准的主 checkout、`personal-use` 和明确的 `origin`，并具有双 Mac 对齐/运行时产物边界 |
| 规则/文档候选边界 | 规则、文档、测试和配置可在任务树本地提交；push、merge、land、publish、安装和重启仍是分别授权的后续阶段 |
| 构建/发布 | 运行时改动才按 `AGENTS.md` 的 Mac mini 构建和直接实体安装规则处理；规则/文档/测试/配置改动不触发 |
| 任务分支收尾 | 未合入、dirty、活跃引用或归属不明时保留任务 worktree；合入后才按本契约核对并安全收尾，不用 `branch -D` 或批量 prune |
| 证据 | 记录完整基线/候选 SHA、显式文件、命令退出码、根层候选和未验证阶段；不记录凭据、token、私钥或用户数据 |

## 接手、隔离与单写者

1. 在任务树内记录以下只读事实：

   ```bash
   pwd
   git rev-parse --show-toplevel
   git rev-parse --path-format=absolute --git-common-dir
   git rev-parse HEAD
   git branch --show-current
   git status --porcelain=v1 --untracked-files=all
   git worktree list --porcelain
   git remote -v
   ```

   任务从接手时记录的完整主线基线 SHA 开始；后续候选、验证和合入证明都使用新的完整 SHA，不使用短 SHA 代替身份。

2. 任务 worktree 是源码修改、测试和本地提交的唯一边界。不要在主 checkout、其他任务树或产品安装路径写入；不要用 `cd`、调用方 cwd 或路径 basename 冒充服务绑定。一个 worktree 只有一个写者，已有 WIP、会话、进程和锁归原所有者。

3. 根 `.gitignore` 保留 `/.worktrees/`，用于阻止把任务副本意外嵌套进 checkout。当前使用的外部 Agent 管理路径不因此自动迁移；创建、复用或移除 worktree 以 Git 登记、所有者和实际路径依赖为准。可用以下命令核对忽略规则：

   ```bash
   git check-ignore -v --no-index .worktrees/ignore-check
   ```

4. 根层扫描只发现候选，不判断垃圾、不删除对象、不递归：

   ```bash
   python3 scripts/scan-root-empty.py "/Users/zibuyu/Projects/mac-mouse-fix"
   python3 scripts/scan-root-empty.py "$PWD"
   ```

   接手、提交前和收尾后都要执行。完整 `candidates` 逐项判断；现有 `mac-mouse-fix-scripts` 空目录属于基线现场，未经确认保持不动。`errors` 非空或退出码非零即为阻塞。

5. 禁止为制造干净状态而 `reset --hard`、`stash`、覆盖他人文件、强删 worktree 或批量清理。遇到脏工作区、归属不明、活跃会话、路径引用或未知写入结果，保留精确现场并报告。

## 开发、验证与本地提交

1. 规则、文档、测试和配置改动不得改变产品运行时行为。此类范围不包含 `App/`、`Helper/`、`Shared/`、`releases/` 或安装脚本的行为性修改；不触发 Xcode 构建、签名、`/Applications` 安装或 Helper/App 重启。

2. 本项目已有 `scripts/ai-deliver.sh` 是双 Mac GitHub 交付入口，不是任意任务的本地提交替代品。它会校验 `personal-use`、固定 `origin`，并在正常使用时 push/同步；未获相应阶段授权时，任务 worktree 只使用 Git 原生命令完成本地候选提交，不调用会产生副作用的入口。

3. 提交前至少执行：

   ```bash
   python3 -B Tests/test_collaboration_contract.py
   python3 -B scripts/test_ai_deliver.py
   python3 scripts/verify-personal-use-build.py
   git diff --check
   git status --porcelain=v1 --untracked-files=all
   git diff --cached --name-status
   git worktree list --porcelain
   ```

   `verify-personal-use-build.py` 是源码个人版契约检查；即使任务没有产品代码变化，也可用于证明既有 `PERSONAL_USE` 规则未被规则/文档改动破坏。若环境缺少 Xcode，不因此构建产品；在规则/文档/测试/配置任务中只报告未执行的构建覆盖。

4. 显式 `git add` 任务文件后创建本地候选提交。提交成功不等于合入、双机对齐或发布成功；报告中分别列出 local commit、push、merge、alignment 和 publish 状态，只声明实际完成的阶段。

5. 若未来按项目授权交付，必须重新读取当前 `personal-use` 基线并按 `scripts/ai-deliver.sh` 的正常或 `--resume <完整SOURCE_SHA>` 流程执行。远端或另一 checkout 脏、分支错误、主线前进、对齐结果未知时，入口必须失败并保留现场；不得强推或重建源码提交。

## AOCI / 仓库治理绑定

### 当前接入结论

本次对仓库 HEAD 的只读审计没有发现项目内 AOCI 合同或正式资产：没有跟踪的 `aoci.txt`、`aoci.code.txt`、`aoci.meta.txt`、`.aoci/`、项目 Guide、项目 AOCI 配置或 task-bound 服务入口。主机上可能存在其他项目使用的 AOCI 可执行文件，但那不构成本项目的接入，也不提供本任务的绑定证明。

因此本项目当前 **AOCI 不适用/未接入**：项目不运行 `init`、`scan`、`maintain`、`update-entry`、`verify`、`check` 或 `mcp`，不创建伪 index、Baseline、Ledger、receipt、`.aoci/` 或其他正式治理资产，也不借用主 checkout/其他项目的服务。没有 AOCI 批次、候选身份或 Baseline 需要报告；这不是绕过治理，而是遵守“项目未接入则不伪造接入”的安全边界。

### 将来启用时的硬门槛

只有项目明确加入 Guide、scope/预算、正式资产范围和恢复入口后，才能启用 AOCI，并须把配置提交到本项目、而非依赖个人主目录。启用后：

1. 首次 Overview、Maintain、Update、Verify 或 Check 前，记录任务 worktree、Agent Run cwd、完整源码候选 SHA、主线基线 SHA 和 `git worktree list --porcelain`。
2. AOCI CLI 必须显式使用 `--repo "$TASK"`；若有 MCP/服务，服务报告的 `runtime_repository_root` 或固定候选身份必须与任务 worktree 精确一致。只用 `cd`、Git 状态或当前 session cwd 不能重绑服务。
3. CLI/服务无法绑定、返回主 checkout/其他任务、候选漂移或写入结果未知时，停止正式治理读写，保留 source-bound 现场；不创建替代资产、不手改 Baseline、不清 Ledger、不重放旧 receipt。
4. 按实时 Guide 分流 `authoring_required`、`observed_*`、`scope_change_required` 和 `blocked`。机器返回的 `path`、`source_sha256`、`candidate_id`、`code_batch_id` 和 domain/批次身份必须原样保留，不自行拼造或拆分。
5. 稳定源码候选上完成维护后，Verify/Check、正式资产提交和合入都绑定同一完整 SHA；若工具提供 `complete=true`，还必须确认没有 remaining、源码漂移、Scope/observe 债务或待恢复事务。AOCI 通过仍不替代项目测试、构建、发布和 worktree 收尾。

## 完成门槛、收尾与临时资源

任务只有在需求验收、最终检查、本项目授权的合入、约定 checkout 对齐及资源收尾都完成后，才能称为已交付。仅本地提交属于候选已保存，不能表述为已合入或已发布。

任务应登记并清理自己创建的项目外临时进程、浏览器配置、远端任务和全局状态；测试自带的临时目录由测试框架 teardown。会话 handoff 文件属于任务证据，不属于项目源码，不加入本地提交。任务未合入、当前 worktree 仍被使用或路径依赖未知时，按规则保留，不执行 worktree/分支删除。

收尾时回读：

```bash
git status --porcelain=v1 --untracked-files=all
git diff --check
git worktree list --porcelain
python3 scripts/scan-root-empty.py "/Users/zibuyu/Projects/mac-mouse-fix"
python3 scripts/scan-root-empty.py "$PWD"
```

对根层扫描的每个候选报告“已清理／合法保留／待确认”。本项目基线中的 `mac-mouse-fix-scripts` 空目录未获删除授权，保持并报告。只有在未来已合入、干净、无会话/进程路径依赖且确认分支 tip 已交付时，才可从主 checkout 使用 `git worktree remove <精确路径>` 和默认 `git branch -d <任务分支>`；禁止 `-D`、`prune` 或跟随链接扩大范围。
