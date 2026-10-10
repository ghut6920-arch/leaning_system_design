/* AI teacher artifact checks, v1, 2026-10-10.
 * Static/simulated-DOM checks only. This does not render or operate a browser.
 */
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, 'information-flow.html'), 'utf8');
const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map(x => x[1]));
const elements = new Map([...ids].map(id => [id, {
  textContent: '', style: {}, classes: new Set(),
  classList: { toggle(name, enabled) { enabled ? elements.get(id).classes.add(name) : elements.get(id).classes.delete(name); } }
}]));
const buttons = [...html.matchAll(/data-mode="([^"]+)"/g)].map(x => ({
  dataset: { mode: x[1] }, attributes: {}, handlers: {},
  setAttribute(k, v) { this.attributes[k] = v; },
  addEventListener(k, fn) { this.handlers[k] = fn; }
}));
const document = {
  getElementById(id) { if (!elements.has(id)) throw Error('Missing element ' + id); return elements.get(id); },
  querySelectorAll(selector) { if (selector !== 'button[data-mode]') throw Error('Unexpected selector'); return buttons; }
};
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const context = vm.createContext({ document });
vm.runInContext(script, context, { timeout: 1000 });
const cases = [];
function assert(ok, label) { if (!ok) throw Error(label); }
for (const button of buttons) {
  button.handlers.click();
  const name = button.dataset.mode;
  const text = id => elements.get(id).textContent;
  assert(buttons.filter(x => x.attributes['aria-pressed'] === 'true').length === 1, 'Selected mode');
  assert(button.attributes['aria-pressed'] === 'true', 'Correct button selected');
  assert(text('scope') && text('info') && text('update') && text('output'), 'Required text populated');
  if (name === 'imagine') {
    assert(text('sample-source').includes('pθ'), 'Future samples from prior');
    assert(elements.get('posterior').classes.has('unavailable'), 'Future q unavailable');
    assert(text('observation-info').includes('不可读取未来'), 'Future actual observation excluded');
  } else {
    assert(text('sample-source').includes('qφ'), 'Observed samples from recognition');
    assert(!elements.get('posterior').classes.has('unavailable'), 'Recognition available');
  }
  if (name === 'train') assert(text('update').includes('θ、φ'), 'Training updates model parameters');
  else assert(text('fixed').includes('固定') || text('fixed').includes('保持'), 'Online parameters fixed');
  cases.push({ mode: name, scope: text('scope'), sample: text('sample-source'), update: text('update'), passed: true });
}
assert(buttons.length === 4, 'Four work modes');
assert(!/<script[^>]+src=/.test(html) && !/\bfetch\(/.test(script), 'No runtime remote dependencies');
assert(html.includes('静态回退') && html.includes('@media'), 'Static fallback and responsive rules present');
const result = { version: 'v1', cases, all_passed: true,
  checked: ['JS execution against a small DOM stub', 'Information-source switching', 'Update-object text', 'No external scripts', 'Static fallback exists'],
  ui_rendering: 'not_executed: localhost preview timed out; file URL blocked by browser policy',
  limits: ['No screenshot or actual layout inspection', 'Stub checks do not verify real browser layout, accessibility, or event dispatch'] };
fs.writeFileSync(path.join(__dirname, 'information-flow-checks.json'), JSON.stringify(result, null, 2), 'utf8');
console.log(JSON.stringify({ all_passed: true, modes: cases.length, ui_rendering: result.ui_rendering }));
