import DataTable from '../components/DataTable';
import { getAllocationList } from '../api/tabsApi';

const columns = [
  { key: '_no', label: 'No.', align: 'center' },
  { key: 'lot_no', label: 'LOT NO' },
  { key: 'product', label: 'PRODUCT' },
  { key: 'sap_no', label: 'SAP NO' },
  { key: 'customer', label: 'CUSTOMER' },
  { key: 'sale_ref', label: 'SALE REF' },
  { key: 'qty_mt', label: 'QTY(MT)', type: 'number', align: 'right', decimals: 3 },
  { key: 'outbound_date', label: 'OUTBOUND DATE', align: 'center' },
  { key: 'status', label: 'STATUS', type: 'status', align: 'center' },
  { key: 'sub_lt', label: 'SUB LT', align: 'center' },
  { key: 'tonbag_id', label: 'TONBAG ID', align: 'center' },
  { key: 'source_file', label: 'SOURCE FILE' },
  { key: 'created_at', label: 'CREATED', align: 'center' },
  { key: 'executed_at', label: 'EXECUTED', align: 'center' },
  { key: 'cancelled_at', label: 'CANCELLED', align: 'center' },
];

const searchFields = [
  { key: 'keyword', label: 'Keyword (LOT, Customer, Sale Ref)', width: 240 },
  { key: 'status', label: 'Status (RESERVED/CANCELLED)', width: 180 },
];

export default function AllocationPage() {
  return <DataTable title="Allocation Plan" columns={columns} fetchFn={getAllocationList} searchFields={searchFields} />;
}
