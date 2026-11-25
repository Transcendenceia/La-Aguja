'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const os = require('node:os');
const { spawn } = require('node:child_process');
const { StringDecoder } = require('node:string_decoder');
const core = require('./core.cjs');
const iotNvs = require('./iot-nvs.cjs');

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

    // Walk up from /sys/class/tty/<name>/device to locate USB idVendor/idProduct
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

    const matchedBoardIds = matchBoardIds(vid, pid, boards);
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
      matchedBoardIds,
    });
  }

  ports.sort((a, b) => {
    const scoreA = (a.matchedBoardIds.length ? 2 : 0) + (a.accessible ? 1 : 0);
    const scoreB = (b.matchedBoardIds.length ? 2 : 0) + (b.accessible ? 1 : 0);
    if (scoreB !== scoreA) return scoreB - scoreA;
    return a.path.localeCompare(b.path);
  });
  return ports;
}

async function listSerialPorts(boards = []) {
  if (process.platform === 'linux') {
    return listLinuxSerialPorts(boards);
  }
  // Future Windows support hook (PowerShell Win32_SerialPort / COM ports)
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

function findPythonWithEsptool() {
  const candidates = [];
  if (process.env.AGUJA_IOT_PYTHON) candidates.push(process.env.AGUJA_IOT_PYTHON);
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
  for (const py of candidates) {
    if (py !== 'python3' && !fs.existsSync(py)) continue;
    try {
      const res = require('node:child_process').spawnSync(
        py,
        ['-c', 'import esptool, serial'],
        { timeout: 4000, stdio: 'ignore' },
      );
      if (res.status === 0) return py;
    } catch {}
  }
  fail('Falta esptool o pyserial en este PC. En Linux instala esptool y pyserial (por ejemplo: pip install esptool pyserial o pacman -S esptool python-pyserial).');
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
} = {}) {
  if (process.platform !== 'linux') {
    fail('La grabación IoT está disponible primero en Linux. El soporte de Windows llegará en la siguiente fase.');
  }
  const catalog = loadBoards({ rootDir, userDataDir, customFirmwareDirs: customFirmwareDir ? { [boardId]: customFirmwareDir } : {} });
  const board = catalog.boards.find((b) => b.id === boardId);
  if (!board) fail('Selecciona una placa de desarrollo compatible.');
  if (board.status === 'planned') fail('Esta placa aún está planificada y no tiene firmware compilado.');

  const bundle = inspectFirmwareDir(board.firmwareDir, board);
  if (!bundle) {
    fail('No se encontró el paquete de firmware compilado para esta placa. Selecciona la carpeta del firmware o compílalo primero.');
  }

  if (typeof port !== 'string' || !/^\/dev\/tty(ACM|USB)\d+$/.test(port)) {
    fail('Selecciona un puerto USB serie válido (/dev/ttyACM* o /dev/ttyUSB*).');
  }
  try {
    fs.accessSync(port, fs.constants.R_OK | fs.constants.W_OK);
  } catch {
    fail(`Sin permisos de lectura/escritura en ${port}. Añade tu usuario al grupo dialout/uucp o ajusta permisos del puerto.`);
  }

  // Auto-fetch Noise public key if using self-hosted Headscale and left blank
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

  const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
  const scriptPath = path.join(iotRoot, 'scripts', 'iot-flash.py');
  if (!fs.existsSync(scriptPath)) {
    await secureDelete(nvsFile);
    fail('Falta el script de grabación IoT (iot/scripts/iot-flash.py).');
  }

  const py = pythonBin || findPythonWithEsptool();
  const segments = [
    ...bundle.segments.map((s) => ({ offset: s.offset, path: s.path, sha256: s.sha256 })),
    { offset: bundle.nvs_offset, path: nvsFile, sha256: nvs.sha256 },
  ];

  try {
    const receipt = await runIotHelper(
      py,
      scriptPath,
      {
        op: 'flash',
        port,
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

    return {
      verified: true,
      boardId: board.id,
      boardName: board.name,
      firmwareVersion: bundle.version,
      port,
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

async function probeSerialPort({
  port,
  rootDir,
  userDataDir,
  customFirmwareDirs = {},
  progress = () => {},
  pythonBin = null,
} = {}) {
  if (process.platform !== 'linux') {
    fail('La detección directa por puerto serie está disponible primero en Linux.');
  }
  if (typeof port !== 'string' || !/^\/dev\/tty(ACM|USB)\d+$/.test(port)) {
    fail('Puerto serie no válido para sondear.');
  }
  try {
    fs.accessSync(port, fs.constants.R_OK | fs.constants.W_OK);
  } catch {
    fail(`Sin permisos en ${port}. Añade tu usuario al grupo uucp/dialout.`);
  }
  const catalog = loadBoards({ rootDir, userDataDir, customFirmwareDirs });
  const ports = await listSerialPorts(catalog.boards);
  const portMeta = ports.find((p) => p.path === port) || { path: port };
  const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
  const scriptPath = path.join(iotRoot, 'scripts', 'iot-flash.py');
  const py = pythonBin || findPythonWithEsptool();
  const receipt = await runIotHelper(py, scriptPath, { op: 'probe', port }, { progress, timeoutMs: 25000 });
  const matched = matchBoardFromProbe(receipt, portMeta, catalog.boards);
  return {
    port,
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
} = {}) {
  const catalog = loadBoards({ rootDir, userDataDir, customFirmwareDirs });
  const ports = await listSerialPorts(catalog.boards);
  const candidates = ports.filter((p) => p.accessible);
  if (!candidates.length) {
    return { ports, detected: null, warning: ports.length ? 'Se detectó un puerto USB serie sin permisos de acceso (grupo uucp/dialout).' : '' };
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
  progress = () => {},
  pythonBin = null,
} = {}) {
  if (process.platform !== 'linux') {
    fail('La limpieza de flash IoT está disponible primero en Linux.');
  }
  if (typeof port !== 'string' || !/^\/dev\/tty(ACM|USB)\d+$/.test(port)) {
    fail('Selecciona un puerto USB serie válido (/dev/ttyACM* o /dev/ttyUSB*).');
  }
  try {
    fs.accessSync(port, fs.constants.R_OK | fs.constants.W_OK);
  } catch {
    fail(`Sin permisos de lectura/escritura en ${port}. Añade tu usuario al grupo dialout/uucp.`);
  }
  const iotRoot = resolveIotRoot(rootDir || path.resolve(__dirname, '..'));
  const scriptPath = path.join(iotRoot, 'scripts', 'iot-flash.py');
  const py = pythonBin || findPythonWithEsptool();
  const receipt = await runIotHelper(py, scriptPath, { op: 'erase', port, chip }, { progress, timeoutMs: 120000 });
  return {
    erased: true,
    port,
    chip: receipt.chip || chip,
    mac: receipt.mac || '',
    flashSize: receipt.flash_size || '',
  };
}

module.exports = {
  resolveIotRoot,
  inspectFirmwareDir,
  loadBoards,
  matchBoardFromProbe,
  listLinuxSerialPorts,
  listSerialPorts,
  fetchControlNoiseKey,
  findPythonWithEsptool,
  probeSerialPort,
  autoDetectConnectedBoard,
  eraseBoard,
  flashBoard,
};
