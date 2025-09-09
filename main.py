import argparse
import json
import os
import subprocess
import sys
import threading
import time


def read_lines(pipe, on_line):
    for raw in iter(pipe.readline, b""):
        try:
            line = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            line = raw.strip().decode(errors="ignore")
        if not line:
            continue
        on_line(line)


def main():
    parser = argparse.ArgumentParser(
        description="Python driver for mineflayer bot with interactive command loop.")
    parser.add_argument("--host", default="127.0.0.1", help="Minecraft server host")
    parser.add_argument("--port", type=int, default=25565, help="Minecraft server port")
    parser.add_argument("--username", default="Bot", help="Bot username")
    parser.add_argument("--password", default=None, help="Password (if needed)")
    parser.add_argument("--auth", default=None, help="Auth provider, e.g. microsoft (optional)")
    parser.add_argument("--version", default=None, help="Minecraft protocol version (optional)")

    parser.add_argument("--direction", default="north",
                        help="Direction to move: north|south|east|west|forward|back|left|right (or use --yaw-deg)")
    parser.add_argument("--yaw-deg", type=float, default=None,
                        help="Absolute yaw direction in degrees (0=east, 90=south, 180=west, 270=north)")
    parser.add_argument("--blocks", type=int, default=10, help="Blocks to move (default 10)")

    parser.add_argument("--message", default="你好，我是一个机器人",
                        help="Chat message to send (initial once)")

    parser.add_argument("--mock", action="store_true",
                        help="使用 bot 的本地模拟模式（无需真实服务器，便于快速测试）")

    args = parser.parse_args()

    node_cmd = [
        "node", "bot.js",
        "--host", str(args.host),
        "--port", str(args.port),
        "--username", str(args.username),
    ]
    if args.password:
        node_cmd += ["--password", str(args.password)]
    if args.auth:
        node_cmd += ["--auth", str(args.auth)]
    if args.version:
        node_cmd += ["--version", str(args.version)]
    if args.mock:
        node_cmd += ["--mock"]

    # Start Node bot bridge
    try:
        proc = subprocess.Popen(
            node_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
        )
    except FileNotFoundError as e:
        print("找不到 Node，可否先安装 Node.js 和 npm?", file=sys.stderr)
        raise e

    ready_event = threading.Event()
    move_done = threading.Event()
    say_done = threading.Event()

    # Store last results for commands so the interactive loop can show outcomes
    state = {
        "last_move": None,   # dict from bridge
        "last_say": None,    # dict from bridge
        "seen_quitting": False,
    }

    def handle_line(line: str):
        # Print raw bridge logs for visibility
        try:
            data = json.loads(line)
        except Exception:
            print(line)
            return
        evt = data.get("event")
        if evt == "ready":
            ready_event.set()
            print("[bridge] ready")
        elif evt == "move_result":
            ok = data.get("ok")
            state["last_move"] = data
            print(f"[move] {'OK' if ok else 'FAIL'}: {data}")
            move_done.set()
        elif evt == "say_result":
            ok = data.get("ok")
            state["last_say"] = data
            print(f"[say] {'OK' if ok else 'FAIL'}: {data}")
            say_done.set()
        elif evt in ("kicked", "error", "fatal", "command_error", "bad_command"):
            print(f"[bridge:{evt}] {data}")
        elif evt == "quitting":
            state["seen_quitting"] = True
            print("[bridge] quitting")
        else:
            # Pass-through misc logs
            print(line)

    t = threading.Thread(target=read_lines, args=(proc.stdout, handle_line), daemon=True)
    t.start()

    print("等待 bot 进入游戏……")
    if not ready_event.wait(timeout=60):
        print("等待超时：bot 未进入游戏。请检查服务器地址/端口/版本/鉴权。", file=sys.stderr)
        try:
            proc.kill()
        except Exception:
            pass
        sys.exit(1)

    # Helper: send a command and wait for its matching result
    def send_and_wait(cmd_obj: dict, expect: str, timeout: float) -> bool:
        line = json.dumps(cmd_obj) + "\n"
        try:
            # Clear corresponding event first
            if expect == "move_result":
                move_done.clear()
            elif expect == "say_result":
                say_done.clear()
        except Exception:
            pass
        proc.stdin.write(line.encode("utf-8"))
        proc.stdin.flush()
        if expect == "move_result":
            ok = move_done.wait(timeout=timeout)
            return bool(ok)
        elif expect == "say_result":
            ok = say_done.wait(timeout=timeout)
            return bool(ok)
        else:
            return True

    # Initial demo commands (kept for compatibility), then enter REPL
    # Move
    init_move = {
        "type": "move",
        "direction": args.direction,
        "blocks": int(args.blocks),
    }
    if args.yaw_deg is not None:
        init_move.pop("direction", None)
        init_move["yawDeg"] = float(args.yaw_deg)
    send_and_wait(init_move, "move_result", timeout=300)

    # Say
    init_say = {"type": "say", "message": args.message}
    send_and_wait(init_say, "say_result", timeout=30)

    # Interactive loop: process one command at a time and only exit on quit
    print("进入交互模式：输入命令，或输入 help 查看帮助。")
    def show_help():
        print("支持命令：")
        print("  say <text>             # 发送聊天消息")
        print("  move <dir> [blocks]    # 绝对/相对方向移动：north/south/east/west/forward/back/left/right")
        print("  move yaw <deg> [blocks]# 指定绝对朝向角度移动：0=东, 90=南, 180=西, 270=北")
        print("  quit / exit            # 退出机器人并结束程序")

    try:
        while True:
            try:
                user = input("> ").strip()
            except EOFError:
                user = "quit"
            if not user:
                continue
            low = user.lower()
            if low in ("quit", "exit"):
                try:
                    proc.stdin.write((json.dumps({"type": "quit"}) + "\n").encode("utf-8"))
                    proc.stdin.flush()
                except Exception:
                    pass
                break
            if low in ("help", "h", "?"):
                show_help()
                continue

            # say command
            if low.startswith("say ") or low == "say":
                msg = user[3:].strip() if len(user) > 3 else ""
                if msg.startswith(" "):
                    msg = msg.strip()
                if not msg:
                    print("用法：say <text>")
                    continue
                ok = send_and_wait({"type": "say", "message": msg}, "say_result", timeout=30)
                if not ok:
                    print("[say] 等待结果超时。")
                continue

            # move command
            if low.startswith("move"):
                tokens = user.split()
                if len(tokens) < 2:
                    print("用法：move <north|south|east|west|forward|back|left|right> [blocks]\n或：  move yaw <deg> [blocks]")
                    continue
                blocks = None
                cmd = {"type": "move"}
                if tokens[1].lower() == "yaw":
                    if len(tokens) < 3:
                        print("用法：move yaw <deg> [blocks]")
                        continue
                    try:
                        cmd["yawDeg"] = float(tokens[2])
                    except ValueError:
                        print("角度必须是数字，例如：move yaw 270 10")
                        continue
                    if len(tokens) >= 4:
                        try:
                            blocks = int(tokens[3])
                        except ValueError:
                            print("blocks 必须是整数")
                            continue
                else:
                    cmd["direction"] = tokens[1].lower()
                    if len(tokens) >= 3:
                        try:
                            blocks = int(tokens[2])
                        except ValueError:
                            print("blocks 必须是整数")
                            continue
                cmd["blocks"] = int(blocks) if blocks is not None else int(args.blocks)
                ok = send_and_wait(cmd, "move_result", timeout=600)
                if not ok:
                    print("[move] 等待结果超时。")
                continue

            print("未知命令，输入 help 查看帮助。")
    finally:
        # If user broke out, ensure process ends
        # Wait a moment for bridge to close itself
        for _ in range(10):
            if state.get("seen_quitting"):
                break
            time.sleep(0.1)
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()

