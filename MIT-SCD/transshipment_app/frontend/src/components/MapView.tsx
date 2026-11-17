import { useEffect, useMemo } from "react";
import L from "leaflet";
import { MapContainer, Marker, Polyline, Popup, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import type { Customer, Flow, Supplier, Warehouse } from "../types";

export type AddMode = "none" | "customer" | "warehouse" | "supplier";

const CUSTOMER_COLOR = "#16a34a";
const WAREHOUSE_COLOR = "#2563eb";
const SUPPLIER_COLOR = "#ea580c";

// 顧客・倉庫・サプライヤーのマーカーアイコン（folium の BeautifyIcon に相当）
function nodeIcon(label: string, color: string) {
  return L.divIcon({
    className: "",
    html: `<div class="node-icon" style="width:26px;height:26px;border-color:${color};color:${color}">${label}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

// 地図クリックでノードを追加する
function ClickHandler({ addMode, onAdd }: { addMode: AddMode; onAdd: (lat: number, lon: number) => void }) {
  const map = useMapEvents({
    click(e) {
      if (addMode !== "none") onAdd(e.latlng.lat, e.latlng.lng);
    },
  });
  useEffect(() => {
    map.getContainer().style.cursor = addMode === "none" ? "" : "crosshair";
  }, [map, addMode]);
  return null;
}

// データを差し替えたときに全ノードが入るように表示範囲を合わせる
function FitBounds({ points, version }: { points: [number, number][]; version: number }) {
  const map = useMap();
  useEffect(() => {
    if (points.length) map.fitBounds(points, { padding: [30, 30] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version]);
  return null;
}

interface Props {
  customers: Customer[];
  suppliers: Supplier[];
  warehouses: Warehouse[];
  flows: Flow[];
  shortages: Record<string, number>;
  warehouseThroughputs: Record<string, number>;
  addMode: AddMode;
  fitVersion: number;
  maxWidth?: number;
  onAdd: (lat: number, lon: number) => void;
  onMoveCustomer: (key: string, lat: number, lon: number) => void;
  onMoveWarehouse: (key: string, lat: number, lon: number) => void;
  onMoveSupplier: (key: string, lat: number, lon: number) => void;
}

export default function MapView({
  customers,
  suppliers,
  warehouses,
  flows,
  shortages,
  warehouseThroughputs,
  addMode,
  fitVersion,
  maxWidth = 20,
  onAdd,
  onMoveCustomer,
  onMoveWarehouse,
  onMoveSupplier,
}: Props) {
  const byId = useMemo(() => {
    const m = new Map<string, [number, number]>();
    customers.forEach((c) => m.set(c.ID, [c.lat, c.lon]));
    warehouses.forEach((w) => m.set(w.ID, [w.lat, w.lon]));
    suppliers.forEach((s) => m.set(s.ID, [s.lat, s.lon]));
    return m;
  }, [customers, warehouses, suppliers]);

  // 線の太さを正規化するためにフローの最大値を求める
  const maxFlow = Math.max(1, ...flows.map((f) => f.flow));
  const points = [...byId.values()];

  return (
    <MapContainer center={[50, 10]} zoom={5} className="h-full w-full">
      <TileLayer
        url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        attribution="Esri"
      />
      <ClickHandler addMode={addMode} onAdd={onAdd} />
      <FitBounds points={points} version={fitVersion} />

      {/* 2段階のフロー（S→W: オレンジ系、W→C: ブルー系） */}
      {flows.map((f) => {
        const a = byId.get(f.from_id);
        const b = byId.get(f.to_id);
        if (!a || !b) return null;
        const lineColor = f.stage === "S→W" ? "#f97316" : "#3b82f6";
        return (
          <Polyline
            key={`${f.stage}-${f.from_id}-${f.to_id}`}
            positions={[a, b]}
            pathOptions={{ color: lineColor, opacity: 0.65, weight: Math.max(1.5, (f.flow / maxFlow) * maxWidth) }}
          >
            <Tooltip sticky>
              [{f.stage}] {f.from_id} → {f.to_id}: {f.flow.toLocaleString()}
            </Tooltip>
          </Polyline>
        );
      })}

      {customers.map((c) => (
        <Marker
          key={c._key}
          position={[c.lat, c.lon]}
          icon={nodeIcon("C", shortages[c.ID] ? "#dc2626" : CUSTOMER_COLOR)}
          draggable
          eventHandlers={{
            dragend: (e) => {
              const p = (e.target as L.Marker).getLatLng();
              onMoveCustomer(c._key, p.lat, p.lng);
            },
          }}
        >
          <Popup>
            <b>{c.ID}</b> {c.name}
            <br />
            需要量: {c.demand.toLocaleString()}
            {shortages[c.ID] ? (
              <>
                <br />
                <span className="text-red-600">未充足: {shortages[c.ID].toLocaleString()}</span>
              </>
            ) : null}
          </Popup>
        </Marker>
      ))}

      {warehouses.map((w) => {
        const throughput = warehouseThroughputs[w.ID];
        const utilPct =
          throughput !== undefined && w.capacity > 0
            ? Math.round((throughput / w.capacity) * 100)
            : null;
        return (
          <Marker
            key={w._key}
            position={[w.lat, w.lon]}
            icon={nodeIcon("W", WAREHOUSE_COLOR)}
            draggable
            eventHandlers={{
              dragend: (e) => {
                const p = (e.target as L.Marker).getLatLng();
                onMoveWarehouse(w._key, p.lat, p.lng);
              },
            }}
          >
            <Popup>
              <b>{w.ID}</b> {w.name}
              <br />
              容量: {w.capacity.toLocaleString()}
              {throughput !== undefined ? (
                <>
                  <br />
                  通過量: {throughput.toLocaleString()}
                  {utilPct !== null ? ` (${utilPct}%)` : ""}
                </>
              ) : null}
            </Popup>
          </Marker>
        );
      })}

      {suppliers.map((s) => (
        <Marker
          key={s._key}
          position={[s.lat, s.lon]}
          icon={nodeIcon("S", SUPPLIER_COLOR)}
          draggable
          eventHandlers={{
            dragend: (e) => {
              const p = (e.target as L.Marker).getLatLng();
              onMoveSupplier(s._key, p.lat, p.lng);
            },
          }}
        >
          <Popup>
            <b>{s.ID}</b> {s.name}
            <br />
            供給可能量: {s.supply.toLocaleString()}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
