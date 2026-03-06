let gameId = null;

const elLog = document.getElementById('log');
const elForm = document.getElementById('cmdForm');
const elInput = document.getElementById('cmdInput');
const elNew = document.getElementById('newGame');

function appendToLog(text) {
  if (!text) return;
  const prior = elLog.textContent || '';
  elLog.textContent = prior ? prior + '\n\n' + text : text;
  elLog.scrollTop = elLog.scrollHeight;
}

async function postJson(url, body) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${t}`);
  }
  return await resp.json();
}

async function newGame() {
  elLog.textContent = '';
  appendToLog('Generating a new adventure...');
  const data = await postJson('/api/new_game');
  gameId = data.state.gameId;
  elLog.textContent = '';
  appendToLog(data.text);
}

async function sendCommand(cmd) {
  if (!gameId) {
    await newGame();
  }
  appendToLog('> ' + cmd);
  const data = await postJson('/api/command', { gameId, command: cmd });
  appendToLog(data.text);
}

elForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const cmd = (elInput.value || '').trim();
  if (!cmd) return;
  elInput.value = '';
  try {
    await sendCommand(cmd);
  } catch (err) {
    appendToLog(String(err));
  } finally {
    elInput.focus();
  }
});

elNew.addEventListener('click', async () => {
  try {
    await newGame();
    elInput.focus();
  } catch (err) {
    appendToLog(String(err));
  }
});

// Start fresh each page load (no persistence).
newGame().catch((err) => appendToLog(String(err)));
