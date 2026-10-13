# WeTypeVoiceTrigger（微信输入法语音输入双击唤醒助手）

本组件是配合 Mac Mouse Fix（MMF）在双 Mac（Mac mini + MacBook Air）跨屏漫游及通用控制（Universal Control）场景下的**无侵入轻量级伴侣应用**。

---

## 1. 背景与技术边界

### 目标
在纯鼠标握持场景下，通过**鼠标滚轮中键双击**瞬间唤醒微信输入法（WeType）的语音输入功能；同时必须**绝对保证**：
1. **通用控制（Universal Control）不中断**：MacBook Air 与 Mac mini 之间的鼠标指针自由漫游与手势无缝衔接。
2. **Mac Mouse Fix 功能完整**：单选中键、双击缩放、手势滑动等既有配置不受任何干扰。
3. **零硬件驱动劫持**：杜绝 DriverKit / Karabiner 抓取鼠标引起的 300ms 点击延迟或驱动冲突。

### 为什么不能直接由 MMF 发送按键？
* **微信输入法的硬件级校验**：微信输入法的核心组件 `ShortcutKeyMonitor` 强制监听硬件底层的真实按键扫描码（ScanCode）。任何经由系统 `CGEvent` 或虚拟键盘注入的软件级修饰键（如单点 Control / 双击 Control），均会被微信输入法静默过滤丢弃。
* **DriverKit 劫持成本过高**：若通过 Karabiner DriverKit 虚拟硬件强制劫持鼠标按键，会导致通用控制（Universal Control）鼠标漫游失效，且为区分单双击会引入物理按键 300ms 抬手延迟。

---

## 2. 核心架构与加速原理（v2 Turbo）

`WeTypeVoiceTrigger.app` 采用 **`listenOnly` 事件纯监听 + 异步菜单触发** 的最优架构：

1. **零延迟事件监听（`listenOnly`）**：
   - 挂载在系统事件链最顶端（`kCGHIDEventTap`），配置为 `.listenOnly`。
   - **完全不拦截、不吞掉、不延迟** 任何物理按键事件，MMF 与 Universal Control 100% 透明透传。
   - 内置精准状态机识别 `0.06s ~ 0.65s` 内的滚轮中键双击，并在触发后进入 `0.50s` 防抖冷却期，防止误触闪烁。

2. **极速异步菜单触发（Non-blocking Async Dispatch）**：
   - 微信输入法的语音输入挂载在系统原生输入法菜单栏中（`com.apple.TextInputMenuAgent`）。
   - **优化瓶颈**：原先直接同步调用 `kAXPressAction` 展开状态栏会导致线程卡死等待系统动画约 1.15 秒。
   - **极速方案**：在后台并发高优先级队列发起展开动作，主流程通过 15ms 微探针直接寻址并点击 `语音输入（左 control）` 菜单项。
   - **实测响应延迟**：从优化前的 **1540 毫秒** 暴降至 **220 毫秒（提速 6 倍以上）**，双击滚轮即瞬间弹出语音录制窗口。

3. **标准 Cocoa 响应架构**：
   - 采用标准 `NSApplication.run` 主事件循环，通过非阻塞计时器监控辅助功能信任状态。
   - 杜绝传统单线程脚本导致的“应用程序没有响应”或频繁弹窗问题。

---

## 3. 安装与双机部署

### 文件规范
* 本机 App 路径：`/Applications/WeTypeVoiceTrigger.app`
* 源码与构建脚本：`/Users/zibuyu/Projects/mac-mouse-fix/WeTypeVoiceTrigger/`

### 自动构建与同步
在 `WeTypeVoiceTrigger` 目录下执行构建脚本：
```bash
./build.sh
```
脚本会自动完成：
1. 编译生成 Release 二进制文件；
2. 打包生成带有 `LSUIElement=true`（无 Dock 栏后台常驻）的标准 macOS App Bundle；
3. 完成本地 Ad-Hoc 签名；
4. 若局域网 MacBook Air 在线，通过内网 rsync 自动同步并完成远端签名。

---

## 4. 系统权限与开机自启配置

由于 macOS TCC 安全机制对监听鼠标事件与辅助功能界面的严格限制，两台 Mac 首次配置需满足以下两项：

### 1. 辅助功能（Accessibility）授权
打开 **系统设置 > 隐私与安全性 > 辅助功能**：
* 找到 **`WeTypeVoiceTrigger.app`**（或微信语音双击助手），将其右侧开关打开（蓝色）。
* *注意*：若后续重新编译导致二进制哈希变化，需在列表中选中旧项按 `-` 删除后，重新将 `/Applications/WeTypeVoiceTrigger.app` 拖入并开启，确保系统录入最新签名哈希。

### 2. 开机自动启动（Login Items）
已通过 AppleScript 注册进系统的用户登录项（**系统设置 > 通用 > 登录项与扩展**），开机或用户登录时静默自启，无需任何人工干预。

---

## 5. 日志与验证排查

运行时调试日志路径：`/tmp/wetype_trigger.log`

典型正常运行日志：
```text
[WETYPE] Accessibility permission ACTIVE! Setting up event tap...
[WETYPE] >>> READY! Event tap listening for middle double-clicks!
[WETYPE] >>> Middle double-click detected (diff=0.186s)! Triggering voice input...
[WETYPE] >>> SUCCESS! Voice input triggered in 229.99ms (attempt 0)
```
