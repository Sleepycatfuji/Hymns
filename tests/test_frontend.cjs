// Exercise the shipped script with lightweight DOM/storage adapters; no npm install.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const dataset = JSON.parse(fs.readFileSync(path.join(root, 'data/hymns_dataset_updated.json'), 'utf8'));
const nodes = new Map();
const storage = new Map();
const document = {
  documentElement: {},
  getElementById(id) {
    if (!nodes.has(id)) nodes.set(id, { dataset: {}, value: '', addEventListener() {} });
    return nodes.get(id);
  },
};
const context = vm.createContext({ document, console,
  localStorage: { getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) },
  // Keep initial loading pending; assertions exercise the same real functions below.
  fetch: () => new Promise(() => {}),
});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
assert.equal(vm.runInContext('DATA_PATH', context), './data/hymns_dataset_updated.json');
let checked = 0;
for (const hymn of Object.values(dataset)) {
  const options = context.getChoraleOptions(hymn);
  const rendered = context.renderChoraleOptionsHtml(hymn, options, null);
  for (const option of options) {
    assert.ok(rendered.includes(`value="${option.option_id}"`));
    assert.ok(rendered.includes(context.escapeHtml(option.chorale_title)));
  }
  if (hymn.special_reference) assert.ok(rendered.includes(context.escapeHtml(hymn.special_reference)));
  checked++;
}
const five = context.getChoraleOptions(dataset['5']);
assert.equal(JSON.stringify(five.map(o => o.display_kds)), '["424","563"]');
assert.equal(dataset['5'].verse_count, 7);
assert.equal(context.hymnMatchesQuery('5', dataset['5'], '5'), true);
assert.equal(context.hymnMatchesQuery('50', dataset['50'], '5'), false);
context.setPreferredChorale(5, 'kds:563');
assert.equal(context.getPreferredChorale(5, five), 'kds:563');
context.setPreferredChorale(790, 'kds:158a');
assert.equal(context.getPreferredChorale(790, context.getChoraleOptions(dataset['790'])), null);
assert.ok(context.renderChoraleOptionsHtml({special_reference:'<script>'}, [], null).includes('&lt;script&gt;'));
console.log(`Frontend rendering validated for ${checked} hymns; numeric search and saved preferences passed.`);
