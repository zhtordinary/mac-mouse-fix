#!/usr/bin/env bash
# macOS 系统应用安装入口 (Direct Copy Install)
# 当前项目没有可信的 App verifier/所有权证明，显式 App 阶段在此 fail closed。
set -Eeuo pipefail

[[ "$#" -eq 1 && "$1" == "--with-app" ]] || {
  printf 'ERROR: App 安装/重启必须显式提供 --with-app\n' >&2
  exit 2
}

printf '%s\n' 'ERROR: App 安装/重启已阻塞：当前项目没有可信的产物、目标所有权和可恢复替换 verifier；不创建临时目录、不复制、签名、移动、安装或重启。' >&2
exit 3
