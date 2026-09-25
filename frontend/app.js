const form = document.getElementById('ask-form');
const input = document.getElementById('medical-input');
const resultBox = document.getElementById('chat-result');
const resultText = document.getElementById('result-text');
const resultMeta = document.getElementById('result-meta');
const submitButton = form.querySelector('button[type="submit"]');
const quickPills = document.querySelectorAll('.action-pill');
const connectionStatus = document.getElementById('connection-status');
const checkConnectionButton = document.getElementById('check-connection');
const conversation = document.getElementById('conversation');
const composerError = document.getElementById('composer-error');
const hero = document.querySelector('.hero');
let pending = false;
let completedReply = null;

function appendMessage(role, text, metadata = '', isError = false) {
  const row = document.createElement('article');
  row.className = role === 'user' ? 'user-message' : 'assistant-message';
  row.classList.toggle('is-error', isError);
  const label = document.createElement('h2');
  label.className = 'result-label';
  label.textContent = role === 'user' ? 'You' : 'MediNova';
  const body = document.createElement('p');
  body.className = 'message-text';
  body.textContent = text;
  row.append(label, body);
  if (metadata) {
    const meta = document.createElement('p');
    meta.className = 'result-meta';
    meta.textContent = metadata;
    row.append(meta);
  }
  conversation.insertBefore(row, resultBox);
}

function startTurn(message) {
  if (completedReply) {
    appendMessage('assistant', completedReply.text, completedReply.metadata, completedReply.isError);
  }
  conversation.classList.remove('hidden');
  hero.classList.toggle('has-conversation', true);
  appendMessage('user', message);
  input.value = '';
  setResult('Thinking...');
}

function setResult(message, isError = false) {
  resultBox.classList.remove('hidden');
  resultBox.classList.toggle('is-error', isError);
  resultText.textContent = message;
  resultMeta.textContent = '';
  completedReply = { text: message, metadata: '', isError };
}

async function requestJSON(url, options = {}, timeoutMs = 180000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new Error('The concierge is unavailable. Please try again.');
    }
    if (!response.ok) {
      const detail = payload?.detail;
      const message = typeof detail === 'string' ? detail
        : Array.isArray(detail) ? detail.map(item => item.msg).filter(Boolean).join(' ')
          : detail?.message;
      throw new Error(message || 'The concierge is unavailable. Please try again.');
    }
    return payload;
  } finally {
    clearTimeout(timer);
  }
}

function connectionState(state, label, description) {
  checkConnectionButton.dataset.state = state;
  connectionStatus.textContent = label;
  checkConnectionButton.setAttribute('title', description + ' Click to check again.');
  checkConnectionButton.setAttribute('aria-label', description + ' Check connection');
}

async function checkConnection() {
  checkConnectionButton.disabled = true;
  connectionState('checking', 'Checking', 'Checking concierge connection.');
  try {
    const payload = await requestJSON('/api/health', {}, 15000);
    const services = payload?.services || {};
    const missing = ['policy', 'research'].filter(name => services[name]?.status !== 'available');
    if (services.concierge?.status !== 'available') {
      connectionState('offline', 'Offline', 'Concierge unavailable.');
    } else if (missing.length || payload.status !== 'ok') {
      connectionState('limited', 'Limited', `Concierge reachable. Unavailable specialists: ${missing.join(', ') || 'service degraded'}.`);
    } else {
      connectionState('connected', 'Connected', 'Concierge connected. Policy and research agents available.');
    }
  } catch {
    connectionState('offline', 'Offline', 'Cannot reach the concierge server.');
  } finally {
    checkConnectionButton.disabled = false;
  }
}

function setPending(value) {
  pending = value;
  submitButton.disabled = value;
  input.disabled = value;
  quickPills.forEach(pill => { pill.disabled = value; });
  submitButton.textContent = value ? 'Thinking...' : 'Send';
  form.setAttribute('aria-busy', String(value));
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (pending) return;
  const message = input.value.trim();
  composerError.textContent = '';
  if (!message) { input.focus(); return; }
  if (message.length > 8000) {
    composerError.textContent = 'Please keep your question under 8,000 characters.';
    input.focus();
    return;
  }
  setPending(true);
  startTurn(message);
  try {
    const payload = await requestJSON('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    if (typeof payload?.answer !== 'string' || !payload.answer.trim()) {
      throw new Error('The concierge returned an empty answer. Please try again.');
    }
    setResult(payload.answer);
    const agents = Array.isArray(payload.agents_used) ? payload.agents_used.filter(agent => typeof agent === 'string') : [];
    const duration = Number.isFinite(payload.latency_ms) && payload.latency_ms >= 0
      ? `${(payload.latency_ms / 1000).toFixed(1)}s` : '';
    resultMeta.textContent = [agents.length ? `Specialists consulted: ${agents.join(', ')}` : 'Answered by concierge', duration].filter(Boolean).join(' · ');
    completedReply = { ...completedReply, metadata: resultMeta.textContent };
  } catch (error) {
    const errorMessage = error.name === 'AbortError'
      ? 'The request timed out. The agent may still be working; wait a moment before retrying.'
      : error.name === 'TypeError'
        ? 'Unable to connect. Check your connection and retry.'
        : error.message || 'The concierge is unavailable right now.';
    setResult(errorMessage, true);
    input.value = message;
  } finally {
    setPending(false);
    input.focus({ preventScroll: true });
  }
});

quickPills.forEach(pill => {
  pill.addEventListener('click', () => {
    if (pending) return;
    input.value = pill.dataset.prompt;
    input.focus();
  });
});
checkConnectionButton.addEventListener('click', checkConnection);
checkConnection();
