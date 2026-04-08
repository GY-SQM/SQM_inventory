import DataTable from '../components/DataTable';
import { getOutboundList } from '../api/tabsApi';

const columns = [
  { key: '_no', label: 'No.', align: 'center' },
  { key: 'outbound_no', label: 'OUTBOUND NO' },
  { key: 'sale_ref', label: 'SALE REF' },
  { key: 'customer', label: 'CUSTOMER' },
  { key: 'total_qty_mt', label: 'QTY(MT)', type: 'number', align: 'right', decimals: 3 },
  { key: 'outbound_date', label: 'OUTBOUND DATE', align: 'center' },
  { key: 'destination', label: 'DESTINATION' },
  { key: 'status', label: 'STATUS', type: 'status', align: 'center' },
  { key: 'remarks', label: 'REMARKS' },
  { key: 'created_at', label: 'CREATED', align: 'center' },
];

export default function OutboundPage() {
  return <DataTable title="Outbound Schedule" columns={columns} fetchFn={getOutboundList} />;
}
