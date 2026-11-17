import { AgGridReact } from "ag-grid-react";
import { themeQuartz, type ColDef } from "ag-grid-community";
import type { Flow, Unit } from "../types";

const fmt = (digits: number) => (p: { value: number }) =>
  p.value?.toLocaleString(undefined, { maximumFractionDigits: digits });

// 最適解のフロー一覧
export default function ResultTable({ flows, unit }: { flows: Flow[]; unit: Unit }) {
  const defaultColDef: ColDef<Flow> = { sortable: true, filter: true, resizable: true };
  const columnDefs: ColDef<Flow>[] = [
    { field: "stage", headerName: "区間", width: 95 },
    { field: "from_id", headerName: "出発", width: 100 },
    { field: "to_id", headerName: "到着", width: 100 },
    { field: "flow", headerName: "フロー量", width: 120, valueFormatter: fmt(2) },
    { field: "distance", headerName: `距離 (${unit})`, width: 120, valueFormatter: fmt(1) },
    { field: "unit_cost", headerName: "単位コスト", width: 120, valueFormatter: fmt(2) },
    { field: "cost", headerName: "輸送コスト", flex: 1, minWidth: 130, valueFormatter: fmt(0) },
  ];
  return (
    <AgGridReact<Flow>
      theme={themeQuartz}
      rowData={flows}
      defaultColDef={defaultColDef}
      columnDefs={columnDefs}
    />
  );
}
