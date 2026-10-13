#!/usr/bin/env bash
# macOS 系统应用直接安装与检查脚本 (Direct Copy Install)
# 作用：将 releases/ 下的应用直接复制到 /Applications，杜绝软链接，确保系统权限与通用控制稳定性。
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> [setup-app] 正在安装 releases 应用到 /Applications (直接实体复制模式)..."

APPS=("Mac Mouse Fix.app")

# 清理历史独立触发器（已原生并入 Mac Mouse Fix）
if [[ -e "/Applications/WeTypeVoiceTrigger.app" ]]; then
  printf '   - 清理已废弃独立应用: /Applications/WeTypeVoiceTrigger.app\n'
  rm -rf "/Applications/WeTypeVoiceTrigger.app"
fi

for app_name in "${APPS[@]}"; do
  src="$REPO_DIR/releases/$app_name"
  dst="/Applications/$app_name"
  
  [[ -d "$src" ]] || {
    printf 'ERROR: 产物未找到: %s (请先构建或从 GitHub 拉取 releases)\n' "$src" >&2
    exit 1
  }
  
  printf '   - 复制: %s -> %s\n' "$src" "$dst"
  rm -rf "$dst"
  cp -a "$src" "$dst"
  
  printf '   - 签名: %s\n' "$dst"
  codesign --force --deep --sign - "$dst" 2>/dev/null || true
  
  test -d "$dst"
  printf '   - 状态: 已安装就绪\n'
done

if pgrep -f "Mac Mouse Fix Helper" >/dev/null 2>&1; then
  printf '   - 重启运行中的 Mac Mouse Fix Helper...\n'
  killall "Mac Mouse Fix Helper" 2>/dev/null || true
  sleep 1
fi

echo "==> ✅ 全部应用已成功实体安装至 /Applications！"
