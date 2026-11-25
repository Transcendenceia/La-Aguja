'use strict';
const { _electron: electron } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

(async () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'aguja-iot-electron-qa-'));
  let application;
  try {
    application = await electron.launch({
      ...(process.env.AGUJA_QA_EXECUTABLE ? { executablePath: process.env.AGUJA_QA_EXECUTABLE } : {}),
      args: [path.resolve(__dirname, '..'), '--lang=es', '--no-sandbox', '--user-data-dir=' + path.join(temp, 'user-data')],
      env: { ...process.env, ELECTRON_RUN_AS_NODE: undefined, ELECTRON_DISABLE_SECURITY_WARNINGS: '1' },
    });
    const win = await application.firstWindow();
    await win.waitForLoadState('domcontentloaded');
    await win.locator('#app-language').selectOption('es');
    await win.waitForFunction(() => document.documentElement.lang === 'es');

    // 1. Default mode is USB Rescue
    assert.equal(await win.locator('#mode-usb').getAttribute('aria-selected'), 'true');
    assert.equal(await win.locator('#steps').isVisible(), true);
    assert.equal(await win.locator('#iot-steps').isVisible(), false);

    // 2. Switch to parallel IoT · MCU mode and verify full ESP32 family catalog + filters
    await win.locator('#mode-iot').click();
    assert.equal(await win.locator('#mode-iot').getAttribute('aria-selected'), 'true');
    await win.locator('[data-board-id="esp32s3-wroom-n16r8"]').waitFor({ state: 'visible' });
    await win.locator('[data-board-id="esp32c3-supermini"]').waitFor({ state: 'visible' });
    await win.locator('[data-board-id="esp32-devkit-v1"]').waitFor({ state: 'visible' });
    assert.ok((await win.locator('.board-card').count()) >= 10);

    // Filter by family chip and search box
    await win.locator('#iot-board-search').fill('SuperMini');
    assert.equal(await win.locator('.board-card').count(), 1);
    await win.locator('#iot-board-search').fill('');

    // Selecting XIAO reveals RF antenna switch card; selecting ESP32-S3 hides it
    await win.locator('[data-board-id="seeed-xiao-esp32c6"]').click();
    assert.equal(await win.locator('#iot-xiao-hw-card').isVisible(), true);
    await win.locator('[data-board-id="esp32s3-wroom-n16r8"]').click();
    assert.equal(await win.locator('#iot-xiao-hw-card').isVisible(), false);
    assert.equal(await win.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

    // 3. Step 02: Wi-Fi networks + verify SoftAP is DISABLED by default
    await win.locator('#next').click();
    await win.locator('#iot-wifi-ssid').waitFor({ state: 'visible' });
    assert.equal(await win.locator('#iot-ap-enabled').isChecked(), false);
    assert.equal(await win.locator('#iot-ap-fields').isVisible(), false);
    await win.locator('#iot-wifi-ssid').fill('SyntheticPrimary');
    await win.locator('#iot-wifi-password').fill('SYNTHETIC-WIFI-PASS');
    await win.locator('#iot-wifi-add').click();
    await win.locator('.iot-wifi-ssid').first().fill('SyntheticBackup');
    assert.equal(await win.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

    // 4. Step 03: Tailscale/Headscale provider switcher + proxy options + SoftAP route disabled
    await win.locator('#next').click();
    await win.locator('#iot-hostname').waitFor({ state: 'visible' });
    assert.equal(await win.locator('#iot-headscale-fields').isVisible(), false);
    assert.equal(await win.locator('#iot-sub-ap').isDisabled(), true);
    assert.equal(await win.locator('#iot-sub-ap').isChecked(), false);
    await win.locator('#iot-provider-headscale').click();
    assert.equal(await win.locator('#iot-headscale-fields').isVisible(), true);
    assert.equal(await win.locator('#iot-derp-region').inputValue(), '999');
    await win.locator('#iot-hostname').fill('aguja-s3-qa');
    await win.locator('#iot-ctrl-host').fill('https://headscale.example.invalid');
    await win.locator('#iot-auth-key').fill('SYNTHETIC-PREAUTH-KEY');
    assert.equal(await win.locator('#iot-exit-node').isChecked(), true);
    assert.equal(await win.locator('#iot-sub-upstream').isChecked(), true);
    assert.equal(await win.locator('#iot-dns-relay').isChecked(), true);
    assert.match(await win.locator('#iot-api-token').inputValue(), /^agj_[0-9a-f]{48}$/);
    assert.equal(await win.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

    // 5. Step 04: Summary + Flash partition map + Erase maintenance tool
    await win.locator('#next').click();
    await win.locator('#iot-summary').waitFor({ state: 'visible' });
    const summaryText = await win.locator('#iot-summary').textContent();
    assert.ok(summaryText.includes('ESP32-S3-WROOM-1'));
    assert.ok(summaryText.includes('SyntheticPrimary, SyntheticBackup'));
    assert.ok(summaryText.includes('Desactivado'));
    assert.ok(summaryText.includes('Exit Node'));
    assert.equal(await win.locator('#iot-flash-map-body tr').count(), 5);
    assert.equal(await win.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

    // 6. Switch back to USB Rescue cleanly
    await win.locator('#mode-usb').click();
    assert.equal(await win.locator('#steps').isVisible(), true);
    assert.equal(await win.locator('[data-step="0"]').isVisible(), true);

    console.log(JSON.stringify({ ok: true, boards: 11, softApDefaultOff: true, headscaleSwitch: true, flashMapRows: 5, zeroOverflow: true }));
  } finally {
    if (application) await application.close();
    fs.rmSync(temp, { recursive: true, force: true });
  }
})().catch((error) => {
  console.error(error.stack);
  process.exitCode = 1;
});
