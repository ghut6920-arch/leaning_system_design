/** Teacher preparation r1; AI-authored SVG-to-PNG rendering, no installation. */
'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');

const bundledSharp = 'C:/Users/15006/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.cjs';
const args = process.argv.slice(2);
const moduleFlag = args.indexOf('--sharp-module');
const sharpModule = moduleFlag >= 0 ? args[moduleFlag + 1] : bundledSharp;
if (!sharpModule || !path.isAbsolute(sharpModule)) {
  throw new Error('--sharp-module must point to an absolute sharp module file');
}
const sharp = require(sharpModule);
const projectRoot = path.resolve(__dirname, '../../..');
const figures = path.join(projectRoot, 'artifacts', 'lesson-preparation',
  '2026-10-11-transformer-kv-cache-r1', 'figures');
const names = ['cache-timeline', 'two-layer-dependency', 'kv-capacity'];
const figureFlag = args.indexOf('--figure');
const selected = figureFlag >= 0 ? [args[figureFlag + 1]] : names;
if (selected.some(name => !names.includes(name))) {
  throw new Error('--figure must select cache-timeline, two-layer-dependency, or kv-capacity');
}

async function main() {
  const infoPath = path.join(figures, 'render-info.json');
  const previousInfo = figureFlag >= 0 ? JSON.parse(await fs.readFile(infoPath, 'utf8')) : null;
  const rendered = previousInfo ? [...previousInfo.rendered] : [];
  for (const name of selected) {
    const source = path.join(figures, `${name}.svg`);
    const target = path.join(figures, `${name}.png`);
    const sourceBytes = await fs.readFile(source);
    await sharp(sourceBytes, { density: 144 }).png().toFile(target);
    const pngBytes = await fs.readFile(target);
    if (!pngBytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
      throw new Error(`Invalid PNG signature: ${target}`);
    }
    const metadata = await sharp(pngBytes).metadata();
    const record = { source, target, width: metadata.width, height: metadata.height,
      format: metadata.format, bytes: pngBytes.length };
    const previousIndex = rendered.findIndex(item => item.target === target);
    if (previousIndex >= 0) rendered[previousIndex] = record;
    else rendered.push(record);
    process.stdout.write(`${name}.png: ${metadata.width} x ${metadata.height}, ${pngBytes.length} bytes\n`);
  }
  const info = { revision: 'preparation-r1', status: 'teacher_preparation_only',
    renderer: 'bundled sharp; no dependency installation', node: process.version,
    nodeExecutable: process.execPath, sharpModule, sharpVersions: sharp.versions,
    density: 144, fontPolicy: 'SVG names Microsoft YaHei, Noto Sans CJK SC, sans-serif; system font resolution',
    lastRenderedFigures: selected, rendered };
  await fs.writeFile(infoPath, JSON.stringify(info, null, 2) + '\n', 'utf8');
  const readBack = JSON.parse(await fs.readFile(infoPath, 'utf8'));
  if (JSON.stringify(readBack) !== JSON.stringify(info)) {
    throw new Error('Renderer metadata read-back mismatch');
  }
}

main().catch(error => { process.stderr.write(`${error.stack}\n`); process.exitCode = 1; });
