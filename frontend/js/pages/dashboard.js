// SQM v8.7.0
// 테이블 2개: [좌] 재고 및 확인 (판매가능/판매배정/판매화물/출고완료/Return 대기/합계/샘플)
//             [우] LOT별 (기초재고/입고/출고/기말재고/검증)
import { apiGet } from '../api-client.js';
import { showToast } from '../toast.js';

const SAMPLE = {
  products: [
    { name: 'LITHIUM CARBONATE', sellable: 200.0, reserved: 0, committed: 0,
      outbound_done: 0, return_wait: 0, total: 200.0, sample: 40 },
  ],
  lots: [
    { opening: 200.0, inbound: 0, outbound: 0, ending: 200.0, status: 'OK' },
  ],
};

export async function mount(container) {
  container.innerHTML = `
    <div class="dashboard-split">
      <div class="panel-half">
        <table class="data-table">
          <thead><tr>
            <th style="width:40px">순번</th>
            <th style="text-align:left;min-width:180px">Product</th>
            <th>판매가능</th><th>판매배정</th><th>판매화물</th>
            <th>출고완료</th><th>Return 대기</th><th>합계</th><th>샘플</th>
          </tr></thead>
          <tbody id="dash-products"></tbody>
        </table>
        <div id="dash-products-footer" style="padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;"></div>
        <div id="dash-error" class="empty" style="display:none;color:var(--status-error);padding:10px 12px;"></div>
      </div>
      <div class="panel-half">
        <table class="data-table">
          <thead><tr>
            <th style="width:40px">순번</th>
            <th>기초재고</th><th>입고</th><th>출고</th><th>기말재고</th><th>검증</th>
          </tr></thead>
          <tbody id="dash-lots"></tbody>
        </table>
        <div id="dash-lots-footer" style="padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;"></div>
      </div>
    </div>
  `;
  await loadAll();
}

function normalizeDashboardStats(res) {
  const payload = res?.data || res || {};
  if (payload.ok === false || payload.success === false) {
    throw new Error(payload.message || payload.error || 'dashboard response failed');
  }
  if (Array.isArray(payload.products) || Array.isArray(payload.lots)) {
    return {
      products: Array.isArray(payload.products) ? payload.products : [],
      lots: Array.isArray(payload.lots) ? payload.lots : [],
    };
  }
  if (Array.isArray(payload.product_matrix)) {
    return {
      products: payload.product_matrix.map((r) => ({
        name: r.product || r.name || '-',
        sellable: Number(r.available_mt || r.sellable || 0),
        reserved: Number(r.reserved_mt || r.reserved || 0),
        committed: Number(r.picked_mt || r.committed || 0),
        outbound_done: Number(r.sold_mt || r.outbound_done || 0),
        return_wait: Number(r.return_wait || 0),
        total: Number(r.total_mt || r.total || 0),
        sample: Number(r.sample || r.sample_bags || 0),
      })),
      lots: Array.isArray(payload.lot_weight_summary) ? payload.lot_weight_summary : [],
    };
  }
  throw new Error('invalid dashboard response shape');
}

async function loadAll() {
  let data = SAMPLE;
  const errEl = document.getElementById('dash-error');
  if (errEl) { errEl.style.display = 'none'; errEl.textContent = ''; }
  try {
    const res = await apiGet('/api/dashboard/stats');
    if (res?.ok === false || res?.success === false) throw new Error(res.message || res.error || 'dashboard response failed');
    data = normalizeDashboardStats(res);
  } catch (e) {
    console.error('[dashboard] load failed', e);
    showToast?.('error', '대시보드 데이터 로드 실패');
    if (errEl) { errEl.textContent = `대시보드 로드 실패: ${e.message}`; errEl.style.display = 'block'; }
  }
  const products = Array.isArray(data.products) ? data.products : SAMPLE.products;
  const lots = Array.isArray(data.lots) ? data.lots : SAMPLE.lots;
  renderProducts(products);
  renderLots(lots);
}

function num(v) {
  if (typeof v !== 'number') return v ?? '-';
  return v.toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function renderProducts(rows) {
  const tbody = document.getElementById('dash-products');
  if (!tbody) return;
  const total = rows.reduce((a, r) => ({
    sellable: a.sellable + (r.sellable || 0),
    reserved: a.reserved + (r.reserved || 0),
    committed: a.committed + (r.committed || 0),
    outbound_done: a.outbound_done + (r.outbound_done || 0),
    return_wait: a.return_wait + (r.return_wait || 0),
    total: a.total + (r.total || 0),
    sample: a.sample + (r.sample || 0),
  }), { sellable:0, reserved:0, committed:0, outbound_done:0, return_wait:0, total:0, sample:0 });
  tbody.innerHTML = rows.map((r, i) => `
    <tr>
      <td>${i+1}</td>
      <td style="text-align:left">${r.name}</td>
      <td>${num(r.sellable)}</td>
      <td>${num(r.reserved)}</td>
      <td>${num(r.committed)}</td>
      <td>${num(r.outbound_done)}</td>
      <td>${num(r.return_wait)}</td>
      <td><b>${num(r.total)}</b></td>
      <td>${r.sample ?? '-'}</td>
    </tr>
  `).join('') + `
    <tr class="total-row">
      <td></td><td style="text-align:left"><b>합계</b></td>
      <td>${num(total.sellable)}</td>
      <td>${num(total.reserved)}</td>
      <td>${num(total.committed)}</td>
      <td>${num(total.outbound_done)}</td>
      <td>${num(total.return_wait)}</td>
      <td>${num(total.total)}</td>
      <td>${total.sample}</td>
    </tr>
  `;
  /* v8.7.0: 노란 배지 footer */
  var _dpfoot = document.getElementById('dash-products-footer');
  if (_dpfoot) {
    var _dps = 'display:inline-block;padding:4px 18px;margin-right:10px;background:#FFD600;border-radius:8px;font-size:14px;color:#222;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.25);';
    _dpfoot.innerHTML =
        '<span style="' + _dps + '">📦 ' + rows.length + ' Product</span>'
      + '<span style="' + _dps + '">⚖ 합계 ' + num(total.total) + ' MT</span>'
      + (total.sample > 0 ? '<span style="' + _dps + '">🧪 샘플 ' + total.sample + '</span>' : '');
  }
}

function renderLots(rows) {
  const tbody = document.getElementById('dash-lots');
  if (!tbody) return;
  tbody.innerHTML = rows.map((r, i) => `
    <tr>
      <td>${i+1}</td>
      <td>${num(r.opening)}</td>
      <td>${num(r.inbound)}</td>
      <td>${num(r.outbound)}</td>
      <td>${num(r.ending)}</td>
      <td><span class="badge-ok" style="color:#2e7d32;font-weight:700">${r.status || 'OK'}</span></td>
    </tr>
  `).join('');
  /* v8.7.0: 노란 배지 footer */
  var _dlfoot = document.getElementById('dash-lots-footer');
  if (_dlfoot) {
    var _dls = 'display:inline-block;padding:4px 18px;margin-right:10px;background:#FFD600;border-radius:8px;font-size:14px;color:#222;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.25);';
    var totEnd = rows.reduce(function(a, r) { return a + Number(r.ending || 0); }, 0);
    _dlfoot.innerHTML =
        '<span style="' + _dls + '">📋 LOT ' + rows.length + ' 건</span>'
      + (totEnd > 0 ? '<span style="' + _dls + '">기말재고 ' + num(totEnd) + ' MT</span>' : '');
  }
}

export function unmount() {}
