# Minecraft Mineflayer 机器人（Python 驱动）

这个项目用 Python 作为入口，启动并驱动一个基于 Node.js 的 mineflayer 机器人，实现：
- 控制角色朝任意方向前进指定格数（默认 10 格）
- 在聊天框里发送指定文本

Python 进程与 Node 机器人之间通过标准输入/输出传递 JSON 指令。

## 功能概览
- 移动：支持绝对方向（north/south/east/west）与相对方向（forward/back/left/right），也支持按绝对朝向角度（yawDeg）移动。
- 聊天：向服务器聊天框发送一条指定消息。

## 目录结构
```
.
├─ main.py         # Python 启动器与示例 CLI
├─ bot.js          # Node 侧 mineflayer 机器人桥接（move/say/quit）
├─ package.json    # Node 依赖
├─ requirements.txt# Python 依赖（本项目无需三方库）
└─ README.md
```

## 环境要求
- Python 3.8+（无需额外第三方库）
- Node.js ≥ 22（mineflayer 及其依赖对 Node 版本要求较新）
  - 建议使用 nvm / nvm-windows 安装并切换至 Node 22+ 版本
- 已有可连接的 Minecraft 服务器（默认 `127.0.0.1:25565`）

## 安装
1) 安装 Node 依赖
```bash
npm install
```

2)（可选）安装 Python 依赖
```bash
pip install -r requirements.txt
```

## 运行示例
- 基本用法：连接本地服务器，向北移动 10 格，并发送一条消息
```bash
python main.py --host 127.0.0.1 --port 25565 --username Bot \
  --direction north --blocks 10 --message "你好，Minecraft！"
```

- 相对朝向移动：相对于当前面向前进 10 格
```bash
python main.py --username Bot --direction forward --message "go go go"
```

- 指定移动格数
```bash
python main.py --username Bot --direction east --blocks 12 --message "到位啦"
```

- 绝对朝向角度移动：0=向东，90=向南，180=向西，270=向北
```bash
python main.py --username Bot --yaw-deg 135 --blocks 10 --message "斜向走10格"
```

## 命令行参数（main.py）
- `--host`：服务器地址，默认 `127.0.0.1`
- `--port`：服务器端口，默认 `25565`
- `--username`：机器人用户名
- `--password`：可选，配合在线服鉴权使用
- `--auth`：可选，鉴权方式（如 `microsoft`）
- `--version`：可选，Minecraft 协议版本（不指定则由 mineflayer 自动检测）
- `--direction`：移动方向，`north|south|east|west|forward|back|left|right`（与 `--yaw-deg` 互斥）
- `--yaw-deg`：移动的绝对朝向角度，单位度（0=东，90=南，180=西，270=北）
- `--blocks`：移动的格数，默认 `10`
- `--message`：要在聊天框发送的文本

## 工作原理
- Python 启动 `node bot.js` 并监听其标准输出。
- `bot.js` 使用 `mineflayer` 连接服务器，并在 `spawn` 后输出 `{ "event": "ready" }`。
- Python 收到 `ready` 后，顺序发送两条指令：
  1) `{"type":"move", ...}`：使用 `mineflayer-pathfinder` 规划至目标坐标（当前位置沿给定方向移动 N 格，Y 取当前地面高度的整数层）
  2) `{"type":"say","message":"..."}`：发送聊天
- 收到 `move_result` / `say_result` 后，Python 发送 `{"type":"quit"}` 让机器人优雅退出。

## 在线服与鉴权说明
- 离线服：通常仅需 `--username` 即可加入。
- 在线服（微软账号）：尝试 `--auth microsoft`。不同环境可能需要额外登录流程与配置，请参考 mineflayer 文档。

## 注意事项 / 常见问题
- Node 版本：若安装依赖时出现 `EBADENGINE` 提示，请升级到 Node 22+ 再运行 `npm install`。
- 路径规划：`mineflayer-pathfinder` 可能因障碍/落差导致到达失败，控制台会输出 `move_result` 的失败原因。
- 服务器限制：部分服务器可能屏蔽机器人、限制移动或聊天。

## 许可证
本项目不包含开源许可证条款，仅用于示例与学习用途。

## 参考
- mineflayer: https://github.com/PrismarineJS/mineflayer
- mineflayer-pathfinder: https://github.com/PrismarineJS/mineflayer-pathfinder

