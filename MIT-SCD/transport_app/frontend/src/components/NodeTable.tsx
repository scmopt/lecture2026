import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { themeQuartz, type ColDef, type CellValueChangedEvent } from "ag-grid-community";

interface Row {
  _key: string;
}

interface Props<T extends Row> {
  rows: T[];
  quantityField: string; // "demand" または "supply"
  quantityLabel: string;
  onChange: (rows: T[]) => void;
}

// 顧客・サプライヤーを表で編集するテーブル
export default function NodeTable<T extends Row>({ rows, quantityField, quantityLabel, onChange }: Props<T>) {
  const columnDefs = useMemo<ColDef<T>[]>(
    () => [
      { field: "ID" as never, headerName: "ID", width: 90, editable: true },
      { field: "name" as never, headerName: "名前", flex: 1, minWidth: 120, editable: true },
      { field: "lat" as never, headerName: "緯度", width: 110, editable: true, cellDataType: "number" },
      { field: "lon" as never, headerName: "経度", width: 110, editable: true, cellDataType: "number" },
      { field: quantityField as never, headerName: quantityLabel, width: 120, editable: true, cellDataType: "number" },
      {
        headerName: "",
        width: 70,
        sortable: false,
        cellRenderer: (p: { data: T }) => (
          <button
            className="text-xs text-red-600 hover:underline"
            onClick={() => onChange(rows.filter((r) => r._key !== p.data._key))}
          >
            削除
          </button>
        ),
      },
    ],
    [quantityField, quantityLabel, rows, onChange],
  );

  const handleChange = (e: CellValueChangedEvent<T>) => {
    onChange(rows.map((r) => (r._key === e.data._key ? { ...e.data } : r)));
  };

  return (
    <AgGridReact<T>
      theme={themeQuartz}
      rowData={rows}
      columnDefs={columnDefs}
      getRowId={(p) => p.data._key}
      onCellValueChanged={handleChange}
      stopEditingWhenCellsLoseFocus
    />
  );
}
