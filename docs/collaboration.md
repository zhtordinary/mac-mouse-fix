# Mac Mouse Fix 项目协作流程

本文件是 Mac Mouse Fix 的详细协作契约。根目录 `AGENTS.md` 是入口；修改源码、规则、文档、测试或配置前必须先阅读本文件。本契约按 `github-repo-ops 2026.11.03.3` 实例化，本地开发边界参考 `2026.11.05.2`（`a24a0e07eb75faafac0f824091e705e2aab05bc9`）修订，最新规范对齐 `2026.11.06.1`；项目文件随版本控制，日常不依赖全局 Skill 安装目录。

## 项目适配结果

| 内容 | 本项目约定 |
| --- | --- |
| 规则来源版本 | `github-repo-ops 2026.11.03.3` |
| 无凭据 remote | `origin`: `git@github.com:zhtordinary/mac-mouse-fix.git`；`upstream` 仅作上游参考 |
| 主线 | `personal-use`；不得改用 `master` 或覆盖个人版规则 |
| 主 checkout | Mac mini: `/Users/zibuyu/Projects/mac-mouse-fix`；MacBook Air: `/Volumes/19821669854/移动扩展盘/Projects/mac-mouse-fix` |
| 任务 worktree | 由 Git 登记的单写者任务树；交付入口必须从该树发起固定源码候选。以 `git worktree list --porcelain` 和共同 Git 目录为准，不凭目录名判断归属 |
| 允许编辑 | 本任务 worktree；主 checkout 仅在已授权的 Git 对齐或显式 App 阶段由交付入口使用，日常源码修改不写入主 checkout |
| 定向检查 | 规则/文档/测试/配置改动：`python3 -B Tests/test_collaboration_contract.py`、`python3 -B scripts/test_ai_deliver.py`、`python3 -B Tests/test_personal_use_actions.py`、`python3 -B Tests/test_button_release_routing.py`、`python3 -B Tests/test_setup_app_safety.py`、`python3 -B Tests/test_keyboard_event_safety.py`、`python3 scripts/verify-personal-use-build.py`（适用时） |
| 最终检查 | `git diff --check`、显式文件清单、`git status --porcelain=v1 --untracked-files=all`、worktree 登记及两棵树的根层扫描 |
| 交付入口 | `./scripts/ai-deliver.sh` 从独立任务 worktree 发起；固定 `origin`、`personal-use`、单父 SOURCE_SHA 和两端 fast-forward 边界。普通 push 可能触发外部自动操作，当前无真实项目副作用守卫，所有交付入口在副作用前阻塞 |
| 规则/文档候选边界 | 当前入口不执行本地提交；push、merge、land、publish、安装和重启仍是分别授权的后续阶段 |
| 构建/发布 | 构建、安装和 Helper 服务重启须分别明确授权；`--with-app` 不能一揽子授权。当前入口及安装均硬阻塞 |
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

1. 规则、文档、测试和配置改动不得改变产品运行时行为；运行时源码改动必须单独验证。缺少远端 verifier 不阻断已登记任务树中的编辑和定向检查；已核验的本地 remote-tracking SHA 只作为开发基线，不是远端最新状态证明。所有交付入口当前在任何 fetch、hook 或提交前硬阻塞，不保存候选；不得手动提交绕过现行门禁。本地检查不授予两端对齐、Xcode 构建、签名、`/Applications` 安装或 Helper/App 重启的权限。

2. `scripts/ai-deliver.sh` 的首次、恢复和内部入口当前均在副作用前硬阻塞，不能仅凭旗标或 HANDOFF 放行。未来实现须经真实平台 verifier 和明确授权，并保留显式文件集合 index tree、单一父 SHA、分支及工作树核验；commit hook 插入额外文件或改写选中文件须阻塞。构建、安装和 Helper 服务重启须各自明确授权，`--with-app` 不是一揽子授权。

3. 提交前至少执行：

   ```bash
   python3 -B Tests/test_collaboration_contract.py
   python3 -B scripts/test_ai_deliver.py
   python3 -B Tests/test_personal_use_actions.py
   python3 -B Tests/test_button_release_routing.py
   python3 -B Tests/test_setup_app_safety.py
   python3 -B Tests/test_keyboard_event_safety.py
   python3 scripts/verify-personal-use-build.py
   git diff --check
   git status --porcelain=v1 --untracked-files=all
   git diff --cached --name-status
   git worktree list --porcelain
   ```

   `verify-personal-use-build.py` 是源码个人版契约检查；即使任务没有产品代码变化，也可用于证明既有 `PERSONAL_USE` 规则未被规则/文档改动破坏。若环境缺少 Xcode，不因此构建产品；在规则/文档/测试/配置任务中只报告未执行的构建覆盖。

4. 仅在副作用已独立核验并明确授权后，才可显式 `git add` 任务文件并创建本地候选提交；当前缺少 verifier，禁止以手动提交绕过交付门禁。提交成功不等于合入、双机对齐或发布成功；报告中分别列出 local commit、push、merge、alignment 和 publish 状态，只声明实际完成的阶段。

5. 若按项目授权交付，必须重新读取当前 `personal-use` 基线并从独立任务 worktree 执行。普通 push 前必须有真实项目副作用守卫及明确 `--request-push-effects`；同 SHA 恢复先核验真实外部未决状态，不能凭旧回执或 Git 接受状态重放。构建、安装和 Helper 服务重启还须分别明确授权及独立验证。当前守卫缺失、外部状态未知、远端或另一 checkout 脏、分支错误或主线前进时，入口必须失败并保留现场；不得强推或重建源码提交。

## Git push 外部副作用与恢复

普通 Git push 不是纯本地 Git 操作：它可能触发仓库/组织 Actions、webhook、Git App、托管平台构建或外部发布。项目必须由真实、当前、可核验的项目副作用守卫检查目标 remote/ref、完整候选与基线、触发配置、明确授权、真实拥有者队列/执行及同 SHA 未决状态；本机锁、分支名、无本地 App 调用、静态 workflow 匹配和通用 fixture 都不能证明这些条件。

当前项目没有已核验的真实副作用守卫或平台实时状态接口。因此 `scripts/ai-deliver.sh` 首次、恢复和内部入口均在 fetch、锁、hook、提交、SSH、构建、安装和 push 前阻塞，不保存 commit；`--request-push-effects` 和伪造 HANDOFF 均不能授权。候选 tree/父 SHA 门禁的隔离替身回归不是平台安全证据。

`--resume` 对已接受的同 SHA 也必须先核验真实外部未决状态。旧回执、Git remote 已包含 SHA、同一分支或本地测试通过都不能代替核验；状态未知或未决时保持阻塞，不重放 push、发布或完成入口。隔离 fixture 只验证入口的失败关闭和参数分流，不是平台安全或实时触发状态证据。

## App 安装与设备副作用

`setup-app.sh` 当前在任何文件或进程操作前无条件拒绝，尚未实现 bundle、复制、签名或替换校验及安装。恢复前必须独立可信地验证产物和目标身份、可恢复替换、权限及竞态；构建、安装和 Helper 服务重启必须各自明确授权，`--with-app` 不证明授权或可用。历史独立应用不自动删除；隔离测试不触碰系统。

`Actions.m` 的事件创建失败路径只记录失败并安全返回，不释放或投递空对象；隔离失败替身不证明系统键盘状态已恢复。Buttons/ClickCycle 的释放回调按设备身份与按钮归属并在 pass-through 门禁前消费，每个已注册 callback 只消费一次。

## AOCI / 仓库治理绑定

### 当前接入结论

本次对仓库 HEAD 的只读审计没有发现项目内 AOCI 合同或正式资产：没有跟踪的 `aoci.txt`、`aoci.code.txt`、`aoci.meta.txt`、`.aoci/`、项目 Guide、项目 AOCI 配置或 task-bound 服务入口。主机上可能存在其他项目使用的 AOCI 可执行文件，但那不构成本项目的接入，也不提供本任务的绑定证明。

因此本项目当前 **AOCI 不适用/未接入**：项目不运行 `init`、`scan`、`maintain`、`update-entry`、`verify`、`check` 或 `mcp`，不创建伪 index、Baseline、Ledger、receipt、`.aoci/` 或其他正式治理资产，也不借用主 checkout/其他项目的服务。没有 AOCI 批次、候选身份或 Baseline 需要报告；这不是绕过治理，而是遵守“项目未接入则不伪造接入”的安全边界。

### 将来启用时的硬门槛

只有项目明确加入 Guide、scope/预算、正式资产范围和恢复入口后，才能启用 AOCI，并须把配置提交到本项目、而非依赖个人主目录。启用后：

1. 首次 Overview、Maintain、Update、Verify 或 Check 前，记录任务 worktree、Agent Run cwd、完整源码候选 SHA、主线基线 SHA 和 `git worktree list --porcelain`。session cwd 与任务树是不同上下文，不要求相等；若实际服务依赖 session cwd 或项目另有更严格要求，则遵守该要求。
2. 核验实际使用的接口支持所需操作且目标为任务 worktree 或已批准的固定候选。AOCI CLI 必须显式使用 `--repo "$TASK"`，并以真实只读输出确认目标；所用 MCP/服务须以只读 probe 确认 `runtime_repository_root` 或固定候选身份。两种接口均使用时分别核验；未使用的接口和常驻 MCP 不要求绑定。不得假定 CLI 支持所有 MCP 操作；`cd`、Git 状态或当前 session cwd 不能证明或重绑服务。
3. 所需目标、能力、范围或证明不明，目标不匹配、候选漂移或写入结果未知时，停止受影响的正式治理读写和受管候选交付，保留 source-bound 现场。按当前 Guide 和项目支持的恢复入口核对 preimage/postimage 与事务状态，不盲目重放；不创建替代资产、不手改 Baseline、不清 Ledger、不重放旧 receipt。保留工具的 CAS 检查与用户数据保护。
4. 在源码稳定态按实时 Guide 分流 `authoring_required`、`observed_*`、`scope_change_required` 和 `blocked`。机器返回的 `path`、`source_sha256`、`candidate_id`、`code_batch_id` 和 domain/批次身份必须原样保留，并核对源码、配置、Baseline 和批次身份，不自行拼造或拆分。
5. 启用治理后，项目自有交付入口对每个候选按当前真实范围判定；受管源码-only 候选即使正式资产未变也不能跳过治理，范围未知即阻塞。真实接口和同候选的 Verify、Check、实时 Guide 证明必须有效；缺失、错误、过期、目标或候选不匹配均拒绝。为该入口增加有效证明通过及无效证明拒绝的回归；离线替身或静态文档不是实际治理证明。
6. 稳定源码候选上完成维护后，Verify、Check、实时 Guide、正式资产提交和合入都绑定同一完整 SHA；rebase、候选、Baseline 或策略变化后重新读取 Guide、核验绑定并刷新受影响证明。若工具提供 `complete` 或 `next_action`，分别确认 `complete=true` 或 `next_action=none`，且没有 remaining、源码漂移、Scope/observe 债务或待恢复事务。AOCI 通过仍不替代项目测试、构建、发布和 worktree 收尾。

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

**单目标闭环契约（对齐 Reader 规范）：** 任务交付与工作树清理是一个连贯闭环。项目不应将交付割裂为“阶段 A 源码交付完成，阶段 B 另行收尾”导致孤儿工作树长期滞留磁盘。在确认主线推送成功且双机对齐后，发起交付的会话必须在当前轮次内立即执行收尾清理（从主 checkout 执行 `git worktree remove <精确路径>` 并按策略执行 `git branch -d <任务分支>`）；仅在明确属于多阶段未结项任务，或存在存活会话与活动进程实际依赖原路径时，才允许保留并报告为“部分完成”及剩余事项。活动会话的 SSH `ControlMaster`、MCP argv 中单独出现任务路径不阻断清理。严禁在门禁或交付流程中引入无实现的空验证器硬阻断；安全由明确授权与可用探针保障。

对根层扫描的每个候选报告“已清理／合法保留／待确认”。本项目基线中的 `mac-mouse-fix-scripts` 空目录未获删除授权，保持并报告。只有在未来已合入、干净、无会话/进程路径依赖且确认分支 tip 已交付时，才可从主 checkout 使用 `git worktree remove <精确路径>` 和默认 `git branch -d <任务分支>`；禁止 `-D`、`prune` 或跟随链接扩大范围。
