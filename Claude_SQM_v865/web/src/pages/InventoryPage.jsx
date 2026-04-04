import { useEffect, useState } from 'react';
import { getInventoryFilters, searchInventory } from '../api/inventoryApi';

export default function InventoryPage() {
  const [filters, setFilters] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState({
    keyword: '', status: '', product_name: '', page: 1,
  });

  useEffect(() => {
    getInventoryFilters()
      .then(setFilters)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    setLoading(true);
    searchInventory(search)
      .then(setResults)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [search]);

  const onSearch = (e) => {
    e.preventDefault();
    setSearch((prev) => ({ ...prev, page: 1 }));
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>Inventory Search</h2>

      <form onSubmit={onSearch} style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input
          placeholder="Keyword (LOT, UID, BL...)"
          value={search.keyword}
          onChange={(e) => setSearch((s) => ({ ...s, keyword: e.target.value }))}
          style={{ padding: 6, width: 200 }}
        />
        <select
          value={search.status}
          onChange={(e) => setSearch((s) => ({ ...s, status: e.target.value, page: 1 }))}
          style={{ padding: 6 }}
        >
          <option value="">All Status</option>
          {filters?.statuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={search.product_name}
          onChange={(e) => setSearch((s) => ({ ...s, product_name: e.target.value, page: 1 }))}
          style={{ padding: 6 }}
        >
          <option value="">All Products</option>
          {filters?.products.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <button type="submit" style={{ padding: '6px 16px' }}>Search</button>
      </form>

      {error && <div style={{ color: 'red', marginBottom: 8 }}>Error: {error}</div>}
      {loading && <div>Loading...</div>}

      {results && !loading && (
        <>
          <p>Total: {results.total} rows (page {results.page})</p>
          <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th>LOT No</th>
                <th>UID</th>
                <th>Product</th>
                <th>Status</th>
                <th>Location</th>
                <th>Weight (kg)</th>
                <th>Sample</th>
              </tr>
            </thead>
            <tbody>
              {results.rows.map((row) => (
                <tr key={row.tonbag_id}>
                  <td>{row.lot_no}</td>
                  <td>{row.tonbag_uid}</td>
                  <td>{row.product_name}</td>
                  <td>{row.status}</td>
                  <td>{row.location}</td>
                  <td style={{ textAlign: 'right' }}>{row.weight_kg.toFixed(1)}</td>
                  <td>{row.is_sample ? 'Y' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button
              disabled={results.page <= 1}
              onClick={() => setSearch((s) => ({ ...s, page: s.page - 1 }))}
            >Prev</button>
            <span>Page {results.page}</span>
            <button
              disabled={results.rows.length < 50}
              onClick={() => setSearch((s) => ({ ...s, page: s.page + 1 }))}
            >Next</button>
          </div>
        </>
      )}
    </div>
  );
}
