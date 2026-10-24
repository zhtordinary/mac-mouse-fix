#!/usr/bin/env bash
# 多 Mac 协同 GitHub 交付脚本：Mac Mouse Fix
# 架构：双 Mac 对偶发起 + 固定 Mac mini 构建 + tracked app 独立提交 + 直接实体复制安装(/Applications)
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
  ./scripts/ai-deliver.sh --message 'fix: describe change' --files path [path ...]
  ./scripts/ai-deliver.sh --resume SOURCE_SHA
  ./scripts/ai-deliver.sh --build-remote SOURCE_SHA (内部命令)

说明：
  1. 无论在 Mac mini 还是 MacBook Air 均可直接发起。
  2. 源码提交与 releases 产物提交完全分离。
  3. 文档、规则、脚本等非运行时改动仅同步 Git，跳过构建、安装、签名与重启。
  4. 应用安装采用直接实体复制到 /Applications，杜绝软链接。
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

MODE='deliver'
COMMIT_MESSAGE=''
SOURCE_SHA=''
PATHS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
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
      [[ $# -eq 2 ]] || die '--resume 需要指定 SOURCE_SHA'
      MODE='resume'
      SOURCE_SHA=$2
      shift 2
      ;;
    --build-remote)
      [[ $# -eq 2 ]] || die '--build-remote 是内部命令，需要 SOURCE_SHA'
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

case "$REPO_DIR" in
  "$MINI_REPO") ROLE='macmini' ;;
  "$AIR_REPO")  ROLE='macbook-air' ;;
  *) die "不支持的 checkout 目录: $REPO_DIR (必须是 $MINI_REPO 或 $AIR_REPO)" ;;
esac

gitq() {
  git -C "$REPO_DIR" "$@"
}

assert_contract() {
  [[ "$(gitq branch --show-current)" == "$TARGET_BRANCH" ]] || die "必须在 $TARGET_BRANCH 分支执行交付"
  local current_origin
  current_origin="$(gitq remote get-url origin 2>/dev/null || true)"
  [[ "$current_origin" == "$ORIGIN_URL" ]] || die "origin remote 必须为: $ORIGIN_URL (当前: $current_origin)"
  [[ -z "$(gitq diff --cached --name-only)" ]] || die '暂存区有未提交内容，请先清理或撤销'
}

assert_no_release_inputs() {
  local path
  for path in "${PATHS[@]}"; do
    if [[ "$path" == releases/* ]]; then
      die '源码提交不得包含 releases/ 产物；app 产物由构建系统独立提交'
    fi
  done
}

assert_only_paths() {
  local expected_file actual_file tmp status=0
  tmp="$(mktemp -d)"
  expected_file="$tmp/expected"
  actual_file="$tmp/actual"

  printf '%s\n' "${PATHS[@]}" | sort -u > "$expected_file"
  {
    gitq -c core.quotePath=false diff --name-only
    gitq -c core.quotePath=false ls-files --others --exclude-standard
  } | sort -u > "$actual_file"

  if ! cmp -s "$expected_file" "$actual_file"; then
    printf '%s\n' '指定的文件列表与当前工作树修改不符:' >&2
    diff -u "$expected_file" "$actual_file" >&2 || true
    status=2
  fi
  rm -- "$expected_file" "$actual_file"
  rmdir -- "$tmp"
  return "$status"
}

paths_require_build() {
  local path
  for path in "${PATHS[@]}"; do
    case "$path" in
      *.md|AGENTS.md|README.md|Personal\ Use\ *.md|scripts/*|docs/*)
        ;;
      *)
        return 0
        ;;
    esac
  done
  return 1
}

# 实体复制安装与签名
install_local_apps() {
  "$REPO_DIR/scripts/setup-app.sh"
}

# Mac mini 构建过程
execute_mini_build() {
  [[ "$ROLE" == 'macmini' ]] || die '内部构建必须在 Mac mini 上执行'
  [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || die 'SOURCE_SHA 无效'

  assert_contract
  gitq fetch --quiet origin "$TARGET_BRANCH"
  gitq merge --ff-only "origin/$TARGET_BRANCH"

  echo "==> [Mini] 构建与打包产物..."
  # 构建 Mac Mouse Fix
  echo "==> [Mini] 构建 Mac Mouse Fix..."
  xcodebuild -scheme "App - Release" -configuration Release CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build
  local built_app="/Users/zibuyu/Library/Developer/Xcode/DerivedData/Mouse_Fix-ceeisowaynrxaeadqybxtuyqkyck/Build/Products/Release/Mac Mouse Fix.app"
  if [[ -d "$built_app" ]]; then
    mkdir -p "$REPO_DIR/releases"
    rsync -a --delete "$built_app/" "$REPO_DIR/releases/Mac Mouse Fix.app/"
  elif [[ -d "/Applications/Mac Mouse Fix.app" ]]; then
    rsync -a "/Applications/Mac Mouse Fix.app/" "$REPO_DIR/releases/Mac Mouse Fix.app/"
  fi

  # 本地实体安装
  install_local_apps

  # 提交产物
  local app_commit_sha=""
  gitq add "${TRACKED_APPS[@]}"
  if ! gitq diff --cached --quiet; then
    gitq commit -m "build: release app artifacts for ${SOURCE_SHA:0:7}"
    gitq push origin "$TARGET_BRANCH"
    app_commit_sha="$(gitq rev-parse HEAD)"
    echo "==> [Mini] 产物已推送: $app_commit_sha"
  else
    echo "==> [Mini] 产物未发生变化，无需新增 build commit"
  fi
}

# ----------------- 主流程 -----------------
case "$MODE" in
  build-remote)
    execute_mini_build
    exit 0
    ;;

  resume)
    [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || die 'SOURCE_SHA 无效'
    assert_contract
    [[ -z "$(gitq status --porcelain=v1 --untracked-files=all)" ]] || die '续交付要求工作区干净'
    gitq fetch --quiet origin "$TARGET_BRANCH"
    gitq merge-base --is-ancestor "$SOURCE_SHA" "origin/$TARGET_BRANCH" || die 'SOURCE_SHA 必须已发布到目标分支'
    while IFS= read -r -d '' path; do
      PATHS+=("$path")
    done < <(gitq diff-tree --root --no-commit-id --name-only -r -z "$SOURCE_SHA")
    [[ ${#PATHS[@]} -gt 0 ]] || die '源码提交没有变更路径'
    assert_no_release_inputs
    ;;

  deliver)
    [[ -n "$COMMIT_MESSAGE" ]] || die '必须提供 --message'
    [[ ${#PATHS[@]} -gt 0 ]] || die '必须通过 --files 提供本次交付的文件列表'

    assert_contract
    assert_no_release_inputs
    assert_only_paths

    echo "==> 1. 提交源码..."
    gitq add -- "${PATHS[@]}"
    gitq commit -m "$COMMIT_MESSAGE"
    gitq push origin "$TARGET_BRANCH"
    SOURCE_SHA="$(gitq rev-parse HEAD)"
    echo "    源码已推送: $SOURCE_SHA"
    ;;
esac

# 检查是否需要触发构建
NEEDS_BUILD=true
if ! paths_require_build; then
  NEEDS_BUILD=false
  echo "==> 本次均为文档/脚本修改，跳过构建。"
fi

if [[ "$NEEDS_BUILD" == true ]]; then
  if [[ "$ROLE" == 'macmini' ]]; then
    echo "==> 2. Mac mini 本地构建产物..."
    execute_mini_build
  else
    echo "==> 2. SSH 触发 Mac mini 远程构建..."
    ssh -o BatchMode=yes "$MINI_HOST" "$MINI_REPO/scripts/ai-deliver.sh --build-remote '$SOURCE_SHA'"
  fi
fi

# 两端以同一 GitHub 提交收口；仅运行时交付执行安装。
[[ -z "$(gitq status --porcelain=v1 --untracked-files=all)" ]] || die '同步前工作区必须干净'
gitq fetch --quiet origin "$TARGET_BRANCH"
if [[ "$NEEDS_BUILD" == false ]]; then
  [[ "$(gitq rev-parse "origin/$TARGET_BRANCH")" == "$SOURCE_SHA" ]] || die '远端已前进，请核对本次源码提交后续交付'
fi
gitq merge --ff-only "origin/$TARGET_BRANCH"
FINAL_SHA="$(gitq rev-parse HEAD)"
gitq merge-base --is-ancestor "$SOURCE_SHA" "$FINAL_SHA" || die '最终提交不包含本次源码提交'

if [[ "$ROLE" == 'macmini' ]]; then
  OTHER_HOST=$AIR_HOST
  OTHER_REPO=$AIR_REPO
  INSTALL_OTHER=$NEEDS_BUILD
else
  OTHER_HOST=$MINI_HOST
  OTHER_REPO=$MINI_REPO
  INSTALL_OTHER=false
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
  "$repo/scripts/setup-app.sh"
fi
[[ "$(git -C "$repo" rev-parse HEAD)" == "$target" && -z "$(git -C "$repo" status --porcelain=v1 --untracked-files=all)" ]] || { echo 'ERROR: 对端未收口' >&2; exit 1; }
echo "PEER_HEAD=$target"
REMOTE

if [[ "$ROLE" == 'macbook-air' && "$NEEDS_BUILD" == true ]]; then
  install_local_apps
fi
[[ "$(gitq rev-parse HEAD)" == "$FINAL_SHA" && -z "$(gitq status --porcelain=v1 --untracked-files=all)" ]] || die '本地未收口'
if [[ "$NEEDS_BUILD" == false ]]; then
  echo 'INSTALL=skipped (仅文档/工作流改动，未安装、签名或重启 App)'
fi
echo "==> 🎉 交付完成！Source SHA: $SOURCE_SHA Final SHA: $FINAL_SHA"
