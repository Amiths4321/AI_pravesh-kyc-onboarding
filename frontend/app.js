const apiBaseInput = document.getElementById('apiBase');
const connStatus = document.getElementById('connStatus');
const queueList = document.getElementById('queueList');
const statusFilter = document.getElementById('statusFilter');
const detailPanel = document.getElementById('detailPanel');
const stampOverlay = document.getElementById('stampOverlay');

let currentAppId = null;

function apiBase() {
  return apiBaseInput.value.replace(/\/+$/, '');
}

function fmtINR(n) {
  return '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

async function getJSON(path) {
  const res = await fetch(apiBase() + path);
  if (!res.ok) throw new Error('GET failed: ' + path);
  return res.json();
}

async function postJSON(path, body) {
  const res = await fetch(apiBase() + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('POST failed: ' + path);
  return res.json();
}

function setConn(ok) {
  connStatus.classList.remove('ok', 'err');
  connStatus.classList.add(ok ? 'ok' : 'err');
  connStatus.innerHTML = `<i class="dot"></i> ${ok ? 'connected' : 'unreachable'}`;
}

// ---------------------------------------------------------------------
// Queue
// ---------------------------------------------------------------------

async function loadQueue() {
  try {
    const data = await getJSON(`/api/applications?status=${statusFilter.value}`);
    setConn(true);
    renderQueue(data.items);
  } catch (e) {
    setConn(false);
    queueList.innerHTML = '<p class="queue-empty">Could not load the queue. Check the API base above.</p>';
  }
}

function renderQueue(items) {
  if (!items.length) {
    queueList.innerHTML = '<p class="queue-empty">No applications in this view.</p>';
    return;
  }
  queueList.innerHTML = items.map(item => `
    <div class="queue-item ${item.app_id === currentAppId ? 'selected' : ''}" data-id="${item.app_id}">
      <div class="queue-item-top">
        <span class="queue-item-name">${item.applicant_name}</span>
        <span class="decision-chip ${item.decision}">${item.decision.replace('_', ' ')}</span>
      </div>
      <div class="queue-item-meta">
        ${item.occupation_type} · score ${item.score}
        <span class="risk-chip ${item.risk_category}">${item.risk_category}</span>
      </div>
    </div>
  `).join('');

  queueList.querySelectorAll('.queue-item').forEach(el => {
    el.addEventListener('click', () => loadDetail(el.getAttribute('data-id')));
  });
}

// ---------------------------------------------------------------------
// Detail
// ---------------------------------------------------------------------

async function loadDetail(appId) {
  currentAppId = appId;
  try {
    const data = await getJSON(`/api/applications/${appId}`);
    setConn(true);
    renderDetail(data);
    queueList.querySelectorAll('.queue-item').forEach(el => {
      el.classList.toggle('selected', el.getAttribute('data-id') === appId);
    });
  } catch (e) {
    setConn(false);
  }
}

function docCard(label, valid, number, reason) {
  return `
    <div class="doc-card ${valid ? 'valid' : 'invalid'}">
      <div class="doc-card-top">
        <span class="doc-card-label">${label}</span>
        <span class="doc-card-icon">${valid ? '✅' : '❌'}</span>
      </div>
      <div class="doc-card-number">${number}</div>
      <div class="doc-card-reason">${reason}</div>
    </div>`;
}

function renderDetail(data) {
  const a = data.applicant;
  const ev = data.evaluation;

  const decidedNote = a.status !== 'PENDING'
    ? `<div class="decided-note">This application has already been marked <strong>${a.status}</strong> in this demo session.</div>`
    : '';

  const flagFields = [];
  if (a.is_pep) flagFields.push('<div class="applicant-field"><div class="applicant-field-label">PEP status</div><div class="applicant-field-value">Yes</div></div>');
  if (a.cash_intensive_business) flagFields.push('<div class="applicant-field"><div class="applicant-field-label">Cash-intensive biz</div><div class="applicant-field-value">Yes</div></div>');
  if (a.is_nri_or_foreign) flagFields.push('<div class="applicant-field"><div class="applicant-field-label">NRI / Foreign</div><div class="applicant-field-value">Yes</div></div>');

  detailPanel.innerHTML = `
    <div class="detail-head">
      <div>
        <h1>${a.name} <span style="font-family: var(--font-mono); font-size: 13px; color: var(--ink-faint);">${a.app_id}</span></h1>
        <div class="sub">${a.occupation_type} · Annual income ${fmtINR(a.annual_income)} · Age ${a.age}</div>
      </div>
      <span class="decision-chip ${ev.decision}" id="headerDecisionChip" style="font-size: 13px; padding: 5px 14px;">${ev.decision.replace('_',' ')}</span>
    </div>

    <div class="applicant-grid">
      <div class="applicant-field"><div class="applicant-field-label">ID-linked name</div><div class="applicant-field-value" style="font-size:12px;">${a.id_linked_name}</div></div>
      <div class="applicant-field"><div class="applicant-field-label">Name match</div><div class="applicant-field-value">${ev.name_match_score}%</div></div>
      <div class="applicant-field"><div class="applicant-field-label">Photo match</div><div class="applicant-field-value">${a.photo_match_score}%</div></div>
      <div class="applicant-field"><div class="applicant-field-label">Stated city / PIN</div><div class="applicant-field-value" style="font-size:12px;">${a.stated_city} / ${a.pincode}</div></div>
      ${flagFields.join('')}
    </div>

    <div class="doc-cards">
      ${docCard('PAN', ev.pan_result.valid, a.pan, ev.pan_result.reason + (ev.pan_result.holder_type ? ` (${ev.pan_result.holder_type})` : ''))}
      ${docCard('Aadhaar', ev.aadhaar_result.valid, a.aadhaar, ev.aadhaar_result.reason)}
    </div>

    <div class="gate-failures" id="gateFailures"></div>

    <div class="risk-box">
      <div class="risk-box-top">
        <h3>Risk category</h3>
        <span class="risk-chip ${ev.risk_category}">${ev.risk_category}</span>
      </div>
      <ul>${ev.risk_reasons.map(r => `<li>${r}</li>`).join('') || '<li>No elevated risk indicators</li>'}</ul>
    </div>

    <div class="reasons-list">
      <h3>Scorecard — score ${ev.score}/100</h3>
      <div id="reasonsBody"></div>
    </div>

    <div class="action-row">
      <button class="btn-verify" id="btnVerify">Verify &amp; open account</button>
      <button class="btn-resubmit" id="btnResubmit">Request resubmission</button>
      <button class="btn-reject" id="btnReject">Reject</button>
    </div>
    ${decidedNote}
  `;

  renderGateAndReasons(ev);

  document.getElementById('btnVerify').addEventListener('click', () => decide(a.app_id, 'VERIFIED', 'VERIFIED'));
  document.getElementById('btnResubmit').addEventListener('click', () => decide(a.app_id, 'RESUBMISSION_REQUESTED', 'RESUBMIT'));
  document.getElementById('btnReject').addEventListener('click', () => decide(a.app_id, 'REJECTED', 'REJECTED'));
}

function renderGateAndReasons(ev) {
  const gateBox = document.getElementById('gateFailures');
  gateBox.innerHTML = ev.gate_failures.length
    ? ev.gate_failures.map(g => `<div class="gate-failure">⛔ ${g}</div>`).join('')
    : '';

  const reasonsBody = document.getElementById('reasonsBody');
  reasonsBody.innerHTML = ev.reasons.map(r => `
    <div class="reason-row"><span>${r.label}</span><span class="reason-points">+${r.points}</span></div>
  `).join('');
}

// ---------------------------------------------------------------------
// Decision + stamp animation
// ---------------------------------------------------------------------

function showStamp(text, colorVar) {
  stampOverlay.textContent = text;
  stampOverlay.style.color = colorVar;
  stampOverlay.hidden = false;
  stampOverlay.classList.remove('show');
  // restart animation cleanly
  void stampOverlay.offsetWidth;
  stampOverlay.classList.add('show');
  setTimeout(() => { stampOverlay.hidden = true; stampOverlay.classList.remove('show'); }, 1400);
}

async function decide(appId, decisionValue, stampText) {
  const stampColor = stampText === 'VERIFIED' ? 'var(--stamp-green)' : 'var(--stamp-red)';
  showStamp(stampText, stampColor);
  try {
    await postJSON(`/api/applications/${appId}/decide`, { decision: decisionValue });
    await loadQueue();
    setTimeout(() => loadDetail(appId), 500); // let the stamp animation read clearly before refreshing
  } catch (e) {
    setConn(false);
  }
}

statusFilter.addEventListener('change', loadQueue);

loadQueue();
setInterval(() => { if (!currentAppId) loadQueue(); }, 5000);
