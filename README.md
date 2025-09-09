# Minecraft Mineflayer 机器人（Python 驱动）

本项目以 Python 作为入口，启动并驱动一个基于 Node.js 的 mineflayer 机器人，支持：
- 控制角色按方向或绝对朝向角度移动指定格数（默认 10 格）
- 在聊天框发送指定文本

Python 与 Node 机器人通过标准输入/输出交换 JSON 指令，结构清晰、便于扩展。

仓库地址：
https://github.com/YJLi-new/MCAgent-TempTest

---

## 功能概览
- 移动：支持绝对方向（north/south/east/west）、相对方向（forward/back/left/right），或通过 `--yaw-deg` 指定绝对朝向角度移动。
- 聊天：向服务器聊天框发送一条指定消息。

## 目录结构
```
.
├─ main.py          # Python 启动器与交互式 CLI
├─ bot.js           # Node + mineflayer 机器人桥接（move/say/quit）
├─ package.json     # Node 依赖与 npm scripts
├─ requirements.txt # Python 依赖（当前无需三方库）
└─ README.md
```

## 环境要求
- Python 3.8+
- Node.js 22+（mineflayer 生态对 Node 版本要求较新；推荐 nvm / nvm-windows 管理版本）
- 可连接的 Minecraft 服务器（默认 `127.0.0.1:25565`），或使用本地 Mock 模式进行快速验证

## 安装
1) 安装 Node 依赖：
```bash
npm install
```

2)（可选）安装 Python 依赖：
```bash
pip install -r requirements.txt
```

## 快速开始
- 连接本地服务器，向北移动 10 格并发送一条消息：
```bash
python main.py --host 127.0.0.1 --port 25565 --username Bot \
  --direction north --blocks 10 --message "你好，Minecraft！"
```

- 相对朝向移动：相对于当前面向前进 10 格：
```bash
python main.py --username Bot --direction forward --message "go go go"
```

- 指定移动格数：
```bash
python main.py --username Bot --direction east --blocks 12 --message "到位"
```

- 使用绝对朝向角度移动（0=东，90=南，180=西，270=北）：
```bash
python main.py --username Bot --yaw-deg 135 --blocks 10 --message "斜向 45°"
```

## Mock 本地测试（无需服务器）
- 一键测试（Python 侧）：
```bash
python main.py --mock --direction east --blocks 5 --message "TEST_CHAT"
```
控制台会看到 `[bridge] ready`、`say_result`、`move_result` 等事件。

- 手动输入 JSON（Node 侧）：
```bash
npm run mock
# 然后逐条输入以下行并回车
{"type":"move","direction":"north","blocks":10}
{"type":"say","message":"Hello"}
{"type":"quit"}
```

## 命令行参数（main.py）
- `--host`：服务器地址，默认 `127.0.0.1`
- `--port`：服务器端口，默认 `25565`
- `--username`：机器人用户名
- `--password`：可选，配合在线服鉴权使用
- `--auth`：可选，鉴权方式（如 `microsoft`）
- `--version`：可选，Minecraft 协议版本（不指定则由 mineflayer 自动检测）
- `--direction`：移动方向，`north|south|east|west|forward|back|left|right`（与 `--yaw-deg` 互斥）
- `--yaw-deg`：移动的绝对朝向角度（度）：0=东，90=南，180=西，270=北
- `--blocks`：移动格数，默认 `10`
- `--message`：要发送的聊天文本
- `--mock`：启用本地模拟模式（无需服务器，便于测试）

## 工作原理
1. Python 启动 `node bot.js` 并监听其标准输出；
2. `bot.js` 使用 `mineflayer`（或 Mock）初始化，`spawn` 后输出 `{ "event": "ready" }`；
3. Python 收到 `ready` 后可发送 `move` 与 `say` 指令，等待 `*_result` 事件；
4. 交互式命令行支持 `say / move / quit` 等常用操作。

## npm scripts
- `npm start`：启动真实 mineflayer 机器人（需服务器在线）
- `npm run mock`：启动本地模拟机器人（开发/联调）

## 常见问题
- Node 版本错误（EBADENGINE）：升级到 Node 22+ 后重试 `npm install`。
- 路径规划失败：`mineflayer-pathfinder` 可能因障碍/落差导致失败，查看 `move_result` 的 `error` 字段定位原因。
- Windows 控制台中文乱码：执行 `chcp 65001` 切换到 UTF-8。
- 服务器限制：部分服务器可能屏蔽 Bot 或限制移动/聊天。

## 版本与发布
- 当前分支：`main`
- 标签发布：`v0.1.0`（初始标记版本）
- Git 远程：`origin` → https://github.com/YJLi-new/MCAgent-TempTest.git

## 许可与致谢
- 本项目用于示例与学习用途。
- 致谢：
  - mineflayer: https://github.com/PrismarineJS/mineflayer
  - mineflayer-pathfinder: https://github.com/PrismarineJS/mineflayer-pathfinder

