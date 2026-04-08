import DataTable from '../components/DataTable';
import { getMoveLogList } from '../api/tabsApi';

const columns = [
  { key: '_no', label: 'No.', align: 'center' },
  { key: 'lot_no', label: 'LOT NO' },
  { key: 'sub_lt', label: 'Sub', align: 'center' },
  { key: 'from_location', label: 'FROM', align: 'center' },
  { key: 'to_location', label: 'TO', align: 'center' },
  { key: 'reason_code', label: 'REASON', align: 'center' },
  { key: 'source', label: 'SOURCE', align: 'center' },
  { key: 'operator', label: 'OPERATOR' },
  { key: 'note', label: 'NOTE' },
  { key: 'created_at', label: 'DATE', align: 'center' },
];

const searchFields = [
  { key: 'keyword', label: 'Keyword', width: 200 },
];

export default function MovePage() {
  return <DataTable title="Move Log" columns={columns} fetchFn={getMoveLogList} searchFields={searchFields} />;
}
