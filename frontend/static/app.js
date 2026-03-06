let gameId = null;

const MAX_LOG_MESSAGES = 200;

let transcript = [];

const elLog = document.getElementById('log');
const elSheet = document.getElementById('sheet');
const elDungeonMap = document.getElementById('dungeonMap');
const elRoomMap = document.getElementById('roomMap');
const elForm = document.getElementById('cmdForm');
const elInput = document.getElementById('cmdInput');
const elNew = document.getElementById('newGame');

function appendToLog(text) {
  if (!text) return;
  transcript.push(String(text));
  if (transcript.length > MAX_LOG_MESSAGES) {
    transcript = transcript.slice(-MAX_LOG_MESSAGES);
  }
  renderLog();
}

function clearLog() {
  transcript = [];
  renderLog();
}

function renderLog() {
  elLog.textContent = transcript.join('\n\n');
  elLog.scrollTop = elLog.scrollHeight;
}

function setText(el, text) {
  if (!el) return;
  el.textContent = text || '';
}

function formatMod(score) {
  const mod = Math.floor((Number(score || 10) - 10) / 2);
  return mod >= 0 ? `+${mod}` : String(mod);
}

function renderSheet(state) {
  if (!state || !state.player) return '';
  if (state.phase !== 'adventure') return '';
  const p = state.player;
  const a = p.abilityScores || {};
  const eq = p.equipped || {};
  const header = `${p.name || 'Adventurer'} — L${p.level || 1} ${p.species || ''} ${p.class || ''}`.trim();
  const gold = p.gold ?? 0;
  const line1 = `HP ${p.hp}/${p.maxHp}   AC ${p.ac}   Proficiency +${p.proficiencyBonus ?? 2}   Gold ${gold}gp`;
  const slots = p.maxSpellSlots ? `${p.spellSlots}/${p.maxSpellSlots}` : '-';
  const line2 = `Spell Slots: ${slots}`;
  const xp = p.xp ?? 0;
  const next = (p.nextLevelXp != null) ? p.nextLevelXp : null;
  const line3 = `XP ${xp}${next ? `   Next Level: ${next}` : ''}`;
  const ab = [
    `STR ${a.str ?? 10} (${formatMod(a.str)})`,
    `DEX ${a.dex ?? 10} (${formatMod(a.dex)})`,
    `CON ${a.con ?? 10} (${formatMod(a.con)})`,
    `INT ${a.int ?? 10} (${formatMod(a.int)})`,
    `WIS ${a.wis ?? 10} (${formatMod(a.wis)})`,
    `CHA ${a.cha ?? 10} (${formatMod(a.cha)})`,
  ].join('\n');
  const equipped = `Equipped:\n  melee: ${eq.melee || '-'}\n  ranged: ${eq.ranged || '-'}\n  armor: ${eq.armor || '-'}\n  shield: ${eq.shield || '-'}`;
  const spells = (p.spells && p.spells.length)
    ? `Spells:\n  - ${p.spells.join('\n  - ')}`
    : 'Spells:\n  - (none)';
  const inv = (p.inventory && p.inventory.length)
    ? `Inventory:\n  - ${p.inventory.join('\n  - ')}`
    : 'Inventory:\n  - (empty)';
  return [header, line1, line2, line3, '', ab, '', equipped, '', spells, '', inv].join('\n');
}

function renderFromState(state) {
  setText(elSheet, renderSheet(state));
  if (state && state.phase === 'adventure') {
    setText(elDungeonMap, state.dungeonMap || '');
    setText(elRoomMap, state.roomMap || '');
  } else {
    setText(elDungeonMap, '');
    setText(elRoomMap, '');
  }
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
  clearLog();
  setText(elSheet, '');
  setText(elDungeonMap, '');
  setText(elRoomMap, '');
  appendToLog('Generating a new adventure...');
  const data = await postJson('api/new_game');
  gameId = data.state.gameId;
  clearLog();
  appendToLog(data.text);
  renderFromState(data.state);
}

async function sendCommand(cmd) {
  if (!gameId) {
    await newGame();
  }
  appendToLog('> ' + cmd);
  const data = await postJson('api/command', { gameId, command: cmd });
  appendToLog(data.text);
  renderFromState(data.state);
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
