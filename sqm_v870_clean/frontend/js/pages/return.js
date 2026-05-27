// SQM v8.7.0
import { apiGet } from '../api-client.js';
import { showToast } from '../toast.js';

export async function mount(container) {
  container.innerHTML = `
    <section class="page" data-page="return">
      <h2>🔄 Return</h2>
      <div class="toolbar-mini">
        <button class="btn btn-secondary" data-action="refresh-return">🔄 새로고침</button>
      </div>
      <div class="loading" id="return-loading">로딩 중…</div>
      <table class="data-table" id="return-table" style="display:none">
        <thead><tr><th>LOT</th><th>Product</th><th>수량</th><th>Return일</th><th>사유</th></tr></thead>
        <tbody id="return-tbody"></tbody>
      </table>
      <div id="return-footer" style="padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;"></div>
      <div class="empty" id="return-empty" style="display:none">표시할 데이터가 없습니다</div>
    </section>`;
  await load();
  container.querySelector('[data-action="refresh-return"]')?.addEventListener('click', load);
}

async function load() {
  const loading = document.getElementById('return-loading');
  const table = document.getElementById('return-table');
  const empty = document.getElementById('return-empty');
  const tbody = document.getElementById('return-tbody');
  try {
    loading.style.display = 'block';
    const res = await apiGet('/api/inventory?status=RETURN');
    const rows = (res?.data ?? []) || [];
    if (rows.length === 0) {
      table.style.display = 'none';
      empty.style.display = 'block';
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr><td>${r.lot ?? ''}</td><td>${r.product ?? ''}</td>
      <td>${r.bags ?? ''}</td><td>${r.date ?? ''}</td><td>${r.reason ?? ''}</td></tr>
    `).join('');
    table.style.display = '';
    empty.style.display = 'none';
    var _rfoot = document.getElementById('return-footer');
    if (_rfoot) {
      var _rbags = rows.reduce(function(s,r){return s+Number(r.bags||0);},0);
      var _rs = 'display:inline-block;padding:4px 18px;margin-right:10px;background:#FFD600;border-radius:8px;font-size:14px;color:#222;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.25);';
      _rfoot.innerHTML = '<span style="'+_rs+'">🔄 Return '+rows.length.toLocaleString('ko-KR')+' 건</span>'
        + (_rbags > 0 ? '<span style="'+_rs+'">🎒 톤백 '+_rbags.toLocaleString('ko-KR')+'</span>' : '');
    }
  } catch (e) {
    empty.textContent = `불러오기 실패: ${e.message}`;
    empty.style.display = 'block';
    showToast?.('error', 'Return 데이터 로드 실패');
  } finally {
    loading.style.display = 'none';
  }
}

export function unmount() { /* no-op */ }
