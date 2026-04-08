import DataTable from '../components/DataTable';
import { getStockMovementList } from '../api/tabsApi';

const columns = [
  { key: '_no', label: 'No.', align: 'center' },
  { key: 'lot_no', label: 'LOT NO' },
  { key: 'sub_lt', label: 'Sub', align: 'center' },
  { key: 'movement_type', label: 'TYPE', align: 'center' },
  { key: 'description', label: 'DESCRIPTION' },
  { key: 'qty_kg', label: 'QTY(Kg)', type: 'number', align: 'right' },
  { key: 'source', label: 'SOURCE', align: 'center' },
  { key: 'created_at', label: 'DATE', align: 'center' },
];

const searchFields = [
  { key: 'keyword', label: 'Keyword', width: 200 },
];

export default function SummaryPage() {
  return <DataTable title="Stock Movement" columns={columns} fetchFn={getStockMovementList} searchFields={searchFields} />;
}
