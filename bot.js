// Node.js bridge that exposes minimal commands to control a mineflayer bot.
// Reads JSON lines from stdin and writes JSON lines to stdout.

const readline = require('readline');
const { EventEmitter } = require('events');

function log(obj) {
  try {
    process.stdout.write(JSON.stringify(obj) + "\n");
  } catch (_) {
    // ignore logging errors
  }
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) continue;
    const key = a.slice(2);
    const val = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    out[key] = val;
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const useMock = Boolean(args.mock);

  let bot;
  let MovementsCtor = null;
  let GoalBlockCtor = null;
  if (useMock) {
    // Lightweight mock bot for local testing without a server
    const emitter = new EventEmitter();
    let position = { x: 0, y: 64, z: 0 };
    let yaw = 0; // radians, 0=east
    bot = {
      once: (...a) => emitter.once(...a),
      on: (...a) => emitter.on(...a),
      emit: (...a) => emitter.emit(...a),
      loadPlugin: () => {},
      entity: {
        get position() { return position; },
        set position(v) { position = v; },
        get yaw() { return yaw; },
        set yaw(v) { yaw = v; }
      },
      chat: (msg) => {
        log({ event: 'chat', message: String(msg) });
      },
      pathfinder: {
        setMovements: () => {},
        goto: (goal) => new Promise((resolve) => {
          // Simulate walking to the goal with a tiny delay
          setTimeout(() => {
            position = { x: goal.x, y: goal.y, z: goal.z };
            resolve();
          }, 50);
        })
      },
      end: () => {}
    };
    // Defer ready event to simulate spawn
    setTimeout(() => bot.emit('spawn'), 30);
  } else {
    // Real mineflayer bot
    const mineflayer = require('mineflayer');
    const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
    MovementsCtor = Movements;
    GoalBlockCtor = goals.GoalBlock;

    const host = args.host || '127.0.0.1';
    const port = args.port ? Number(args.port) : 25565;
    const username = args.username || 'Bot';
    const password = args.password || undefined;
    const auth = args.auth || undefined; // e.g., 'microsoft'
    const version = args.version || undefined; // let mineflayer autodetect if not provided

    bot = mineflayer.createBot({ host, port, username, password, auth, version });
    bot.loadPlugin(pathfinder);

    bot.on('kicked', (reason) => {
      log({ event: 'kicked', reason });
    });
    bot.on('error', (err) => {
      log({ event: 'error', message: String(err && err.message || err) });
    });
  }

  // Common spawn handler for both real and mock modes
  bot.once('spawn', () => {
    try {
      if (!useMock && MovementsCtor) {
        const mcData = require('minecraft-data')(bot.version);
        const movements = new MovementsCtor(bot, mcData);
        bot.pathfinder.setMovements(movements);
      }
    } catch (_) {
      // ignore
    }
    log({ event: 'ready' });
  });

  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

  rl.on('line', async (line) => {
    let cmd;
    try {
      cmd = JSON.parse(line);
    } catch (e) {
      return log({ event: 'bad_command', error: 'invalid_json' });
    }

    if (!cmd || typeof cmd !== 'object') return log({ event: 'bad_command', error: 'not_object' });

    try {
      switch (cmd.type) {
        case 'say':
          if (!cmd.message) return log({ event: 'say_result', ok: false, error: 'missing_message' });
          bot.chat(String(cmd.message));
          return log({ event: 'say_result', ok: true });

        case 'move': {
          const blocks = typeof cmd.blocks === 'number' && cmd.blocks > 0 ? cmd.blocks : 10;
          const pos = bot.entity.position;
          const cx = pos.x, cy = pos.y, cz = pos.z;
          const y = Math.floor(cy);

          // Vector from direction or yaw
          let vx = 0, vz = 0;
          const dir = cmd.direction && String(cmd.direction).toLowerCase();
          if (typeof cmd.yawDeg === 'number') {
            const yaw = (cmd.yawDeg * Math.PI) / 180;
            vx = -Math.sin(yaw);
            vz = Math.cos(yaw);
          } else if (dir === 'north') { vz = -1; }
          else if (dir === 'south') { vz = 1; }
          else if (dir === 'east') { vx = 1; }
          else if (dir === 'west') { vx = -1; }
          else if (dir === 'forward' || dir === 'back' || dir === 'left' || dir === 'right') {
            const yaw = bot.entity.yaw || 0;
            const fx = -Math.sin(yaw);
            const fz = Math.cos(yaw);
            if (dir === 'forward') { vx = fx; vz = fz; }
            if (dir === 'back') { vx = -fx; vz = -fz; }
            if (dir === 'left') { vx = -fz; vz = fx; }
            if (dir === 'right') { vx = fz; vz = -fx; }
          } else {
            return log({ event: 'move_result', ok: false, error: 'unknown_direction' });
          }

          // Normalize vector then scale to block count
          const len = Math.hypot(vx, vz) || 1;
          vx /= len; vz /= len;
          const tx = Math.round(cx + vx * blocks);
          const tz = Math.round(cz + vz * blocks);

          if (!bot.pathfinder) {
            return log({ event: 'move_result', ok: false, error: 'pathfinder_unavailable' });
          }
          try {
            // Resolve GoalBlock ctor in both real and mock modes
            const GB = GoalBlockCtor || (useMock ? (class GB { constructor(x,y,z){ this.x=x; this.y=y; this.z=z; } }) : require('mineflayer-pathfinder').goals.GoalBlock);
            await bot.pathfinder.goto(new GB(tx, y, tz));
            return log({ event: 'move_result', ok: true, target: { x: tx, y, z: tz } });
          } catch (err) {
            return log({ event: 'move_result', ok: false, error: String(err && err.message || err) });
          }
        }

        case 'quit': {
          log({ event: 'quitting' });
          try { bot.end(); } catch (_) {}
          try { rl.close(); } catch (_) {}
          return;
        }

        default:
          return log({ event: 'bad_command', error: 'unknown_type' });
      }
    } catch (err) {
      return log({ event: 'command_error', error: String(err && err.message || err) });
    }
  });
}

main().catch((e) => {
  log({ event: 'fatal', error: String(e && e.message || e) });
  process.exitCode = 1;
});
