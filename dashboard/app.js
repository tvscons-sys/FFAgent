const apiBaseUrl = window.API_BASE_URL || 'http://127.0.0.1:8000';
const requestRows = document.getElementById('request-rows');

document.getElementById('refresh').addEventListener('click', loadMetrics);
document.getElementById('date-range').addEventListener('change', loadMetrics);

async function loadMetrics() {
  const days = document.getElementById('date-range').value;
  try {
    const response = await fetch(`${apiBaseUrl}/admin/metrics?days=${days}`);
    if (!response.ok) throw new Error('metrics unavailable');
    const data = await response.json();
    const metrics = data.kpis || {};
    setText('metrics-status', 'Live');
    setText('updated', `Updated ${new Date().toLocaleTimeString()}`);
    setText('total-questions', format(metrics.total_questions));
    setText('total-tokens', compact(metrics.total_tokens));
    setText('estimated-cost', metrics.estimated_cost_inr ? `₹${format(metrics.estimated_cost_inr, 4)}` : 'Free tier');
    setText('average-latency', `${format(metrics.average_latency_ms)}ms`);
    setText('retrieval-latency', `${format(metrics.average_retrieval_latency_ms)}ms`);
    setText('ticket-count', format(metrics.ticket_count));
    renderRows(data.recent_questions || []);
  } catch (error) {
    setText('metrics-status', 'Backend offline');
    setText('updated', 'Waiting for backend');
  }
}

function renderRows(rows) {
  requestRows.innerHTML = rows.length ? rows.map((row) => `<tr><td><div class="question-cell"><i></i><span title="${escapeHtml(row.query)}">${escapeHtml(row.query)}</span></div></td><td>${formatTime(row.created_at)}</td><td class="model-cell">${escapeHtml(row.model)}</td><td>${format(row.input_tokens)}</td><td>${format(row.output_tokens)}</td><td><strong>${format(row.total_tokens)}</strong></td><td class="cost-cell">${formatCost(row.estimated_cost_inr)}</td><td>${format(row.retrieval_latency_ms)}ms</td><td class="time-cell">${format(row.latency_ms)}ms</td><td>${format(row.retrieved_count)}</td></tr>`).join('') : '<tr><td class="empty" colspan="10">Waiting for the first question.</td></tr>';
}

function setText(id, value) { document.getElementById(id).textContent = value; }
function format(value, decimals = 0) { return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: decimals }); }
function compact(value) { const amount = Number(value || 0); return amount >= 1000000 ? `${(amount / 1000000).toFixed(1)}M` : format(amount); }
function formatTime(value) { return value ? new Date(value).toLocaleString() : '-'; }
function formatCost(value) { return Number(value || 0) ? `₹${format(value, 4)}` : 'Free tier'; }
function escapeHtml(value) { return String(value || '').replace(/[&<>\'\"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]); }

loadMetrics();
window.setInterval(loadMetrics, 5000);
