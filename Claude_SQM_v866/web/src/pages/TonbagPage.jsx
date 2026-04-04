import DataTable from '../components/DataTable';
import { getTonbagList } from '../api/tabsApi';

const columns = [
  { key: '_no', label: 'No.', align: 'center' },
  { key: 'lot_no', label: 'LOT NO' },
  { key: 'tonbag_no', label: 'TONBAG NO', align: 'center' },
  { key: 'tonbag_uid', label: 'UID' },
  { key: 'sap_no', label: 'SAP NO' },
  { key: 'bl_no', label: 'BL NO' },
  { key: 'product', label: 'PRODUCT' },
  { key: 'status', label: 'STATUS', type: 'status', align: 'center' },
  { key: 'weight', label: 'Weight(Kg)', type: 'number', align: 'right' },
  { key: 'current_weight', label: 'Balance(Kg)', type: 'number', align: 'right' },
  { key: 'location', label: 'LOCATION', align: 'center' },
  { key: 'container_no', label: 'CONTAINER' },
  { key: 'net_weight', label: 'NET(Kg)', type: 'number', align: 'right' },
  { key: 'salar_invoice_no', label: 'INVOICE NO' },
  { key: 'ship_date', label: 'SHIP DATE', align: 'center' },
  { key: 'arrival_date', label: 'ARRIVAL', align: 'center' },
  { key: 'con_return', label: 'CON RETURN', align: 'center' },
  { key: 'free_time', label: 'FREE TIME', align: 'center' },
  { key: 'warehouse', label: 'WAREHOUSE', align: 'center' },
];

const searchFields = [
  { key: 'keyword', label: 'Keyword', width: 180 },
  { key: 'lot_no', label: 'LOT No', width: 120 },
  { key: 'status', label: 'Status', width: 100 },
];

export default function TonbagPage() {
  return <DataTable title="Tonbag List" columns={columns} fetchFn={getTonbagList} searchFields={searchFields} />;
}
