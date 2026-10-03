const byId = id => document.getElementById(id);
const form = byId('ask-form');
const input = byId('medical-input');
const submitButton = form.querySelector('button[type="submit"]');
const quickPills = document.querySelectorAll('.action-pill');
const conversation = byId('conversation');
const composerError = byId('composer-error');
const hero = document.querySelector('.hero');
let user = null;
let csrf = '';
let activeId = null;
let pending = false;
let generation = 0;
let retry = null;
let register = false;
let historyCollapsed = false;
let renderedRequests = new Set();
let menuConversation = null;
let menuTrigger = null;
let renameTargetId = null;

function savedConversation(value) {
  if (!user) return null;
  const key = `medinova.conversation.${user.id}`;
  try {
    if (value === undefined) return localStorage.getItem(key);
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch { /* History still works when browser storage is disabled. */ }
  return null;
}
function setPending(value) {
  pending = value;
  const disabled = value || !user;
  submitButton.disabled = disabled;
  input.disabled = disabled;
  quickPills.forEach(pill => { pill.disabled = disabled; });
  byId('new-conversation').disabled = disabled;
  byId('rename-conversation').disabled = disabled || !menuConversation;
  byId('delete-conversation').disabled = disabled || !menuConversation;
  byId('conversation-list').querySelectorAll('button').forEach(button => { button.disabled = value; });
  submitButton.textContent = value ? 'Thinking…' : 'Send';
  form.setAttribute('aria-busy', String(value));
}
function setHistoryCollapsed(collapsed) {
  closeConversationMenu();
  historyCollapsed = collapsed;
  byId('chat-workspace').classList.toggle('history-collapsed', collapsed);
  const toggle = byId('toggle-history');
  toggle.setAttribute('aria-expanded', String(!collapsed));
  toggle.setAttribute('aria-label', collapsed ? 'Show conversation history' : 'Hide conversation history');
  toggle.title = collapsed ? 'Show conversation history' : 'Hide conversation history';
}
function closeConversationMenu() {
  byId('conversation-menu').classList.add('hidden');
  if (menuTrigger) menuTrigger.setAttribute('aria-expanded', 'false');
  menuConversation = null;
  menuTrigger = null;
}
function openConversationMenu(item, trigger) {
  if (pending) return;
  if (menuTrigger === trigger) { closeConversationMenu(); return; }
  closeConversationMenu();
  menuConversation = item;
  menuTrigger = trigger;
  trigger.setAttribute('aria-expanded', 'true');
  const menu = byId('conversation-menu');
  menu.classList.remove('hidden');
  const anchor = trigger.getBoundingClientRect();
  const left = Math.max(8, Math.min(anchor.right - menu.offsetWidth, window.innerWidth - menu.offsetWidth - 8));
  const below = anchor.bottom + 4;
  const top = below + menu.offsetHeight <= window.innerHeight - 8 ? below : Math.max(8, anchor.top - menu.offsetHeight - 4);
  menu.style.left = `${left}px`;
  menu.style.top = `${top}px`;
  setPending(false);
  byId('rename-conversation').focus();
}
function clearSession() {
  generation += 1;
  closeConversationMenu();
  if (byId('rename-dialog').open) byId('rename-dialog').close();
  savedConversation(null);
  user = null; csrf = ''; activeId = null; retry = null;
  conversation.replaceChildren();
  renderedRequests = new Set();
  byId('conversation-list').replaceChildren();
  byId('account-email').textContent = '';
  input.value = ''; composerError.textContent = '';
  byId('auth-password').value = '';
  byId('auth-email').value = '';
  byId('account-controls').classList.add('hidden');
  byId('chat-workspace').classList.add('hidden');
  setHistoryCollapsed(false);
  byId('auth-panel').classList.remove('hidden');
  hero.classList.remove('has-conversation');
  setPending(false);
}
async function requestJSON(url, options = {}, timeoutMs = 180000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const epoch = generation;
  const mutation = options.method && options.method !== 'GET';
  try {
    const response = await fetch(url, {...options, credentials: 'same-origin', signal: controller.signal,
      headers: {...(mutation ? {'Content-Type': 'application/json', 'X-Requested-With': 'fetch', ...(csrf ? {'X-CSRF-Token': csrf} : {})} : {}), ...options.headers}});
    if (response.status === 401 && epoch === generation) clearSession();
    if (response.status === 204) return null;
    let payload;
    try { payload = await response.json(); }
    catch { throw new Error('The server is unavailable. Please try again.'); }
    if (!response.ok) {
      const detail = payload?.detail;
      throw new Error(typeof detail === 'string' ? detail : detail?.message || 'The request could not be completed. Please try again.');
    }
    return payload;
  } finally { clearTimeout(timer); }
}
function showError(error) {
  return error.name === 'AbortError' ? 'The request timed out. Retry the same question to check its result.'
    : error.name === 'TypeError' ? 'Unable to connect. Check your connection and retry.' : error.message;
}
function renderMessages(messages) {
  renderedRequests = new Set(messages.filter(message => message.role === 'user').map(message => message.request_id));
  conversation.replaceChildren();
  conversation.classList.toggle('hidden', !messages.length);
  hero.classList.toggle('has-conversation', !!messages.length);
  messages.forEach(message => {
    const row = document.createElement('article');
    row.className = message.role === 'user' ? 'user-message' : 'assistant-message';
    const label = document.createElement('h2'); label.className = 'result-label';
    label.textContent = message.role === 'user' ? 'You' : 'MediNova';
    const body = document.createElement('p'); body.className = 'message-text'; body.textContent = message.content;
    row.append(label, body);
    if (message.status === 'pending' || message.status === 'failed') {
      const status = document.createElement('p'); status.className = 'message-status';
      status.textContent = message.status === 'pending' ? 'Awaiting response — retry to check progress.' : 'Response failed — retry this question.';
      row.append(status);
      if (message.role === 'user' && message.request_id) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'text-button'; button.textContent = 'Retry';
        button.addEventListener('click', () => {
          if (pending) return;
          retry = {message: message.content, conversation_id: activeId, request_id: message.request_id};
          input.value = message.content; input.focus();
        }); row.append(button);
      }
    }
    conversation.append(row);
  });
  conversation.scrollTop = conversation.scrollHeight;
}
async function loadMessages(id, epoch = generation) {
  const data = await requestJSON(`/api/conversations/${encodeURIComponent(id)}/messages`);
  if (epoch !== generation || id !== activeId) return;
  renderMessages(data.messages);
  const last = data.messages.at(-1);
  if (last?.role === 'user' && last.status !== 'complete' && last.request_id) {
    retry = {message: last.content, conversation_id: id, request_id: last.request_id};
  }
}
async function selectConversation(id) {
  if (pending) return;
  closeConversationMenu();
  const epoch = ++generation;
  activeId = id; savedConversation(id); retry = null;
  input.value = ''; composerError.textContent = '';
  renderMessages([]); setPending(true);
  try { await loadMessages(id, epoch); }
  catch (error) { if (epoch === generation) composerError.textContent = showError(error); }
  finally { if (epoch === generation) setPending(false); }
}
async function loadConversations(epoch = generation, restore = false) {
  const data = await requestJSON('/api/conversations');
  if (epoch !== generation || !user) return;
  closeConversationMenu();
  byId('conversation-list').replaceChildren();
  data.conversations.forEach(item => {
    const row = document.createElement('div'); row.className = 'conversation-item';
    const button = document.createElement('button'); button.type = 'button'; button.className = 'conversation-choice';
    button.textContent = item.title || 'New conversation'; button.disabled = pending;
    button.setAttribute('aria-current', String(item.id === activeId));
    button.addEventListener('click', () => selectConversation(item.id));
    const actions = document.createElement('button'); actions.type = 'button'; actions.className = 'icon-button conversation-actions-toggle';
    actions.textContent = '⋯'; actions.disabled = pending;
    actions.setAttribute('aria-label', `Actions for ${button.textContent}`);
    actions.setAttribute('aria-haspopup', 'menu');
    actions.setAttribute('aria-expanded', 'false');
    actions.addEventListener('click', event => { event.stopPropagation(); openConversationMenu(item, actions); });
    row.append(button, actions);
    byId('conversation-list').append(row);
  });
  if (restore) {
    const saved = savedConversation();
    const target = data.conversations.find(item => item.id === saved) || data.conversations[0];
    if (target) await selectConversation(target.id);
  }
}
async function acceptSession(payload) {
  user = payload.user; csrf = payload.csrf_token; generation += 1;
  byId('account-email').textContent = user.email;
  byId('auth-panel').classList.add('hidden');
  byId('account-controls').classList.remove('hidden');
  byId('chat-workspace').classList.remove('hidden');
  setHistoryCollapsed(false);
  setPending(false);
  await loadConversations(generation, true);
}
byId('auth-toggle').addEventListener('click', () => {
  register = !register;
  byId('auth-title').textContent = register ? 'Create your account' : 'Welcome back';
  byId('auth-submit').textContent = register ? 'Create account' : 'Sign in';
  byId('auth-toggle').textContent = register ? 'Already have an account? Sign in' : 'Create an account';
  byId('auth-password').setAttribute('autocomplete', register ? 'new-password' : 'current-password');
  byId('auth-error').textContent = '';
});
byId('auth-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (byId('auth-submit').disabled) return;
  generation += 1;
  byId('auth-submit').disabled = true; byId('auth-toggle').disabled = true; byId('auth-error').textContent = '';
  try {
    const payload = await requestJSON(`/api/auth/${register ? 'register' : 'login'}`, {method: 'POST', body: JSON.stringify({email: byId('auth-email').value.trim(), password: byId('auth-password').value})});
    byId('auth-password').value = ''; await acceptSession(payload);
  } catch (error) { (user ? composerError : byId('auth-error')).textContent = showError(error); }
  finally { byId('auth-submit').disabled = false; byId('auth-toggle').disabled = false; }
});
byId('logout').addEventListener('click', async () => {
  try { await requestJSON('/api/auth/logout', {method: 'POST'}); clearSession(); }
  catch (error) { composerError.textContent = `Sign out failed. ${showError(error)}`; }
});
byId('new-conversation').addEventListener('click', async () => {
  if (pending || !user) return;
  closeConversationMenu();
  generation += 1; activeId = null; savedConversation(null); retry = null;
  renderMessages([]); input.value = ''; composerError.textContent = ''; setPending(false); input.focus();
});
byId('toggle-history').addEventListener('click', () => setHistoryCollapsed(!historyCollapsed));
byId('conversation-list').addEventListener('scroll', closeConversationMenu);
document.addEventListener('click', event => {
  if (menuConversation && !byId('conversation-menu').contains(event.target) && event.target !== menuTrigger) closeConversationMenu();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menuConversation) {
    const trigger = menuTrigger;
    closeConversationMenu();
    trigger.focus();
  }
});
byId('rename-conversation').addEventListener('click', () => {
  if (!menuConversation || pending) return;
  const target = menuConversation;
  closeConversationMenu();
  renameTargetId = target.id;
  byId('rename-input').value = target.title;
  byId('rename-error').textContent = '';
  byId('rename-dialog').showModal();
  byId('rename-input').focus();
});
byId('rename-cancel').addEventListener('click', () => byId('rename-dialog').close());
byId('rename-dialog').addEventListener('close', () => { renameTargetId = null; });
byId('rename-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!renameTargetId || byId('rename-save').disabled) return;
  const title = byId('rename-input').value.trim();
  if (!title || title.length > 80) { byId('rename-error').textContent = 'Enter a name with up to 80 characters.'; return; }
  const epoch = generation;
  byId('rename-save').disabled = true;
  byId('rename-error').textContent = '';
  try {
    await requestJSON(`/api/conversations/${encodeURIComponent(renameTargetId)}`, {method: 'PATCH', body: JSON.stringify({title})});
    if (epoch !== generation) return;
    byId('rename-dialog').close();
    await loadConversations(epoch);
  } catch (error) { if (epoch === generation) byId('rename-error').textContent = showError(error); }
  finally { byId('rename-save').disabled = false; }
});
byId('delete-conversation').addEventListener('click', async () => {
  if (pending || !menuConversation) return;
  const target = menuConversation;
  closeConversationMenu();
  if (!confirm(`Delete "${target.title}" and all its messages?`)) return;
  const epoch = generation;
  setPending(true);
  try {
    await requestJSON(`/api/conversations/${encodeURIComponent(target.id)}`, {method: 'DELETE'});
    if (epoch !== generation) return;
    if (activeId === target.id) {
      activeId = null; retry = null; savedConversation(null); renderMessages([]);
    }
    await loadConversations(epoch);
  } catch (error) { if (epoch === generation) composerError.textContent = showError(error); }
  finally { if (epoch === generation) setPending(false); }
});
form.addEventListener('submit', async event => {
  event.preventDefault(); if (pending || !user) return;
  const message = input.value.trim(); composerError.textContent = '';
  if (!message) { input.focus(); return; }
  if (message.length > 8000) { composerError.textContent = 'Please keep your question under 8,000 characters.'; return; }
  const epoch = generation; setPending(true);
  try {
    if (!activeId) {
      const created = await requestJSON('/api/conversations', {method: 'POST', body: '{}'});
      if (epoch !== generation) return;
      activeId = created.id; savedConversation(activeId);
    }
    const request = retry?.message === message && retry.conversation_id === activeId ? retry
      : {message, conversation_id: activeId, request_id: crypto.randomUUID()};
    retry = request;
    // Show submission immediately; persisted history replaces this optimistic row.
    if (!renderedRequests.has(request.request_id)) {
    const row = document.createElement('article'); row.className = 'user-message';
    const label = document.createElement('h2'); label.className = 'result-label'; label.textContent = 'You';
    const body = document.createElement('p'); body.className = 'message-text'; body.textContent = message;
    row.append(label, body); conversation.append(row); conversation.classList.remove('hidden'); hero.classList.add('has-conversation');
    conversation.scrollTop = conversation.scrollHeight;
    renderedRequests = new Set([...renderedRequests, request.request_id]);
    }
    input.value = '';
    await requestJSON('/api/chat', {method: 'POST', body: JSON.stringify(request)});
    if (epoch !== generation) return;
    retry = null; await loadMessages(activeId, epoch); await loadConversations(epoch);
  } catch (error) {
    if (epoch !== generation) return;
    composerError.textContent = showError(error); input.value = message;
    if (activeId) { try { await loadMessages(activeId, epoch); } catch { /* Preserve the actionable request error. */ } }
  } finally { if (epoch === generation) { setPending(false); input.focus({preventScroll: true}); } }
});
quickPills.forEach(pill => pill.addEventListener('click', () => {
  if (pending || !user) return; input.value = pill.dataset.prompt; input.focus();
}));
async function checkConnection() {
  const button = byId('check-connection'); button.disabled = true;
  let state = 'offline'; let label = 'Offline';
  try {
    const data = await requestJSON('/api/health', {}, 15000);
    if (data.services?.concierge?.status === 'available') {
      state = data.status === 'ok' ? 'connected' : 'limited'; label = state === 'connected' ? 'Connected' : 'Limited';
    }
  } catch { /* The offline indicator represents health failures. */ }
  button.dataset.state = state; byId('connection-status').textContent = label;
  button.setAttribute('aria-label', `Concierge ${label.toLowerCase()}. Check connection`); button.disabled = false;
}
byId('check-connection').addEventListener('click', checkConnection);
setPending(false);
checkConnection();
const bootEpoch = generation;
(async () => {
  try {
    const payload = await requestJSON('/api/auth/me');
    if (bootEpoch === generation) await acceptSession(payload);
  } catch (error) {
    if (user) composerError.textContent = showError(error);
    else if (bootEpoch === generation) clearSession();
  }
})();
