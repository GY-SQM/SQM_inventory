import DataTable from '../components/DataTable';
import { getAuditLogList } from '../api/tabsApi';

const columns = [
  { key: '_no', label: 'No.', align: 'center' },
  { key: 'event_type', label: 'EVENT TYPE' },
  { key: 'event_data', label: 'EVENT DATA' },
  { key: 'created_at', label: 'DATE', align: 'center' },
];

const searchFields = [
  { key: 'keyword', label: 'Keyword', width: 200 },
];

export default function LogPage() {
  return <DataTable title="Audit Log" columns={columns} fetchFn={getAuditLogList} searchFields={searchFields} />;
}
