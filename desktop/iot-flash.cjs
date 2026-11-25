'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const os = require('node:os');
const { spawn, spawnSync } = require('node:child_process');
const { StringDecoder } = require('node:string_decoder');
const core = require('./core.cjs');
const iotNvs = require('./iot-nvs.cjs');
const { windowsPowerShell } = require('./ai-tools.cjs');

const SUPPORTED_PLATFORMS = new Set(['linux', 'win32']);

function fail(message) {
  throw new Error(message);
}

function readTrimmed(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8').trim();
  } catch {
    return '';
  }
}

function isValidSerialPort(port, platform = process.platform) {
  if (typeof port !== 'string') return false;
  if (platform === 'win32') return /^COM\d{1,3}$/i.test(port.trim());
  return /^\/dev\/tty(ACM|USB)\d+$/.test(port);
}

function normalizeSerialPort(port, platform = process.platform) {
  if (!isValidSerialPort(port, platform)) {
    fail(platform === 'win32'
      ? 'Selecciona un puerto serie válido de Windows (por ejemplo COM3).'
      : 'Selecciona un puerto USB serie válido (/dev/ttyACM* o /dev/ttyUSB*).');
  }
  return platform === 'win32' ? port.trim().toUpperCase() : port;
}

function resolveIotRoot(rootDir) {
  const candidates = [
    path.join(rootDir, 'iot'),
    path.resolve(__dirname, '..', 'iot'),
  ];
  for (const dir of candidates) {
    if (fs.existsSync(path.join(dir, 'boards.json'))) return dir;
  }
  return candidates[0];
}

function resolveWinSerialScript(rootDir) {
  const candidates = [
    path.join(rootDir || '', 'windows-iot-serial.ps1'),
    path.join(__dirname, 'windows-iot-serial.ps1'),
  ];
  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  return candidates[1];
}

function candidateFirmwareDirs(board, { rootDir, userDataDir, customDir } = {}) {
  const dirs = [];
  const profile = board.firmware_profile || board.id;
  if (customDir && typeof customDir === 'string') dirs.push(customDir);
  if (process.env.AGUJA_IOT_PREBUILT_DIR) {
    dirs.push(path.join(process.env.AGUJA_IOT_PREBUILT_DIR, profile));
    dirs.push(path.join(process.env.AGUJA_IOT_PREBUILT_DIR, board.id));
  }
  const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
  if (board.prebuilt_dir) {
    dirs.push(path.resolve(path.dirname(iotRoot), board.prebuilt_dir));
  }
  dirs.push(path.join(iotRoot, 'prebuilt', profile));
  dirs.push(path.join(iotRoot, 'prebuilt', board.id));
  if (userDataDir) {
    dirs.push(path.join(userDataDir, 'iot-firmware', profile));
    dirs.push(path.join(userDataDir, 'iot-firmware', board.id));
  }
  dirs.push(path.join(os.homedir(), '.local', 'share', 'aguja-iot', 'prebuilt', profile));
  dirs.push(path.join(os.homedir(), '.local', 'share', 'aguja-iot', 'prebuilt', board.id));
  return [...new Set(dirs)];
}

function inspectFirmwareDir(dirPath, board) {
  if (!dirPath || !fs.existsSync(dirPath)) return null;
  const manifestPath = path.join(dirPath, 'manifest.json');
  if (!fs.existsSync(manifestPath)) return null;
  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  } catch {
    return null;
  }
  if (manifest.schema !== 1 || !manifest.files || typeof manifest.files !== 'object') return null;
  if (board && manifest.chip && manifest.chip !== board.chip) return null;

  const required = ['bootloader.bin', 'partition-table.bin', 'ota_data_initial.bin', 'aguja_iot.bin'];
  const segments = [];
  for (const name of required) {
    const entry = manifest.files[name];
    if (!entry || typeof entry.offset !== 'string' || !/^0x[0-9a-fA-F]+$/.test(entry.offset)) {
      return null;
    }
    const fullPath = path.join(dirPath, name);
    if (!fs.existsSync(fullPath)) return null;
    const stat = fs.lstatSync(fullPath);
    if (!stat.isFile() || stat.isSymbolicLink()) return null;
    segments.push({
      name,
      offset: entry.offset,
      path: fullPath,
      bytes: stat.size,
      sha256: typeof entry.sha256 === 'string' ? entry.sha256.toLowerCase() : '',
    });
  }
  return {
    dir: dirPath,
    version: String(manifest.version || '0.0.0'),
    chip: String(manifest.chip || board?.chip || ''),
    flash_mode: String(manifest.flash_mode || board?.flash_mode || 'dio'),
    flash_freq: String(manifest.flash_freq || board?.flash_freq || '80m'),
    flash_size: String(manifest.flash_size || board?.flash_size || 'detect'),
    nvs_offset: String(manifest.nvs_offset || board?.flash_offsets?.nvs || '0x9000'),
    nvs_size: Number(manifest.nvs_size || 49152),
    segments,
  };
}

function loadBoards({ rootDir, userDataDir, customFirmwareDirs = {} } = {}) {
  const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
  const manifestPath = path.join(iotRoot, 'boards.json');
  if (!fs.existsSync(manifestPath)) {
    fail('No se encontró el catálogo de placas IoT (iot/boards.json).');
  }
  const raw = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const boards = (raw.boards || []).map((board) => {
    let bundle = null;
    for (const dir of candidateFirmwareDirs(board, { rootDir, userDataDir, customDir: customFirmwareDirs[board.id] })) {
      bundle = inspectFirmwareDir(dir, board);
      if (bundle) break;
    }
    return {
      ...board,
      firmwareReady: Boolean(bundle),
      firmwareVersion: bundle?.version || null,
      firmwareDir: bundle?.dir || null,
      firmwareSegments: bundle
        ? [
            ...bundle.segments.map((s) => ({
              offset: s.offset,
              name: s.name,
              bytes: s.bytes,
              sha256Short: s.sha256 ? s.sha256.slice(0, 12) : '',
            })),
            {
              offset: bundle.nvs_offset,
              name: 'nvs_private.bin (generada al vuelo)',
              bytes: bundle.nvs_size,
              sha256Short: 'dinámica',
            },
          ].sort((a, b) => parseInt(a.offset, 16) - parseInt(b.offset, 16))
        : [],
    };
  });
  const families = [...new Set(boards.map((b) => b.family).filter(Boolean))];
  return {
    schemaVersion: raw.schema_version || 1,
    nvsProvisioning: raw.nvs_provisioning || {},
    families,
    boards,
  };
}

function normalizeChipName(rawChip) {
  const s = String(rawChip || '').toUpperCase();
  for (const key of ['ESP32-S3', 'ESP32-C6', 'ESP32-C3', 'ESP32-S2', 'ESP32-C2', 'ESP32-H2']) {
    if (s.includes(key)) return key.replace('-', '').toLowerCase();
  }
  if (s.includes('ESP32')) return 'esp32';
  return '';
}

function parseEsptoolChipInfo(lines) {
  const info = {
    chip: '',
    chip_normalized: '',
    features: '',
    mac: '',
    flash_size: '',
    flash_mb: 0,
    psram_mb: 0,
  };
  for (const line of lines || []) {
    let m = /Chip type:\s*(.+)$/i.exec(line);
    if (m) {
      info.chip = m[1].trim();
      info.chip_normalized = normalizeChipName(info.chip);
    }
    m = /Features:\s*(.+)$/i.exec(line);
    if (m) {
      info.features = m[1].trim();
      const mp = /PSRAM\s*(\d+)\s*MB/i.exec(info.features);
      if (mp) info.psram_mb = Number(mp[1]);
      else if (/PSRAM/i.test(info.features)) info.psram_mb = 2;
    }
    m = /MAC:\s*([0-9a-fA-F:]{17})/i.exec(line);
    if (m) info.mac = m[1].toLowerCase();
    m = /Detected flash size:\s*(\S+)/i.exec(line);
    if (m) {
      info.flash_size = m[1].trim();
      const mf = /^(\d+)\s*MB$/i.exec(info.flash_size);
      if (mf) info.flash_mb = Number(mf[1]);
    }
  }
  return info;
}

function flashSizeBytes(label) {
  const m = /^(\d+)\s*MB$/i.exec(String(label || '').trim());
  if (!m) return 4 * 1024 * 1024;
  return Number(m[1]) * 1024 * 1024;
}

function matchBoardFromProbe(probeInfo, portMeta, boards) {
  const chip = String(probeInfo?.chip_normalized || '').toLowerCase();
  if (!chip) return null;
  const flashMb = Number(probeInfo?.flash_mb || 0);
  const hasPsram = Number(probeInfo?.psram_mb || 0) > 0;
  const vid = String(portMeta?.vid || '').toLowerCase();

  let best = null;
  let bestScore = -1;
  for (const board of boards) {
    if (board.status === 'planned') continue;
    if (String(board.chip || '').toLowerCase() !== chip) continue;
    const rule = board.auto_match || {};
    let score = Number(rule.priority || 50);
    if (typeof rule.psram === 'boolean') {
      score += rule.psram === hasPsram ? 40 : -35;
    }
    if (Array.isArray(rule.flash_mb) && flashMb > 0) {
      score += rule.flash_mb.includes(flashMb) ? 30 : -10;
    }
    if (rule.vid && vid) {
      score += String(rule.vid).toLowerCase() === vid ? 25 : -10;
    } else if (vid && Array.isArray(board.usb_ids) && board.usb_ids.some((u) => String(u.vid).toLowerCase() === vid)) {
      score += 10;
    }
    if (board.firmwareReady) score += 5;
    if (score > bestScore) {
      bestScore = score;
      best = board;
    }
  }
  if (!best) return null;
  return {
    boardId: best.id,
    boardName: best.name,
    family: best.family || best.chip.toUpperCase(),
    firmwareReady: Boolean(best.firmwareReady),
  };
}

function matchBoardIds(vid, pid, boards) {
  const v = String(vid || '').toLowerCase();
  const p = String(pid || '').toLowerCase();
  if (!v || !p) return [];
  return boards
    .filter((b) => Array.isArray(b.usb_ids) && b.usb_ids.some((u) => String(u.vid).toLowerCase() === v && String(u.pid).toLowerCase() === p))
    .map((b) => b.id);
}

function sortPorts(ports) {
  ports.sort((a, b) => {
    const scoreA = (a.matchedBoardIds.length ? 2 : 0) + (a.accessible ? 1 : 0);
    const scoreB = (b.matchedBoardIds.length ? 2 : 0) + (b.accessible ? 1 : 0);
    if (scoreB !== scoreA) return scoreB - scoreA;
    return a.path.localeCompare(b.path, undefined, { numeric: true });
  });
  return ports;
}

function listLinuxSerialPorts(boards = [], { sysClassTty = '/sys/class/tty', devDir = '/dev', byIdDir = '/dev/serial/by-id' } = {}) {
  if (!fs.existsSync(sysClassTty)) return [];
  const byIdMap = new Map();
  try {
    for (const name of fs.readdirSync(byIdDir)) {
      const full = path.join(byIdDir, name);
      const resolved = fs.realpathSync(full);
      byIdMap.set(resolved, full);
    }
  } catch {}

  const ports = [];
  for (const name of fs.readdirSync(sysClassTty)) {
    if (!/^tty(ACM|USB)\d+$/.test(name)) continue;
    const devPath = path.join(devDir, name);
    if (!fs.existsSync(devPath)) continue;

    let cur = path.join(sysClassTty, name, 'device');
    try { cur = fs.realpathSync(cur); } catch {}
    let vid = '', pid = '', product = '', manufacturer = '', serial = '';
    for (let depth = 0; depth < 6 && cur && cur !== '/'; depth++) {
      const v = readTrimmed(path.join(cur, 'idVendor'));
      const p = readTrimmed(path.join(cur, 'idProduct'));
      if (v && p) {
        vid = v.toLowerCase();
        pid = p.toLowerCase();
        product = readTrimmed(path.join(cur, 'product'));
        manufacturer = readTrimmed(path.join(cur, 'manufacturer'));
        serial = readTrimmed(path.join(cur, 'serial'));
        break;
      }
      cur = path.dirname(cur);
    }

    let accessible = false;
    try {
      fs.accessSync(devPath, fs.constants.R_OK | fs.constants.W_OK);
      accessible = true;
    } catch {}

    ports.push({
      path: devPath,
      name,
      byId: byIdMap.get(devPath) || '',
      vid,
      pid,
      usbId: vid && pid ? `${vid}:${pid}` : '',
      product: product || 'USB Serial',
      manufacturer,
      serial,
      accessible,
      matchedBoardIds: matchBoardIds(vid, pid, boards),
    });
  }

  return sortPorts(ports);
}

function parseWindowsPortsOutput(stdout, boards = []) {
  const trimmed = String(stdout || '').replace(/^\ufeff/, '').trim();
  if (!trimmed) return [];
  let parsed = null;
  for (const line of trimmed.split(/\r?\n/).reverse()) {
    try {
      const obj = JSON.parse(line);
      if (obj && typeof obj.ok === 'boolean') {
        parsed = obj;
        break;
      }
    } catch {}
  }
  const rawList = Array.isArray(parsed?.ports) ? parsed.ports : (parsed?.ports ? [parsed.ports] : []);
  const ports = rawList
    .filter((p) => p && typeof p.path === 'string' && /^COM\d{1,3}$/i.test(p.path))
    .map((p) => {
      const vid = String(p.vid || '').toLowerCase();
      const pid = String(p.pid || '').toLowerCase();
      const com = p.path.toUpperCase();
      return {
        path: com,
        name: com,
        byId: String(p.byId || ''),
        vid,
        pid,
        usbId: vid && pid ? `${vid}:${pid}` : '',
        product: String(p.product || 'USB Serial'),
        manufacturer: String(p.manufacturer || ''),
        serial: String(p.serial || ''),
        accessible: p.accessible !== false,
        matchedBoardIds: matchBoardIds(vid, pid, boards),
      };
    });
  return sortPorts(ports);
}

function runProcessText(command, args, { timeoutMs = 15000 } = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
    let stdout = '';
    let stderr = '';
    let settled = false;
    const outDec = new StringDecoder('utf8');
    const errDec = new StringDecoder('utf8');
    const finish = (err, val) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      err ? reject(err) : resolve(val);
    };
    const timer = setTimeout(() => {
      proc.kill('SIGTERM');
      finish(new Error('Tiempo de espera agotado al consultar puertos serie de Windows.'));
    }, timeoutMs);
    proc.stdout.on('data', (d) => { stdout += outDec.write(d); });
    proc.stderr.on('data', (d) => { stderr += errDec.write(d); });
    proc.on('error', (e) => finish(e));
    proc.on('close', (code) => {
      stdout += outDec.end();
      stderr += errDec.end();
      if (code !== 0) return finish(new Error(stderr.trim() || `PowerShell exit ${code}`));
      finish(null, stdout);
    });
  });
}

async function listWindowsSerialPorts(boards = [], { rootDir, scriptPath = null, execText = runProcessText } = {}) {
  const ps1 = scriptPath || resolveWinSerialScript(rootDir);
  if (!fs.existsSync(ps1)) return [];
  try {
    const stdout = await execText(
      windowsPowerShell(),
      ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', ps1, '-Action', 'list-ports'],
      { timeoutMs: 12000 },
    );
    return parseWindowsPortsOutput(stdout, boards);
  } catch {
    return [];
  }
}

async function listSerialPorts(boards = [], options = {}) {
  const platform = options.platform || process.platform;
  if (platform === 'linux') return listLinuxSerialPorts(boards, options);
  if (platform === 'win32') return listWindowsSerialPorts(boards, options);
  return [];
}

async function fetchControlNoiseKey(controlHostOrUrl, { getHTTPS = core.getHTTPS } = {}) {
  const host = iotNvs.normalizeControlHost(controlHostOrUrl);
  const url = `https://${host}/key?v=131`;
  const body = await getHTTPS(url, 32768, 12000);
  const rawKey = typeof body?.PublicKey === 'string'
    ? body.PublicKey
    : typeof body?.publicKey === 'string'
      ? body.publicKey
      : '';
  const hex = rawKey.replace(/^mkey:/i, '').trim().toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(hex)) {
    fail('El servidor no devolvió una clave Noise válida en /key?v=131.');
  }
  return { host, noisePubkeyHex: hex };
}

function findEsptoolBinary({ rootDir, userDataDir, platform = process.platform } = {}) {
  const exe = platform === 'win32' ? 'esptool.exe' : 'esptool';
  const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
  const candidates = [];
  if (process.env.AGUJA_IOT_ESPTOOL) candidates.push(process.env.AGUJA_IOT_ESPTOOL);
  candidates.push(
    path.join(iotRoot, 'bin', platform, exe),
    path.join(iotRoot, 'bin', exe),
  );
  if (userDataDir) {
    candidates.push(path.join(userDataDir, 'iot-tools', exe));
  }
  for (const p of candidates) {
    if (p && fs.existsSync(p)) {
      try {
        const st = fs.lstatSync(p);
        if (st.isFile() && !st.isSymbolicLink()) return p;
      } catch {}
    }
  }
  // Check PATH for standalone esptool binary
  const pathEnv = process.env.PATH || process.env.Path || '';
  for (const dir of pathEnv.split(path.delimiter).filter(Boolean)) {
    const full = path.join(dir, exe);
    if (fs.existsSync(full)) return full;
  }
  return null;
}

function findPythonWithEsptool({ platform = process.platform } = {}) {
  const candidates = [];
  if (process.env.AGUJA_IOT_PYTHON) candidates.push(process.env.AGUJA_IOT_PYTHON);

  if (platform === 'win32') {
    const localApp = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
    candidates.push(path.join(localApp, 'aguja-iot', 'venv', 'Scripts', 'python.exe'));
    const pyRoot = path.join(localApp, 'Programs', 'Python');
    if (fs.existsSync(pyRoot)) {
      try {
        for (const name of fs.readdirSync(pyRoot).sort().reverse()) {
          candidates.push(path.join(pyRoot, name, 'python.exe'));
        }
      } catch {}
    }
    candidates.push('python.exe', 'python');
  } else {
    const espressifEnvRoot = path.join(os.homedir(), '.espressif', 'python_env');
    if (fs.existsSync(espressifEnvRoot)) {
      try {
        for (const name of fs.readdirSync(espressifEnvRoot).sort().reverse()) {
          candidates.push(path.join(espressifEnvRoot, name, 'bin', 'python'));
        }
      } catch {}
    }
    candidates.push(
      path.join(os.homedir(), '.local', 'share', 'aguja-iot', 'venv', 'bin', 'python'),
      '/tmp/esp_probe_venv/bin/python',
      '/usr/bin/python3',
      'python3',
    );
  }

  for (const py of candidates) {
    if (!['python3', 'python', 'python.exe'].includes(py) && !fs.existsSync(py)) continue;
    try {
      const res = spawnSync(py, ['-c', 'import esptool, serial'], {
        timeout: 4000,
        stdio: 'ignore',
        windowsHide: true,
      });
      if (res.status === 0) return py;
    } catch {}
  }
  return null;
}

function runEsptoolDirect(binPath, argv, { stage = 'write', label = 'Ejecutando esptool', progress = () => {}, timeoutMs = 5 * 60 * 1000 } = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(binPath, argv, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
    let pending = '';
    let stderr = '';
    const lines = [];
    let lastPct = -1;
    let settled = false;
    const outDec = new StringDecoder('utf8');
    const errDec = new StringDecoder('utf8');

    const finish = (err, val) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      err ? reject(err) : resolve(val);
    };

    const timer = setTimeout(() => {
      proc.kill('SIGTERM');
      finish(new Error('La operación con esptool tardó demasiado. Comprueba el cable USB y el puerto COM.'));
    }, timeoutMs);

    const flushLines = () => {
      let sep;
      while ((sep = pending.search(/[\r\n]/)) >= 0) {
        const line = pending.slice(0, sep).trim();
        pending = pending.slice(sep + 1);
        if (!line) continue;
        lines.push(line);
        const m = /\((\d{1,3})\s*%\)/.exec(line);
        if (m) {
          const pct = Math.max(0, Math.min(100, Number(m[1])));
          if (pct !== lastPct) {
            lastPct = pct;
            progress('iot-flash', { stage, message: `${label} (${pct}%)`, done: pct, total: 100 });
          }
        }
      }
    };

    proc.stdout.on('data', (chunk) => {
      pending += outDec.write(chunk);
      flushLines();
    });
    proc.stderr.on('data', (chunk) => {
      stderr += errDec.write(chunk);
      if (stderr.length > 512 * 1024) stderr = stderr.slice(-512 * 1024);
    });
    proc.on('error', () => finish(new Error('No se pudo ejecutar esptool. Comprueba que esptool.exe esté disponible.')));
    proc.on('close', (code) => {
      pending += outDec.end();
      stderr += errDec.end();
      if (pending.trim()) lines.push(pending.trim());
      if (code !== 0) {
        const tail = [...lines.slice(-5), stderr.trim()].filter(Boolean).join(' ').slice(0, 280);
        return finish(new Error(tail || `esptool finalizó con código ${code}.`));
      }
      finish(null, lines);
    });
  });
}

async function verifyWindowsSerialBoot(port, { timeoutSec = 24, rootDir, progress = () => {}, scriptPath = null } = {}) {
  const ps1 = scriptPath || resolveWinSerialScript(rootDir);
  if (!fs.existsSync(ps1)) {
    return { booted: false, warning: 'Falta el verificador serie de Windows (windows-iot-serial.ps1).' };
  }
  progress('iot-flash', { stage: 'boot', message: `Verificando arranque y estado en ${port}…`, done: 20, total: 100 });
  try {
    const stdout = await runProcessText(
      windowsPowerShell(),
      [
        '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', ps1,
        '-Action', 'verify-boot',
        '-Port', port,
        '-TimeoutSeconds', String(timeoutSec),
      ],
      { timeoutMs: (timeoutSec + 10) * 1000 },
    );
    for (const line of stdout.trim().split(/\r?\n/).reverse()) {
      try {
        const obj = JSON.parse(line);
        if (obj && obj.ok && obj.boot) {
          progress('iot-flash', {
            stage: 'boot',
            message: obj.boot.vpn_ip
              ? `Nodo en línea en tailnet (${obj.boot.vpn_ip})`
              : obj.boot.booted
                ? 'Firmware arrancado y verificado por puerto COM.'
                : 'Grabación completada; sin respuesta serie en el tiempo límite.',
            done: 100,
            total: 100,
          });
          return obj.boot;
        }
      } catch {}
    }
    return { booted: false, warning: 'No se pudo leer el estado de arranque por puerto COM.' };
  } catch (err) {
    return { booted: false, warning: err.message };
  }
}

function runIotHelper(pythonBin, scriptPath, job, { progress = () => {}, timeoutMs = 5 * 60 * 1000 } = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(pythonBin, [scriptPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    let pending = '';
    let settled = false;
    const outDec = new StringDecoder('utf8');
    const errDec = new StringDecoder('utf8');

    const done = (err, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      err ? reject(err) : resolve(value);
    };

    const timer = setTimeout(() => {
      proc.kill('SIGTERM');
      done(new Error('La grabación IoT tardó demasiado. Comprueba el cable USB y vuelve a intentarlo.'));
    }, timeoutMs);

    proc.stdout.on('data', (chunk) => {
      const text = outDec.write(chunk);
      stdout += text;
      pending += text;
      let nl;
      while ((nl = pending.indexOf('\n')) >= 0) {
        const line = pending.slice(0, nl).trim();
        pending = pending.slice(nl + 1);
        if (!line) continue;
        try {
          const obj = JSON.parse(line);
          if (obj.type === 'progress') {
            progress('iot-flash', {
              stage: obj.stage,
              message: String(obj.message || 'Grabando microcontrolador…').slice(0, 160),
              ...(typeof obj.percent === 'number' ? { done: obj.percent, total: 100 } : {}),
            });
          }
        } catch {}
      }
      if (stdout.length > 4 * 1024 * 1024) {
        proc.kill('SIGTERM');
        done(new Error('La respuesta del grabador IoT superó el límite seguro.'));
      }
    });

    proc.stderr.on('data', (chunk) => {
      stderr += errDec.write(chunk);
      if (stderr.length > 1024 * 1024) stderr = stderr.slice(-1024 * 1024);
    });

    proc.on('error', () => done(new Error('No se pudo ejecutar el grabador IoT de Python.')));
    proc.on('close', (code) => {
      stdout += outDec.end();
      stderr += errDec.end();
      let finalObj = null;
      for (const line of stdout.trim().split('\n').reverse()) {
        try {
          const parsed = JSON.parse(line);
          if (typeof parsed.ok === 'boolean') {
            finalObj = parsed;
            break;
          }
        } catch {}
      }
      if (code !== 0 || !finalObj || finalObj.ok === false) {
        return done(new Error(finalObj?.error || 'No se completó la grabación del microcontrolador. Revisa permisos del puerto serie y el cable USB.'));
      }
      done(null, finalObj);
    });

    proc.stdin.on('error', () => {});
    proc.stdin.end(JSON.stringify(job));
  });
}

function sha256FileSync(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

async function secureDelete(filePath) {
  if (!filePath) return;
  try {
    const stat = await fs.promises.lstat(filePath);
    if (stat.isFile() && !stat.isSymbolicLink() && stat.size > 0 && stat.size <= 1024 * 1024) {
      await fs.promises.writeFile(filePath, Buffer.alloc(stat.size, 0x00));
    }
  } catch {}
  await fs.promises.unlink(filePath).catch(() => {});
}

function assertSupportedPlatform(platform = process.platform) {
  if (!SUPPORTED_PLATFORMS.has(platform)) {
    fail('La grabación IoT está disponible en Linux y Windows.');
  }
}

function resolveFlashEngine({ rootDir, userDataDir, pythonBin = null, esptoolBin = null, platform = process.platform } = {}) {
  if (pythonBin) return { kind: 'python', bin: pythonBin };
  if (esptoolBin) return { kind: 'esptool', bin: esptoolBin };
  if (platform === 'win32') {
    const direct = findEsptoolBinary({ rootDir, userDataDir, platform });
    if (direct) return { kind: 'esptool', bin: direct };
    const py = findPythonWithEsptool({ platform });
    if (py) return { kind: 'python', bin: py };
    fail('Falta esptool.exe para grabar en Windows. Usa el paquete oficial de LA AGUJA con esptool incluido o instala Python con esptool y pyserial.');
  }
  const py = findPythonWithEsptool({ platform });
  if (py) return { kind: 'python', bin: py };
  const direct = findEsptoolBinary({ rootDir, userDataDir, platform });
  if (direct) return { kind: 'esptool', bin: direct };
  fail('Falta esptool o pyserial en este PC. En Linux instala esptool y pyserial (por ejemplo: pip install esptool pyserial o pacman -S esptool python-pyserial).');
}

async function probeSerialPort({
  port,
  rootDir,
  userDataDir,
  customFirmwareDirs = {},
  progress = () => {},
  pythonBin = null,
  esptoolBin = null,
} = {}) {
  assertSupportedPlatform();
  const cleanPort = normalizeSerialPort(port);
  if (process.platform === 'linux') {
    try {
      fs.accessSync(cleanPort, fs.constants.R_OK | fs.constants.W_OK);
    } catch {
      fail(`Sin permisos en ${cleanPort}. Añade tu usuario al grupo uucp/dialout.`);
    }
  }
  const catalog = loadBoards({ rootDir, userDataDir, customFirmwareDirs });
  const ports = await listSerialPorts(catalog.boards, { rootDir });
  const portMeta = ports.find((p) => p.path === cleanPort) || { path: cleanPort };
  const engine = resolveFlashEngine({ rootDir, userDataDir, pythonBin, esptoolBin });

  let receipt;
  if (engine.kind === 'esptool') {
    progress('iot-flash', { stage: 'probe', message: `Sondeando silicio en ${cleanPort}…`, done: 25, total: 100 });
    const lines = await runEsptoolDirect(engine.bin, ['--port', cleanPort, 'flash-id'], {
      stage: 'probe',
      label: 'Sondeando chip',
      progress,
      timeoutMs: 25000,
    });
    receipt = parseEsptoolChipInfo(lines);
    progress('iot-flash', { stage: 'probe', message: `Detectado ${receipt.chip || 'ESP32'} (${receipt.flash_size || '?'})`, done: 100, total: 100 });
  } else {
    const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
    const scriptPath = path.join(iotRoot, 'scripts', 'iot-flash.py');
    receipt = await runIotHelper(engine.bin, scriptPath, { op: 'probe', port: cleanPort }, { progress, timeoutMs: 25000 });
  }

  const matched = matchBoardFromProbe(receipt, portMeta, catalog.boards);
  return {
    port: cleanPort,
    usbId: portMeta.usbId || '',
    product: portMeta.product || '',
    chip: receipt.chip || '',
    chipNormalized: receipt.chip_normalized || '',
    features: receipt.features || '',
    mac: receipt.mac || '',
    flashSize: receipt.flash_size || '',
    flashMb: receipt.flash_mb || 0,
    psramMb: receipt.psram_mb || 0,
    matchedBoardId: matched?.boardId || '',
    matchedBoardName: matched?.boardName || '',
    matchedFamily: matched?.family || '',
  };
}

async function autoDetectConnectedBoard({
  rootDir,
  userDataDir,
  customFirmwareDirs = {},
  progress = () => {},
  pythonBin = null,
  esptoolBin = null,
} = {}) {
  const catalog = loadBoards({ rootDir, userDataDir, customFirmwareDirs });
  const ports = await listSerialPorts(catalog.boards, { rootDir });
  const candidates = ports.filter((p) => p.accessible);
  if (!candidates.length) {
    return {
      ports,
      detected: null,
      warning: ports.length
        ? (process.platform === 'win32'
          ? 'Se detectó un puerto COM sin estado OK. Comprueba el Administrador de dispositivos de Windows.'
          : 'Se detectó un puerto USB serie sin permisos de acceso (grupo uucp/dialout).')
        : '',
    };
  }
  const preferred = candidates.find((p) => p.matchedBoardIds.length > 0) || candidates[0];
  try {
    const detected = await probeSerialPort({
      port: preferred.path,
      rootDir,
      userDataDir,
      customFirmwareDirs,
      progress,
      pythonBin,
      esptoolBin,
    });
    return { ports, detected, warning: '' };
  } catch (err) {
    return { ports, detected: null, warning: err.message };
  }
}

async function eraseBoard({
  port,
  chip = 'auto',
  rootDir,
  userDataDir,
  progress = () => {},
  pythonBin = null,
  esptoolBin = null,
} = {}) {
  assertSupportedPlatform();
  const cleanPort = normalizeSerialPort(port);
  if (process.platform === 'linux') {
    try {
      fs.accessSync(cleanPort, fs.constants.R_OK | fs.constants.W_OK);
    } catch {
      fail(`Sin permisos de lectura/escritura en ${cleanPort}. Añade tu usuario al grupo dialout/uucp.`);
    }
  }
  const engine = resolveFlashEngine({ rootDir, userDataDir, pythonBin, esptoolBin });
  let receipt;
  if (engine.kind === 'esptool') {
    progress('iot-flash', { stage: 'erase', message: `Borrando memoria flash en ${cleanPort}…`, done: 15, total: 100 });
    const argv = ['--port', cleanPort];
    if (chip && chip !== 'auto') argv.push('--chip', chip);
    argv.push('erase-flash');
    const lines = await runEsptoolDirect(engine.bin, argv, {
      stage: 'erase',
      label: 'Borrando memoria flash',
      progress,
      timeoutMs: 120000,
    });
    receipt = parseEsptoolChipInfo(lines);
    progress('iot-flash', { stage: 'erase', message: 'Memoria flash borrada completamente.', done: 100, total: 100 });
  } else {
    const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
    const scriptPath = path.join(iotRoot, 'scripts', 'iot-flash.py');
    receipt = await runIotHelper(engine.bin, scriptPath, { op: 'erase', port: cleanPort, chip }, { progress, timeoutMs: 120000 });
  }
  return {
    erased: true,
    port: cleanPort,
    chip: receipt.chip || chip,
    mac: receipt.mac || '',
    flashSize: receipt.flash_size || '',
  };
}

async function flashBoard({
  boardId,
  port,
  configInput,
  backupPath = '',
  verifyBoot = true,
  customFirmwareDir = '',
  rootDir,
  userDataDir,
  progress = () => {},
  getHTTPS = core.getHTTPS,
  pythonBin = null,
  esptoolBin = null,
} = {}) {
  assertSupportedPlatform();
  const catalog = loadBoards({ rootDir, userDataDir, customFirmwareDirs: customFirmwareDir ? { [boardId]: customFirmwareDir } : {} });
  const board = catalog.boards.find((b) => b.id === boardId);
  if (!board) fail('Selecciona una placa de desarrollo compatible.');
  if (board.status === 'planned') fail('Esta placa aún está planificada y no tiene firmware compilado.');

  const bundle = inspectFirmwareDir(board.firmwareDir, board);
  if (!bundle) {
    fail('No se encontró el paquete de firmware compilado para esta placa. Selecciona la carpeta del firmware o compílalo primero.');
  }

  const cleanPort = normalizeSerialPort(port);
  if (process.platform === 'linux') {
    try {
      fs.accessSync(cleanPort, fs.constants.R_OK | fs.constants.W_OK);
    } catch {
      fail(`Sin permisos de lectura/escritura en ${cleanPort}. Añade tu usuario al grupo dialout/uucp o ajusta permisos del puerto.`);
    }
  }

  const preparedInput = JSON.parse(JSON.stringify(configInput || {}));
  preparedInput.tailnet = preparedInput.tailnet || {};
  const host = iotNvs.normalizeControlHost(preparedInput.tailnet.ctrlHost || preparedInput.tailnet.loginServer || '');
  preparedInput.tailnet.ctrlHost = host;
  if (!preparedInput.tailnet.ctrlNoisePubkeyHex) {
    progress('iot-flash', { message: `Obteniendo clave Noise de ${host}…` });
    const fetched = await fetchControlNoiseKey(host, { getHTTPS });
    preparedInput.tailnet.ctrlNoisePubkeyHex = fetched.noisePubkeyHex;
  }

  progress('iot-flash', { message: 'Generando partición NVS privada (48 KiB)…' });
  const nvs = iotNvs.buildProvisioningNvs(preparedInput, board, { sizeBytes: bundle.nvs_size });

  const tmpDir = path.join(userDataDir || os.tmpdir(), 'iot-tmp');
  await fs.promises.mkdir(tmpDir, { recursive: true, mode: 0o700 });
  const nvsFile = path.join(tmpDir, `aguja-nvs-${crypto.randomBytes(12).toString('hex')}.bin`);
  await fs.promises.writeFile(nvsFile, nvs.partition, { mode: 0o600 });

  const engine = resolveFlashEngine({ rootDir, userDataDir, pythonBin, esptoolBin });
  const segments = [
    ...bundle.segments.map((s) => ({ offset: s.offset, path: s.path, sha256: s.sha256 })),
    { offset: bundle.nvs_offset, path: nvsFile, sha256: nvs.sha256 },
  ];

  try {
    let receipt;
    if (engine.kind === 'esptool') {
      progress('iot-flash', { stage: 'verify', message: 'Comprobando integridad SHA-256 del firmware y NVS…', done: 10, total: 100 });
      const writeArgs = [];
      for (const seg of segments) {
        if (!/^0x[0-9a-fA-F]+$/.test(seg.offset)) fail(`Offset de flash inválido: ${seg.offset}`);
        if (!fs.existsSync(seg.path)) fail(`Falta archivo de firmware: ${path.basename(seg.path)}`);
        if (seg.sha256 && sha256FileSync(seg.path) !== seg.sha256.toLowerCase()) {
          fail(`SHA-256 incorrecto para ${path.basename(seg.path)}.`);
        }
        writeArgs.push(seg.offset, seg.path);
      }

      progress('iot-flash', { stage: 'probe', message: `Conectando con el microcontrolador en ${cleanPort}…`, done: 15, total: 100 });
      const probeArgv = ['--port', cleanPort];
      if (bundle.chip && bundle.chip !== 'auto') probeArgv.push('--chip', bundle.chip);
      probeArgv.push('flash-id');
      const probeLines = await runEsptoolDirect(engine.bin, probeArgv, {
        stage: 'probe',
        label: 'Detectando placa',
        progress,
        timeoutMs: 30000,
      });
      const info = parseEsptoolChipInfo(probeLines);

      let backupReceipt = null;
      if (backupPath) {
        const totalBytes = flashSizeBytes(info.flash_size || bundle.flash_size);
        await fs.promises.mkdir(path.dirname(path.resolve(backupPath)), { recursive: true });
        progress('iot-flash', { stage: 'backup', message: `Respaldando flash completa (${Math.round(totalBytes / 1048576)} MB)…`, done: 0, total: 100 });
        await runEsptoolDirect(
          engine.bin,
          ['--chip', bundle.chip, '--port', cleanPort, '--baud', '460800', 'read-flash', '0x0', '0x' + totalBytes.toString(16), backupPath],
          { stage: 'backup', label: 'Respaldando flash', progress, timeoutMs: 10 * 60 * 1000 },
        );
        backupReceipt = {
          path: backupPath,
          bytes: fs.statSync(backupPath).size,
          sha256: sha256FileSync(backupPath),
        };
      }

      progress('iot-flash', { stage: 'write', message: 'Grabando firmware y configuración privada NVS…', done: 0, total: 100 });
      await runEsptoolDirect(
        engine.bin,
        [
          '--chip', bundle.chip,
          '--port', cleanPort,
          '--baud', '460800',
          '--before', 'default-reset',
          '--after', 'hard-reset',
          'write-flash',
          '-z',
          '--flash-mode', bundle.flash_mode,
          '--flash-freq', bundle.flash_freq,
          '--flash-size', bundle.flash_size,
          ...writeArgs,
        ],
        { stage: 'write', label: 'Grabando flash', progress, timeoutMs: 5 * 60 * 1000 },
      );
      progress('iot-flash', { stage: 'write', message: 'Flash verificada por esptool.', done: 100, total: 100 });

      let bootInfo = null;
      if (verifyBoot) {
        await new Promise((r) => setTimeout(r, 900));
        if (process.platform === 'win32') {
          bootInfo = await verifyWindowsSerialBoot(cleanPort, { timeoutSec: 24, rootDir, progress });
        } else {
          bootInfo = { booted: true, warning: 'Verificación serie directa disponible vía Python pyserial en Linux.' };
        }
      }

      receipt = {
        chip: info.chip || bundle.chip,
        mac: info.mac || '',
        flash_size: info.flash_size || bundle.flash_size,
        backup: backupReceipt,
        boot: bootInfo,
      };
    } else {
      const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
      const scriptPath = path.join(iotRoot, 'scripts', 'iot-flash.py');
      if (!fs.existsSync(scriptPath)) fail('Falta el script de grabación IoT (iot/scripts/iot-flash.py).');
      receipt = await runIotHelper(
        engine.bin,
        scriptPath,
        {
          op: 'flash',
          port: cleanPort,
          chip: bundle.chip,
          baud: 460800,
          flash_mode: bundle.flash_mode,
          flash_freq: bundle.flash_freq,
          flash_size: bundle.flash_size,
          segments,
          backup_path: backupPath || '',
          verify_boot: Boolean(verifyBoot),
          boot_timeout_s: 26,
        },
        { progress },
      );
    }

    return {
      verified: true,
      boardId: board.id,
      boardName: board.name,
      firmwareVersion: bundle.version,
      port: cleanPort,
      chip: receipt.chip,
      mac: receipt.mac,
      flashSize: receipt.flash_size,
      hostname: nvs.config.tailnet.hostname,
      ctrlHost: nvs.config.tailnet.ctrl_host,
      apiToken: nvs.config.agent.api_token,
      exitNodeEnabled: nvs.config.tailnet.exit_node_enabled,
      advertiseUpstreamSubnet: nvs.config.tailnet.advertise_upstream_subnet,
      advertiseApSubnet: nvs.config.tailnet.advertise_ap_subnet,
      backup: receipt.backup || null,
      boot: receipt.boot || null,
    };
  } finally {
    await secureDelete(nvsFile);
  }
}

module.exports = {
  isValidSerialPort,
  normalizeSerialPort,
  resolveIotRoot,
  inspectFirmwareDir,
  loadBoards,
  normalizeChipName,
  parseEsptoolChipInfo,
  matchBoardFromProbe,
  listLinuxSerialPorts,
  parseWindowsPortsOutput,
  listWindowsSerialPorts,
  listSerialPorts,
  fetchControlNoiseKey,
  findEsptoolBinary,
  findPythonWithEsptool,
  probeSerialPort,
  autoDetectConnectedBoard,
  eraseBoard,
  flashBoard,
};
