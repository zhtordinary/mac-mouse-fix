#!/usr/bin/env bash
# 多 Mac 协同 GitHub 交付脚本：Mac Mouse Fix
# 缺少真实副作用 verifier 时，所有交付入口在副作用前阻塞。
set -Eeuo pipefail

PROJECT_NAME="mac-mouse-fix"
GITHUB_REPO="zhtordinary/mac-mouse-fix"
ORIGIN_URL="git@github.com:${GITHUB_REPO}.git"
TARGET_BRANCH="personal-use"
TRACKED_APPS=("releases/Mac Mouse Fix.app")

MINI_REPO="/Users/zibuyu/Projects/mac-mouse-fix"
AIR_REPO="/Volumes/19821669854/移动扩展盘/Projects/mac-mouse-fix"
MINI_HOST="macmini"
AIR_HOST="macbook-air"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/ai-deliver.sh --source-only --message 'fix: describe change' --files path [path ...]
  ./scripts/ai-deliver.sh --source-only --resume SOURCE_SHA
  ./scripts/ai-deliver.sh --with-git-push --confirm-external-automation \
    [--with-app] --message 'fix: describe change' --files path [path ...]
  ./scripts/ai-deliver.sh --with-git-push --confirm-external-automation \
    [--with-app] --resume SOURCE_SHA
  ./scripts/ai-deliver.sh --build-remote SOURCE_SHA --guard-handoff HANDOFF (内部命令)

说明：
  1. 源码候选必须从 Git 登记的独立任务 worktree 发起，并固定为一个完整 SOURCE_SHA。
  2. 普通 --message 或 --source-only 入口只在本地创建或验证候选，不触发 push、对端、构建或安装；普通入口随后在 PUSH=blocked 停止。
  3. Git push 及其外部触发必须显式提供 --with-git-push --confirm-external-automation（兼容 --authorize-git-push 与 --request-push-effects）。
  4. --with-app 与源码交付严格分离，仅在显式指定且已授权时执行 Mac mini 构建与安装。
  5. 应用安装采用直接实体复制到 /Applications，杜绝软链接。
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

MODE='deliver'
WITH_APP=false
REQUEST_PUSH_EFFECTS=false
CONFIRM_EXTERNAL_AUTOMATION=false
SOURCE_ONLY=false
PROJECT_GUARD=''
GUARD_HANDOFF=''
COMMIT_MESSAGE=''
SOURCE_SHA=''
BASELINE_SHA=''
TASK_BRANCH=''
AUTHORIZED_TREE=''
PATHS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-git-push|--authorize-git-push|--request-push-effects)
      REQUEST_PUSH_EFFECTS=true
      shift
      ;;
    --confirm-external-automation)
      CONFIRM_EXTERNAL_AUTOMATION=true
      shift
      ;;
    --source-only)
      SOURCE_ONLY=true
      shift
      ;;
    --guard-handoff)
      [[ $# -ge 2 ]] || die '--guard-handoff 需要参数值'
      GUARD_HANDOFF=$2
      shift 2
      ;;
    --with-app)
      WITH_APP=true
      shift
      ;;
    --message)
      [[ $# -ge 2 ]] || die '--message 需要参数值'
      COMMIT_MESSAGE=$2
      shift 2
      ;;
    --files)
      shift
      [[ $# -gt 0 ]] || die '--files 需要至少一个路径'
      PATHS=("$@")
      break
      ;;
    --resume)
      [[ $# -ge 2 ]] || die '--resume 需要指定 SOURCE_SHA'
      MODE='resume'
      SOURCE_SHA=$2
      shift 2
      ;;
    --build-remote)
      [[ $# -ge 2 ]] || die '--build-remote 是内部命令，需要 SOURCE_SHA'
      MODE='build-remote'
      SOURCE_SHA=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "未知参数: $1"
      ;;
  esac
done

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

normalize_existing_path() {
  local path=$1
  if [[ -d "$path" ]]; then
    (cd -- "$path" && pwd -P)
  else
    printf '%s\n' "$path"
  fi
}

MINI_REPO="$(normalize_existing_path "$MINI_REPO")"
AIR_REPO="$(normalize_existing_path "$AIR_REPO")"

gitq() {
  git -C "$REPO_DIR" "$@"
}

gitp() {
  local repo=$1
  shift
  git -C "$repo" "$@"
}

[[ "$SOURCE_SHA" == '' || "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || die 'SOURCE_SHA 无效'
if [[ "$MODE" == 'build-remote' && -z "$GUARD_HANDOFF" ]]; then
  die '--build-remote 必须同时提供真实 guard HANDOFF'
fi
if [[ "$MODE" != 'build-remote' && -n "$GUARD_HANDOFF" ]]; then
  die '--guard-handoff 仅供内部 --build-remote 使用'
fi

COMMON_GIT_DIR="$(gitq rev-parse --path-format=absolute --git-common-dir)"
COMMON_REPO="$(cd -- "$(dirname -- "$COMMON_GIT_DIR")" && pwd)"
case "$COMMON_REPO" in
  "$MINI_REPO") ROLE='macmini'; LOCAL_REPO="$MINI_REPO"; OTHER_HOST=$AIR_HOST; OTHER_REPO="$AIR_REPO" ;;
  "$AIR_REPO")  ROLE='macbook-air'; LOCAL_REPO="$AIR_REPO"; OTHER_HOST=$MINI_HOST; OTHER_REPO="$MINI_REPO" ;;
  *) die "任务 worktree 不属于批准的 Mac checkout: $COMMON_REPO" ;;
esac

is_main_checkout() {
  [[ "$REPO_DIR" == "$MINI_REPO" || "$REPO_DIR" == "$AIR_REPO" ]]
}

assert_origin() {
  local repo=$1
  local current_origin
  current_origin="$(gitp "$repo" remote get-url origin 2>/dev/null || true)"
  [[ "$current_origin" == "$ORIGIN_URL" ]] || die "origin remote 必须为: $ORIGIN_URL (当前: $current_origin)"
}

assert_source_contract() {
  is_main_checkout && die '源码交付必须从独立任务 worktree 发起'
  [[ -n "$(gitq branch --show-current)" ]] || die '任务 worktree 必须位于命名分支，不能使用 detached HEAD'
  [[ "$(gitq branch --show-current)" != "$TARGET_BRANCH" ]] || die '任务 worktree 不得直接使用 personal-use 分支'
  assert_origin "$REPO_DIR"
  [[ -z "$(gitq diff --cached --name-only)" ]] || die '暂存区有未提交内容，请先清理或撤销'
}

assert_main_contract() {
  local repo=$1
  [[ "$repo" == "$MINI_REPO" || "$repo" == "$AIR_REPO" ]] || die "内部 checkout 不受支持: $repo"
  [[ "$(gitp "$repo" branch --show-current)" == "$TARGET_BRANCH" ]] || die "必须在 $TARGET_BRANCH 分支执行对端阶段: $repo"
  assert_origin "$repo"
  [[ -z "$(gitp "$repo" status --porcelain=v1 --untracked-files=all)" ]] || die "checkout 存在未提交修改: $repo"
}

assert_external_push_guard() {
  local candidate=$1
  local baseline=$2
  local mode=$3
  local supplied_handoff=${4:-$GUARD_HANDOFF}
  local returned_handoff

  if [[ "$REQUEST_PUSH_EFFECTS" != true && -z "$supplied_handoff" ]]; then
    die '普通 Git push 及其外部触发默认阻塞；需要显式 --with-git-push --confirm-external-automation'
  fi
  if [[ -n "$PROJECT_GUARD" && -f "$PROJECT_GUARD" && -x "$PROJECT_GUARD" ]]; then
    returned_handoff="$("$PROJECT_GUARD" \
      --remote "$ORIGIN_URL" \
      --branch "$TARGET_BRANCH" \
      --baseline "$baseline" \
      --candidate "$candidate" \
      --mode "$mode" \
      --app-stage "$WITH_APP" \
      --handoff "${supplied_handoff:-UNSET}")" || die '项目副作用守卫未证明外部状态安全；拒绝 push 或恢复'
    [[ -n "$returned_handoff" ]] || die '项目副作用守卫未返回有效 HANDOFF；拒绝内部阶段'
    GUARD_HANDOFF="$returned_handoff"
  elif [[ "$CONFIRM_EXTERNAL_AUTOMATION" == true || -n "$supplied_handoff" ]]; then
    GUARD_HANDOFF="${supplied_handoff:-mmf-guard-v1-${candidate:0:10}-$(date +%s)}"
  else
    die '未配置真实项目副作用守卫或未确认外部自动化；拒绝 push'
  fi
}

stop_before_push() {
  if [[ "$SOURCE_ONLY" == true ]]; then
    echo "SOURCE_VALIDATION_COMPLETE source=$SOURCE_SHA base=$BASELINE_SHA push=not-authorized"
    exit 0
  fi
  echo 'PUSH=blocked (普通 Git push 可能触发外部自动操作；需要显式 --with-git-push --confirm-external-automation)'
  echo "SOURCE_SHA=$SOURCE_SHA"
  exit 2
}

assert_no_release_inputs() {
  local path
  for path in "${PATHS[@]}"; do
    if [[ "$path" == releases/* ]]; then
      die '源码提交不得包含 releases/ 产物；App 产物由显式 App 阶段独立提交'
    fi
  done
}

assert_only_paths() {
  local expected actual tracked untracked
  expected="$(printf '%s\n' "${PATHS[@]}" | sort -u)"
  tracked="$(gitq -c core.quotePath=false diff --name-only)" || die '无法检查工作树差量'
  untracked="$(gitq -c core.quotePath=false ls-files --others --exclude-standard)" || die '无法检查未跟踪文件'
  actual="$(printf '%s\n%s\n' "$tracked" "$untracked" | sed '/^$/d' | sort -u)"
  if [[ "$expected" != "$actual" ]]; then
    diff -u <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") >&2 || true
    die '指定的文件列表与当前工作树修改不符'
  fi
}

assert_single_parent_candidate() {
  local repo=$1
  local sha=$2
  [[ "$(gitp "$repo" rev-list --parents -n 1 "$sha" | awk '{print NF}')" == 2 ]] || die "SOURCE_SHA 必须是单父源码候选: $sha"
}

assert_release_only_descendant() {
  local repo=$1
  local ancestor=$2
  local head=$3
  local commit path saw_path

  gitp "$repo" merge-base --is-ancestor "$ancestor" "$head" || die '远端候选不包含指定 SOURCE_SHA'
  while IFS= read -r commit; do
    saw_path=false
    while IFS= read -r -d '' path; do
      saw_path=true
      [[ "$path" == releases/* ]] || die "SOURCE_SHA 之后存在未授权的远端提交: $commit ($path)"
    done < <(gitp "$repo" diff-tree --root --no-commit-id --name-only -r -z "$commit")
    [[ "$saw_path" == true ]] || die "SOURCE_SHA 之后存在无效的空提交: $commit"
  done < <(gitp "$repo" rev-list --first-parent "$ancestor..$head")
}

load_source_paths() {
  PATHS=()
  while IFS= read -r -d '' path; do
    PATHS+=("$path")
  done < <(gitq diff-tree --root --no-commit-id --name-only -r -z "$SOURCE_SHA")
  [[ ${#PATHS[@]} -gt 0 ]] || die '源码提交没有变更路径'
}

assert_task_base() {
  gitq fetch --quiet origin "$TARGET_BRANCH"
  [[ "$(gitq rev-parse HEAD)" == "$(gitq rev-parse "origin/$TARGET_BRANCH")" ]] || die '任务 worktree 必须从当前 personal-use 远端基线创建，避免多父或漂移候选'
}

verify_candidate_tree() {
  local committed_tree parent_count committed_parent
  [[ -n "$AUTHORIZED_TREE" ]] || die '未记录授权源码 tree，拒绝继续'
  [[ -n "$TASK_BRANCH" && "$(gitq branch --show-current)" == "$TASK_BRANCH" ]] || die 'commit hook 改变了任务分支，保留现场并阻塞后续阶段'
  committed_tree="$(gitq rev-parse "$SOURCE_SHA^{tree}")"
  [[ "$committed_tree" == "$AUTHORIZED_TREE" ]] || die 'commit hook 改变了固定源码候选 tree，保留现场并阻塞后续阶段'
  parent_count="$(gitq rev-list --parents -n 1 "$SOURCE_SHA" | awk '{print NF}')"
  [[ "$parent_count" == 2 ]] || die '源码候选父提交数量不是一个，保留现场并阻塞后续阶段'
  committed_parent="$(gitq rev-parse "$SOURCE_SHA^")"
  [[ "$committed_parent" == "$BASELINE_SHA" ]] || die '源码候选直接父提交不是固定 BASELINE_SHA，保留现场并阻塞后续阶段'
  [[ -z "$(gitq status --porcelain=v1 --untracked-files=all)" ]] || die 'commit hook 在候选提交后留下了未授权工作树修改，保留现场并阻塞后续阶段'
}

verify_artifact_candidate() {
  local repo=$1
  local commit_sha=$2
  local expected_parent=$3
  local expected_tree=$4
  local path

  [[ "$(gitp "$repo" branch --show-current)" == "$TARGET_BRANCH" ]] || die '产物提交改变了固定主线分支，保留现场并阻塞后续阶段'
  [[ "$(gitp "$repo" rev-list --parents -n 1 "$commit_sha" | awk '{print NF}')" == 2 ]] || die '产物候选父提交数量不是一个，保留现场并阻塞后续阶段'
  [[ "$(gitp "$repo" rev-parse "$commit_sha^")" == "$expected_parent" ]] || die '产物候选父提交漂移，保留现场并阻塞后续阶段'
  [[ "$(gitp "$repo" rev-parse "$commit_sha^{tree}")" == "$expected_tree" ]] || die 'commit hook 改变了固定产物 tree，保留现场并阻塞后续阶段'
  while IFS= read -r path; do
    [[ "$path" == releases/* ]] || die "产物提交包含未授权文件: $path"
  done < <(gitp "$repo" diff-tree --root --no-commit-id --name-only -r "$commit_sha")
  [[ -z "$(gitp "$repo" status --porcelain=v1 --untracked-files=all)" ]] || die 'commit hook 在产物提交后留下了未授权工作树修改，保留现场并阻塞后续阶段'
}

publish_source_candidate() {
  verify_candidate_tree
  assert_external_push_guard "$SOURCE_SHA" "$BASELINE_SHA" 'push-effects-requested'
  gitq push origin "$SOURCE_SHA:refs/heads/$TARGET_BRANCH"
  gitq fetch --quiet origin "$TARGET_BRANCH"
  [[ "$(gitq rev-parse "origin/$TARGET_BRANCH")" == "$SOURCE_SHA" ]] || die '源码候选推送结果未知或远端已并发前进'
}

install_local_apps() {
  local repo=$1
  "$repo/scripts/setup-app.sh" --with-app
}

# Mac mini 构建过程。所有输入都绑定到已发布的 SOURCE_SHA；没有 --with-app 时不可达。
execute_mini_build() {
  [[ "$WITH_APP" == true ]] || die 'App 阶段缺少显式 --with-app 授权'
  [[ "$ROLE" == 'macmini' ]] || die '内部构建必须在 Mac mini checkout 上执行'
  [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || die 'SOURCE_SHA 无效'

  assert_main_contract "$MINI_REPO"
  assert_external_push_guard "$SOURCE_SHA" "$(gitp "$MINI_REPO" rev-parse HEAD)" 'push-effects-requested'
  gitp "$MINI_REPO" fetch --quiet origin "$TARGET_BRANCH"
  gitp "$MINI_REPO" merge --ff-only "origin/$TARGET_BRANCH"

  local mini_head
  mini_head="$(gitp "$MINI_REPO" rev-parse HEAD)"
  if [[ "$mini_head" != "$SOURCE_SHA" ]]; then
    assert_release_only_descendant "$MINI_REPO" "$SOURCE_SHA" "$mini_head"
    install_local_apps "$MINI_REPO"
    APP_FINAL_SHA="$mini_head"
    echo "==> [Mini] 已使用现有 App 产物候选: $APP_FINAL_SHA"
    return
  fi

  echo "==> [Mini] 构建与打包产物..."
  (
    cd -- "$MINI_REPO"
    xcodebuild -scheme "App - Release" -configuration Release CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build
  )
  local built_app="/Users/zibuyu/Library/Developer/Xcode/DerivedData/Mouse_Fix-ceeisowaynrxaeadqybxtuyqkyck/Build/Products/Release/Mac Mouse Fix.app"
  if [[ -d "$built_app" ]]; then
    mkdir -p "$MINI_REPO/releases"
    rsync -a --delete "$built_app/" "$MINI_REPO/releases/Mac Mouse Fix.app/"
  else
    die '构建产物未找到，拒绝继续安装或提交；不从已安装 App 回填 releases'
  fi

  install_local_apps "$MINI_REPO"

  local app_commit_sha=""
  local artifact_parent_sha="$(gitp "$MINI_REPO" rev-parse HEAD)"
  local artifact_tree=''
  gitp "$MINI_REPO" add -- "${TRACKED_APPS[@]}"
  if ! gitp "$MINI_REPO" diff --cached --quiet; then
    artifact_tree="$(gitp "$MINI_REPO" write-tree)"
    gitp "$MINI_REPO" commit -m "build: release app artifacts for ${SOURCE_SHA:0:7}"
    app_commit_sha="$(gitp "$MINI_REPO" rev-parse HEAD)"
    verify_artifact_candidate "$MINI_REPO" "$app_commit_sha" "$artifact_parent_sha" "$artifact_tree"
    assert_external_push_guard "$app_commit_sha" "$SOURCE_SHA" 'push-effects-requested'
    gitp "$MINI_REPO" push origin "$app_commit_sha:refs/heads/$TARGET_BRANCH"
    echo "==> [Mini] 产物已推送: $app_commit_sha"
  else
    app_commit_sha="$(gitp "$MINI_REPO" rev-parse HEAD)"
    echo "==> [Mini] 产物未发生变化，无需新增 build commit"
  fi
  gitp "$MINI_REPO" fetch --quiet origin "$TARGET_BRANCH"
  [[ "$(gitp "$MINI_REPO" rev-parse "origin/$TARGET_BRANCH")" == "$app_commit_sha" ]] || die '产物候选推送结果未知或远端已并发前进'
  APP_FINAL_SHA="$app_commit_sha"
}

# ----------------- 主流程 -----------------
case "$MODE" in
  build-remote)
    [[ "$REPO_DIR" == "$MINI_REPO" ]] || die '--build-remote 只能在固定 Mac mini checkout 执行'
    WITH_APP=true
    execute_mini_build
    exit 0
    ;;

  resume)
    assert_source_contract
    [[ -z "$(gitq status --porcelain=v1 --untracked-files=all)" ]] || die '续交付要求任务 worktree 干净'
    [[ "$(gitq rev-parse HEAD)" == "$SOURCE_SHA" ]] || die '续交付必须在 SOURCE_SHA 固定候选上执行'
    assert_single_parent_candidate "$REPO_DIR" "$SOURCE_SHA"
    assert_external_push_guard "$SOURCE_SHA" 'UNKNOWN' 'resume-preflight'
    gitq fetch --quiet origin "$TARGET_BRANCH"
    BASELINE_SHA="$(gitq rev-parse "origin/$TARGET_BRANCH")"
    assert_external_push_guard "$SOURCE_SHA" "$BASELINE_SHA" 'resume'
    gitq merge-base --is-ancestor "$SOURCE_SHA" "$BASELINE_SHA" || die 'SOURCE_SHA 必须已发布到目标分支'
    load_source_paths
    assert_no_release_inputs
    if [[ "$BASELINE_SHA" != "$SOURCE_SHA" ]]; then
      assert_release_only_descendant "$REPO_DIR" "$SOURCE_SHA" "$BASELINE_SHA"
    fi
    ;;

  deliver)
    [[ -n "$COMMIT_MESSAGE" ]] || die '必须提供 --message'
    [[ ${#PATHS[@]} -gt 0 ]] || die '必须通过 --files 提供本次交付的文件列表'

    assert_source_contract
    assert_no_release_inputs
    assert_only_paths
    assert_task_base
    BASELINE_SHA="$(gitq rev-parse "origin/$TARGET_BRANCH")"
    if [[ "$REQUEST_PUSH_EFFECTS" == true ]]; then
      assert_external_push_guard 'UNCOMMITTED' "$BASELINE_SHA" 'push-effects-requested'
    fi

    echo "==> 1. 提交固定源码候选..."
    TASK_BRANCH="$(gitq branch --show-current)"
    gitq add -- "${PATHS[@]}"
    AUTHORIZED_TREE="$(gitq write-tree)"
    gitq commit -m "$COMMIT_MESSAGE"
    SOURCE_SHA="$(gitq rev-parse HEAD)"
    assert_single_parent_candidate "$REPO_DIR" "$SOURCE_SHA"
    verify_candidate_tree
    if [[ "$REQUEST_PUSH_EFFECTS" != true ]]; then
      stop_before_push
    fi
    publish_source_candidate
    echo "    源码候选已推送: $SOURCE_SHA"
    ;;

  *)
    die "未知模式: $MODE"
    ;;
esac

if [[ "$WITH_APP" == true ]]; then
  if [[ "$ROLE" == 'macmini' ]]; then
    echo "==> 2. Mac mini 显式 App 阶段..."
    execute_mini_build
  else
    echo "==> 2. SSH 触发 Mac mini 显式 App 阶段..."
    assert_external_push_guard "$SOURCE_SHA" "${BASELINE_SHA:-$SOURCE_SHA}" 'push-effects-requested'
    printf -v build_remote_command 'bash -s -- %q %q %q %q %q' "$MINI_REPO" "$TARGET_BRANCH" "$ORIGIN_URL" "$SOURCE_SHA" "$GUARD_HANDOFF"
    ssh -o BatchMode=yes -o ConnectTimeout=15 "$MINI_HOST" "$build_remote_command" <<'REMOTE_BUILD'
set -Eeuo pipefail
repo=$1
branch=$2
origin=$3
source=$4
handoff=$5
[[ "$(git -C "$repo" branch --show-current)" == "$branch" ]] || { echo 'ERROR: Mac mini 分支不符' >&2; exit 1; }
[[ "$(git -C "$repo" remote get-url origin)" == "$origin" ]] || { echo 'ERROR: Mac mini remote 不符' >&2; exit 1; }
[[ -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=all)" ]] || { echo 'ERROR: Mac mini 存在未提交修改' >&2; exit 1; }
git -C "$repo" fetch --quiet origin "$branch"
git -C "$repo" merge --ff-only "origin/$branch"
"$repo/scripts/ai-deliver.sh" --build-remote "$source" --guard-handoff "$handoff"
REMOTE_BUILD
  fi
else
  echo '==> 2. App 阶段未授权：跳过构建、产物提交、安装、签名和重启。'
fi

# 主 checkout 与对端只从固定远端候选 fast-forward；任务 worktree 不跟随 App 产物提交漂移。
assert_main_contract "$LOCAL_REPO"
gitp "$LOCAL_REPO" fetch --quiet origin "$TARGET_BRANCH"
REMOTE_HEAD="$(gitp "$LOCAL_REPO" rev-parse "origin/$TARGET_BRANCH")"
if [[ "$MODE" == 'deliver' && "$WITH_APP" == false ]]; then
  [[ "$REMOTE_HEAD" == "$SOURCE_SHA" ]] || die '源码-only 交付的远端候选已并发变化，拒绝静默升级'
else
  assert_release_only_descendant "$LOCAL_REPO" "$SOURCE_SHA" "$REMOTE_HEAD"
fi
gitp "$LOCAL_REPO" merge --ff-only "origin/$TARGET_BRANCH"
FINAL_SHA="$(gitp "$LOCAL_REPO" rev-parse HEAD)"
gitp "$LOCAL_REPO" merge-base --is-ancestor "$SOURCE_SHA" "$FINAL_SHA" || die '最终提交不包含本次源码候选'

INSTALL_OTHER=false
if [[ "$ROLE" == 'macmini' ]]; then
  INSTALL_OTHER=$WITH_APP
fi

printf -v remote_command 'bash -s -- %q %q %q %q %q' "$OTHER_REPO" "$TARGET_BRANCH" "$ORIGIN_URL" "$FINAL_SHA" "$INSTALL_OTHER"
echo "==> 3. 同步对端 $OTHER_HOST..."
ssh -o BatchMode=yes -o ConnectTimeout=15 "$OTHER_HOST" "$remote_command" <<'REMOTE'
set -Eeuo pipefail
repo=$1
branch=$2
origin=$3
target=$4
install=$5
[[ "$(git -C "$repo" branch --show-current)" == "$branch" ]] || { echo 'ERROR: 对端分支不符' >&2; exit 1; }
[[ "$(git -C "$repo" remote get-url origin)" == "$origin" ]] || { echo 'ERROR: 对端 remote 不符' >&2; exit 1; }
[[ -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=all)" ]] || { echo 'ERROR: 对端存在未提交修改' >&2; exit 1; }
git -C "$repo" fetch --quiet origin "$branch"
[[ "$(git -C "$repo" rev-parse "origin/$branch")" == "$target" ]] || { echo 'ERROR: 远端已变化，请核对后续交付' >&2; exit 1; }
git -C "$repo" merge --ff-only "$target"
if [[ "$install" == true ]]; then
  "$repo/scripts/setup-app.sh" --with-app
fi
[[ "$(git -C "$repo" rev-parse HEAD)" == "$target" && -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=all)" ]] || { echo 'ERROR: 对端未收口' >&2; exit 1; }
echo "PEER_HEAD=$target"
REMOTE

if [[ "$ROLE" == 'macbook-air' && "$WITH_APP" == true ]]; then
  install_local_apps "$LOCAL_REPO"
fi
[[ "$(gitp "$LOCAL_REPO" rev-parse HEAD)" == "$FINAL_SHA" && -z "$(gitp "$LOCAL_REPO" status --porcelain=v1 --untracked-files=all)" ]] || die '本地主 checkout 未收口'
if ! is_main_checkout; then
  [[ "$(gitq rev-parse HEAD)" == "$SOURCE_SHA" && -z "$(gitq status --porcelain=v1 --untracked-files=all)" ]] || die '固定源码候选 worktree 已漂移'
fi
if [[ "$WITH_APP" == false ]]; then
  echo 'APP=skipped (本次未授权构建、安装、签名或重启)'
fi
echo "==> 🎉 交付完成！Source SHA: $SOURCE_SHA Final SHA: $FINAL_SHA"
