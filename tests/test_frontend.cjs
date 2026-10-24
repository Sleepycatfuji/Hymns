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
  if (hymn.book_page) {
    assert.ok(rendered.includes(`Bogside ${hymn.book_page}</strong> — ${context.escapeHtml(hymn.book_page_label)}`));
    assert.ok(rendered.includes(`data-reference-type="book_page" data-page-number="${hymn.book_page}"`));
  }
  assert.equal((rendered.match(/data-reference-type="chorale"/g) || []).length, options.length);
  assert.ok(!rendered.includes('.pdf'), 'The app must not invent score URLs');
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
assert.equal(context.getPreferredChorale(790, context.getChoraleOptions(dataset['790'])), 'kds:158a');
context.setPreferredChorale(433, 'kds:202');
assert.equal(context.getPreferredChorale(433, context.getChoraleOptions(dataset['433'])), null);
const six = context.getChoraleOptions(dataset['6']);
assert.equal(JSON.stringify(six.map(o => o.display_kds)), '["424","563"]');
assert.equal(dataset['6'].verse_count, 3);
context.setPreferredChorale(6, 'kds:563');
assert.equal(context.getPreferredChorale(6, six), 'kds:563');
assert.equal(five.find(o => o.display_kds === '563').recording_melody, 'Hamburg 1690');
vm.runInContext('currentLanguage = "en";', context);
const page438 = context.renderChoraleOptionsHtml(dataset['438'], context.getChoraleOptions(dataset['438']), null);
assert.ok(page438.includes('Book page 568</strong> — Nadver C'));
assert.ok(!page438.includes('kds:568'));
assert.ok(!page438.includes('type="radio"'));
assert.equal(dataset['438'].verse_count, 1);
const page440 = context.renderChoraleOptionsHtml(dataset['440'], context.getChoraleOptions(dataset['440']), null);
assert.ok(page440.includes('Chorale book no. 416'));
assert.ok(page440.includes('Book page 570</strong> — Agnus Dei'));
assert.ok(page440.indexOf('Chorale book no. 416') < page440.indexOf('Book page 570'));
assert.ok(!page440.includes('kds:570'));
assert.equal(dataset['440'].verse_count, 3);
context.setPreferredChorale(440, 'kds:416');
assert.equal(context.getPreferredChorale(440, context.getChoraleOptions(dataset['440'])), 'kds:416');
assert.ok(context.renderChoraleOptionsHtml({book_page:568, book_page_label:'<script>'}, [], null).includes('&lt;script&gt;'));
assert.ok(!context.renderChoraleOptionsHtml({book_page:'<script>', book_page_label:'Nadver C'}, [], null).includes('<script>'));

console.log(`Frontend rendering validated for ${checked} hymns; numeric search and saved preferences passed.`);

// A release must reject a mismatched payload, even if it is valid hymn JSON.
(async () => {
  const { createHash, webcrypto } = require('node:crypto');
  const payload = JSON.stringify(dataset);
  const digest = createHash('sha256').update(payload).digest('hex');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace('const DATA_SHA256 = null;', `const DATA_SHA256 = "${digest}";`);
  const production = vm.createContext({document, localStorage: context.localStorage,
    console: {error() {}}, crypto: webcrypto, TextEncoder,
    fetch: () => new Promise(() => {})});
  vm.runInContext(script, production);
  production.runSearch = () => {};
  production.fetch = async () => ({ok: true, text: async () => payload});
  await production.loadData();
  assert.equal(document.getElementById('status').dataset.state, 'loaded');
  production.fetch = async () => ({ok: true, text: async () => payload + ' '});
  await production.loadData();
  assert.equal(document.getElementById('status').dataset.state, 'error');
  console.log('Release loader accepted matching data and rejected a mismatched payload.');
})().catch(error => { console.error(error); process.exitCode = 1; });
