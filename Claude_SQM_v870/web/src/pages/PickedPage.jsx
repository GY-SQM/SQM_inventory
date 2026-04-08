import DataTable from '../components/DataTable';
import { getPickedList } from '../api/tabsApi';

const columns = [
  { key: '_no', label: 'No.', align: 'center' },
  { key: 'lot_no', label: 'LOT NO' },
  { key: 'product', label: 'PRODUCT' },
  { key: 'tonbag_uid', label: 'TONBAG UID' },
  { key: 'picking_no', label: 'PICKING NO' },
  { key: 'customer', label: 'CUSTOMER' },
  { key: 'qty_kg', label: 'QTY(Kg)', type: 'number', align: 'right' },
  { key: 'qty_mt', label: 'QTY(MT)', type: 'number', align: 'right', decimals: 3 },
  { key: 'status', label: 'STATUS', type: 'status', align: 'center' },
  { key: 'creation_date', label: 'DATE', align: 'center' },
  { key: 'sub_lt', label: 'SUB LT', align: 'center' },
];

export default function PickedPage() {
  return <DataTable title="Picked (Picking)" columns={columns} fetchFn={getPickedList} />;
}
