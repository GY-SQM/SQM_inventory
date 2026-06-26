/* ── Inventory Page Module ── */
'use strict';

const InventoryPage = (() => {
  const API = window.SQM_API_BASE || window.location.origin || '';
  let allData = [];
  let filtered = [];
  let currentStatus = 'ALL';
  let currentProduct = '';
  let searchQuery = '';
  let sortCol = 'lot';
  let sortAsc = true;
  let page = 1;
  const PAGE_SIZE = 50;

  function extractRows(res) {
    if (Array.isArray(res)) return res;
    if (!res) return [];
    if (Array.isArray(res.data)) return res.data;
    if (res.data && Array.isArray(res.data.rows)) return res.data.rows;
    if (res.data && Array.isArray(res.data.items)) return res.data.items;
    if (Array.isArray(res.rows)) return res.rows;
    if (Array.isArray(res.items)) return res.items;
    return [];
  }

  function normalizeInventoryRow(row) {
    const r = row || {};
    const net = Number(r.net ?? r.net_mt ?? r.net_weight_mt ?? ((r.net_weight != null) ? Number(r.net_weight) / 1000 : 0));
    const balance = Number(r.balance ?? r.current_weight_mt ?? ((r.current_weight != null) ? Number(r.current_weight) / 1000 : 0));
    return {
      ...r,
      lot: String(r.lot ?? r.lot_no ?? ''),
      sap: String(r.sap ?? r.sap_no ?? ''),
      bl: String(r.bl ?? r.bl_no ?? ''),
      container: String(r.container ?? r.container_no ?? ''),
      product: String(r.product ?? r.product_name ?? ''),
      status: String(r.status ?? ''),
      net: Number.isFinite(net) ? net : 0,
      balance: Number.isFinite(balance) ? balance : 0,
      bags: r.bags ?? r.total_bags ?? r.mxbg_pallet ?? r.tonbag_count ?? r.avail_bags ?? 0,
      date: String(r.date ?? r.inbound_date ?? r.stock_date ?? ''),
      location: String(r.location ?? r.warehouse ?? ''),
    };
  }

  async function load() {
    try {
      const res = await fetch(API + '/api/inventory');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const payload = await res.json();
      const rows = extractRows(payload);
      allData = Array.isArray(rows) ? rows.map(normalizeInventoryRow) : [];
    } catch (err) {
      console.error('[inventory] load failed', err);
      window.showToast?.('warning', '재고 API 로드 실패 — 샘플 데이터를 표시합니다.');
      const sampleRows = extractRows(window.SAMPLE_INVENTORY || []);
      allData = Array.isArray(sampleRows) ? sampleRows.map(normalizeInventoryRow) : [];
    }
    applyFilters();
  }

  function applyFilters() {
    const rows = Array.isArray(allData) ? allData : [];
    filtered = rows.filter(row => {
      if (currentStatus !== 'ALL' && row.status !== currentStatus) return false;
      if (currentProduct && row.product !== currentProduct) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!String(row.lot || '').toLowerCase().includes(q) &&
            !String(row.sap || '').toLowerCase().includes(q) &&
            !String(row.bl || '').toLowerCase().includes(q)) return false;
      }
      return true;
    });
    filtered.sort((a, b) => {
      let va = a[sortCol], vb = b[sortCol];
      if (typeof va === 'number') return sortAsc ? va - vb : vb - va;
      return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
    page = 1;
    render();
  }

  function render() {
    const tbody = document.getElementById('inventory-tbody');
    if (!tbody) return;
    const start = (page - 1) * PAGE_SIZE;
    const slice = filtered.slice(start, start + PAGE_SIZE);
    tbody.innerHTML = slice.map(row => `
      <tr onclick="InventoryPage.showDetail('${row.lot}')">
        <td onclick="event.stopPropagation()"><input type="checkbox"></td>
        <td class="mono-cell" style="color:var(--accent);font-weight:500;">${row.lot}</td>
        <td class="mono-cell">${row.sap}</td>
        <td class="mono-cell">${row.bl}</td>
        <td class="mono-cell">${row.container}</td>
        <td><span class="tag">${row.product}</span></td>
        <td>${window.STATUS_BADGE?.[row.status] || row.status}</td>
        <td class="mono-cell">${row.net.toLocaleString()}</td>
        <td class="mono-cell" style="color:${row.balance > 0 ? 'var(--status-available)' : 'var(--text-muted)'};">
          ${row.balance.toLocaleString()}
        </td>
        <td class="mono-cell">${row.bags}</td>
        <td class="mono-cell">${row.date}</td>
        <td><span class="tag">${row.location}</span></td>
        <td onclick="event.stopPropagation()">
          <button class="btn btn-ghost btn-xs" onclick="InventoryPage.showDetail('${row.lot}')">상세</button>
        </td>
      </tr>
    `).join('');

    const footer = document.querySelector('#page-inventory .card-footer span');
    if (footer) footer.textContent = `${filtered.length}건 중 ${start+1}-${Math.min(start+PAGE_SIZE, filtered.length)} 표시`;
  }

  function showDetail(lotNo) {
    window.showToast?.('info', `LOT 상세: ${lotNo}`);
    // TODO: T6에서 LOT 상세 모달 구현
  }

  function setStatus(status) {
    currentStatus = status;
    applyFilters();
  }
  function setProduct(product) {
    currentProduct = product;
    applyFilters();
  }
  function setSearch(q) {
    searchQuery = q;
    applyFilters();
  }

  return { load, setStatus, setProduct, setSearch, showDetail, render };
})();
