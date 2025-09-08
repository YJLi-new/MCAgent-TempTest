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
        description="Python driver for mineflayer bot: move 10 blocks and say a message.")
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

    parser.add_argument("--message", default="你好，我是一个机器人！",
                        help="Chat message to send")

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
            print(f"[move] {'OK' if ok else 'FAIL'}: {data}")
            move_done.set()
        elif evt == "say_result":
            ok = data.get("ok")
            print(f"[say] {'OK' if ok else 'FAIL'}: {data}")
            say_done.set()
        elif evt in ("kicked", "error", "fatal", "command_error", "bad_command"):
            print(f"[bridge:{evt}] {data}")
        elif evt == "quitting":
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

    # Send move command
    cmd_move = {
        "type": "move",
        "direction": args.direction,
        "blocks": int(args.blocks),
    }
    if args.yaw_deg is not None:
        cmd_move.pop("direction", None)
        cmd_move["yawDeg"] = float(args.yaw_deg)

    proc.stdin.write((json.dumps(cmd_move) + "\n").encode("utf-8"))
    proc.stdin.flush()

    # Send say command
    cmd_say = {"type": "say", "message": args.message}
    proc.stdin.write((json.dumps(cmd_say) + "\n").encode("utf-8"))
    proc.stdin.flush()

    # Wait for both to complete (with generous timeouts)
    move_done.wait(timeout=120)
    say_done.wait(timeout=30)

    # Quit the bot cleanly
    try:
        proc.stdin.write((json.dumps({"type": "quit"}) + "\n").encode("utf-8"))
        proc.stdin.flush()
    except Exception:
        pass

    # Allow some time to shutdown
    time.sleep(1.0)
    try:
        proc.terminate()
    except Exception:
        pass


if __name__ == "__main__":
    main()
