const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

function element() {
  const classes = new Set(['hidden']);
  return {
    children: [], className: '',
    value: '', textContent: '', disabled: false, dataset: {}, style: {}, attributes: {},
    classList: { remove: (c) => classes.delete(c), toggle: (c, on) => on ? classes.add(c) : classes.delete(c) },
    addEventListener(name, fn) { this[name] = fn; },
    setAttribute(name, value) { this.attributes[name] = value; },
    focus() { this.focused = true; },
    append(...nodes) { this.children.push(...nodes); },
    insertBefore(node, reference) { const index = this.children.indexOf(reference); this.children.splice(index < 0 ? this.children.length : index, 0, node); },
  };
}

async function setup(chat = async () => ({ ok: true, json: async () => ({ answer: 'Answer', agents_used: ['policy'], latency_ms: 500 }) }), health) {
  const ids = Object.fromEntries(['ask-form', 'medical-input', 'chat-result', 'result-text', 'result-meta', 'connection-status', 'check-connection', 'conversation', 'composer-error'].map(id => [id, element()]));
  ids.conversation.append(ids['chat-result']);
  const button = element();
  ids['ask-form'].querySelector = () => button;
  ids['chat-result'].querySelector = () => ids['result-text'];
  const pill = element();
  pill.textContent = 'Insurance coverage';
  pill.dataset.prompt = 'What does my insurance cover?';
  const calls = [];
  const context = vm.createContext({
    document: { getElementById: id => ids[id], querySelectorAll: () => [pill], querySelector: () => element(), createElement: () => element() },
    fetch: async (url, options) => {
      calls.push({ url, options });
      return url === '/api/health' ? (health ? health() : { ok: true, json: async () => ({ status: 'ok', services: { concierge: { status: 'available' }, policy: { status: 'available' }, research: { status: 'available' } } }) }) : chat(url, options);
    },
    AbortController, setTimeout, clearTimeout,
  });
  vm.runInContext(readFileSync('frontend/app.js', 'utf8'), context, { filename: 'frontend/app.js' });
  await new Promise(setImmediate);
  return { ids, button, pill, calls, submit: async (value) => {
    ids['medical-input'].value = value;
    await ids['ask-form'].submit({ preventDefault() {} });
  } };
}

test('sends trimmed question to same-origin concierge endpoint and shows metadata', async () => {
  const ui = await setup();
  await ui.submit('  My benefits?  ');
  const call = ui.calls.find(c => c.url === '/api/chat');
  assert.deepEqual(JSON.parse(call.options.body), { message: 'My benefits?' });
  assert.equal(ui.ids['result-text'].textContent, 'Answer');
  assert.match(ui.ids['result-meta'].textContent, /policy/i);
  assert.equal(ui.button.textContent, 'Send');
});
test('blank questions do not call concierge', async () => {
  const ui = await setup(); await ui.submit('   ');
  assert.equal(ui.calls.filter(c => c.url === '/api/chat').length, 0);
  assert.equal(ui.ids['medical-input'].focused, true);
});
test('overlong questions are rejected before sending', async () => {
  const ui = await setup(); await ui.submit('a'.repeat(8001));
  assert.equal(ui.calls.filter(c => c.url === '/api/chat').length, 0);
  assert.match(ui.ids['composer-error'].textContent, /8,000/);
});
test('duplicate submissions are prevented while request is pending', async () => {
  let finish;
  const ui = await setup(() => new Promise(resolve => { finish = resolve; }));
  const pending = ui.submit('question');
  assert.equal(ui.button.disabled, true);
  await ui.submit('duplicate');
  assert.equal(ui.calls.filter(c => c.url === '/api/chat').length, 1);
  finish({ ok: true, json: async () => ({ answer: 'Done' }) }); await pending;
  assert.equal(ui.button.disabled, false);
});
test('quick actions insert actual prompts', async () => {
  const ui = await setup(); ui.pill.click();
  assert.equal(ui.ids['medical-input'].value, 'What does my insurance cover?');
});
for (const detail of ['Service unavailable', { message: 'Service unavailable' }, [{ msg: 'Too long' }]]) {
  test(`handles API error detail ${JSON.stringify(detail)}`, async () => {
    const ui = await setup(async () => ({ ok: false, json: async () => ({ detail }) }));
    await ui.submit('question');
    assert.match(ui.ids['result-text'].textContent, /Service unavailable|Too long/);
    assert.equal(ui.button.disabled, false);
  });
}
test('non-JSON responses show a readable error', async () => {
  const ui = await setup(async () => ({ ok: false, json: async () => { throw new SyntaxError('Unexpected <'); } }));
  await ui.submit('question');
  assert.match(ui.ids['result-text'].textContent, /unavailable/i);
  assert.doesNotMatch(ui.ids['result-text'].textContent, /Unexpected/);
});
test('network failure leaves form retryable', async () => {
  const ui = await setup(async () => { throw new TypeError('Failed to fetch'); });
  await ui.submit('question'); assert.equal(ui.button.disabled, false);
  assert.match(ui.ids['result-text'].textContent, /connection/i);
});
test('timeout has an actionable message', async () => {
  const ui = await setup(async () => { const error = new Error(); error.name = 'AbortError'; throw error; });
  await ui.submit('question'); assert.match(ui.ids['result-text'].textContent, /timed out/i);
});
test('empty answers are errors', async () => {
  const ui = await setup(async () => ({ ok: true, json: async () => ({ answer: ' ' }) }));
  await ui.submit('question'); assert.match(ui.ids['result-text'].textContent, /empty answer/i);
});
test('model output is rendered as plain text', async () => {
  const ui = await setup(async () => ({ ok: true, json: async () => ({ answer: '<script>bad()</script>' }) }));
  await ui.submit('question'); assert.equal(ui.ids['result-text'].textContent, '<script>bad()</script>');
});
test('reports ready connection only for healthy services', async () => {
  const ui = await setup(); assert.match(ui.ids['connection-status'].textContent, /connected/i);
});
test('reports missing specialists', async () => {
  const ui = await setup(undefined, async () => ({ ok: true, json: async () => ({ status: 'degraded', services: { concierge: { status: 'available' }, policy: { status: 'unavailable' } } }) }));
  assert.match(ui.ids['check-connection'].attributes.title, /policy.*research/i);
});
test('reports unavailable concierge and supports recheck', async () => {
  const ui = await setup(undefined, async () => ({ ok: true, json: async () => ({ services: { concierge: { status: 'unavailable' } } }) }));
  assert.match(ui.ids['connection-status'].textContent, /offline/i);
  await ui.ids['check-connection'].click();
  assert.equal(ui.calls.filter(c => c.url === '/api/health').length, 2);
});
test('health network errors do not break the form', async () => {
  const ui = await setup(undefined, async () => { throw new TypeError('offline'); });
  assert.match(ui.ids['connection-status'].textContent, /offline/i);
  await ui.submit('question'); assert.equal(ui.ids['result-text'].textContent, 'Answer');
});

test('keeps user questions and replies in order across submissions', async () => {
  const ui = await setup();
  await ui.submit('First question');
  assert.equal(ui.ids['medical-input'].value, '');
  await ui.submit('Second question');
  const rows = ui.ids.conversation.children;
  assert.equal(rows.length, 4);
  assert.equal(rows[0].className, 'user-message');
  assert.equal(rows[0].children[1].textContent, 'First question');
  assert.equal(rows[1].children[1].textContent, 'Answer');
  assert.equal(rows[2].children[1].textContent, 'Second question');
  assert.equal(rows[3], ui.ids['chat-result']);
});
test('errors keep the submitted question available for retry without losing history', async () => {
  const ui = await setup(async () => { throw new TypeError('offline'); });
  await ui.submit('My question');
  assert.equal(ui.ids['medical-input'].value, 'My question');
  assert.equal(ui.ids.conversation.children[0].children[1].textContent, 'My question');
});

test('connection button shows a green state only for healthy services', async () => {
  const ui = await setup();
  assert.equal(ui.ids['check-connection'].dataset.state, 'connected');
  assert.equal(ui.ids['connection-status'].textContent, 'Connected');
});
