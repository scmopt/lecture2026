import { useEffect, useRef, useState } from "react";
import { fetchSample, fetchSolvers, newKey, solve } from "./api";
import MapView, { type AddMode } from "./components/MapView";
import NodeTable from "./components/NodeTable";
import ResultTable from "./components/ResultTable";
import { downloadCsv, parseCsv } from "./csv";
import type { Customer, Params, SolveResult, Supplier, Warehouse } from "./types";

type Tab = "customers" | "warehouses" | "suppliers" | "result";

// 既存の ID と重ならない連番を作る
function nextId(prefix: string, existing: string[]): string {
  for (let i = 1; ; i++) {
    const id = `${prefix}${i}`;
    if (!existing.includes(id)) return id;
  }
}

export default function App() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [solvers, setSolvers] = useState<string[]>([]);
  const [params, setParams] = useState<Params>({
    cost_per_unit_distance_sw: 15,
    cost_per_unit_distance_wc: 20,
    unit: "km",
    solver: "highs",
    enforce_capacity: true,
    allow_shortage: false,
    penalty: 100000,
  });
  const [addMode, setAddMode] = useState<AddMode>("none");
  const [tab, setTab] = useState<Tab>("customers");
  const [result, setResult] = useState<SolveResult | null>(null);
  const [stale, setStale] = useState(false); // 解いた後にデータ・設定を変えたら true
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fitVersion, setFitVersion] = useState(0);

  const customerFile = useRef<HTMLInputElement>(null);
  const warehouseFile = useRef<HTMLInputElement>(null);
  const supplierFile = useRef<HTMLInputElement>(null);

  const loadSample = async () => {
    setError("");
    try {
      const s = await fetchSample();
      setCustomers(s.customers);
      setWarehouses(s.warehouses);
      setSuppliers(s.suppliers);
      setResult(null);
      setStale(false);
      setFitVersion((v) => v + 1);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    fetchSolvers()
      .then((list) => {
        setSolvers(list);
        if (list.length && !list.includes("highs")) setParams((p) => ({ ...p, solver: list[0] }));
      })
      .catch((e) => setError(`バックエンドに接続できません: ${e}`));
    loadSample();
  }, []);

  // データやパラメータを変えたら、表示中の解は古いことを示す
  const updateCustomers = (rows: Customer[]) => { setCustomers(rows); setStale(true); };
  const updateWarehouses = (rows: Warehouse[]) => { setWarehouses(rows); setStale(true); };
  const updateSuppliers = (rows: Supplier[]) => { setSuppliers(rows); setStale(true); };
  const updateParams = (p: Partial<Params>) => { setParams((old) => ({ ...old, ...p })); setStale(true); };

  const totalDemand = customers.reduce((a, c) => a + c.demand, 0);
  const totalCapacity = warehouses.reduce((a, w) => a + w.capacity, 0);
  const totalSupply = suppliers.reduce((a, s) => a + s.supply, 0);

  const runSolve = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await solve(customers, suppliers, warehouses, params);
      setResult(r);
      setStale(false);
      if (r.status === "solved") setTab("result");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const importCsv = async (file: File, kind: "customers" | "warehouses" | "suppliers") => {
    try {
      if (kind === "customers") {
        updateCustomers(await parseCsv<Customer>(file, ["lat", "lon", "demand"], ["ID", "lat", "lon", "demand"]));
      } else if (kind === "warehouses") {
        updateWarehouses(await parseCsv<Warehouse>(file, ["lat", "lon", "capacity"], ["ID", "lat", "lon", "capacity"]));
      } else {
        updateSuppliers(await parseCsv<Supplier>(file, ["lat", "lon", "supply"], ["ID", "lat", "lon", "supply"]));
      }
      setFitVersion((v) => v + 1);
      setTab(kind);
    } catch (e) {
      setError(`CSV の読み込みに失敗しました: ${e}`);
    }
  };

  // 地図クリックまたは表ボタンでノードを追加
  const addNodeAt = (kind: "customer" | "warehouse" | "supplier", lat: number, lon: number) => {
    const ids = [
      ...customers.map((c) => c.ID),
      ...warehouses.map((w) => w.ID),
      ...suppliers.map((s) => s.ID),
    ];
    if (kind === "customer") {
      const ID = nextId("c", ids);
      updateCustomers([...customers, { _key: newKey(), ID, name: "", lat, lon, demand: 500 }]);
      setTab("customers");
    } else if (kind === "warehouse") {
      const ID = nextId("w", ids);
      updateWarehouses([...warehouses, { _key: newKey(), ID, name: "", lat, lon, capacity: 2000 }]);
      setTab("warehouses");
    } else {
      const ID = nextId("s", ids);
      updateSuppliers([...suppliers, { _key: newKey(), ID, name: "", lat, lon, supply: 2000 }]);
      setTab("suppliers");
    }
  };

  const addNode = (lat: number, lon: number) => {
    if (addMode !== "none") addNodeAt(addMode, lat, lon);
  };

  const addRowInTable = (kind: "customer" | "warehouse" | "supplier") => {
    const all = [...customers, ...warehouses, ...suppliers];
    const lat = all.length ? all.reduce((a, n) => a + n.lat, 0) / all.length : 50;
    const lon = all.length ? all.reduce((a, n) => a + n.lon, 0) / all.length : 10;
    addNodeAt(kind, Number(lat.toFixed(4)), Number(lon.toFixed(4)));
  };

  const solved = result?.status === "solved";
  const flows = solved ? result.flows ?? [] : [];
  const costSW = flows.filter((f) => f.stage === "S→W").reduce((a, f) => a + f.cost, 0);
  const costWC = flows.filter((f) => f.stage === "W→C").reduce((a, f) => a + f.cost, 0);
  const shortages = solved ? result.shortages ?? {} : {};
  const warehouseThroughputs = solved ? result.warehouse_throughputs ?? {} : {};
  const shortageTotal = Object.values(shortages).reduce((a, b) => a + b, 0);

  return (
    <div className="flex h-full flex-col bg-slate-100 text-slate-800">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <h1 className="text-lg font-semibold">
          積換問題ソルバー <span className="text-sm font-normal text-slate-500">Transshipment Problem</span>
        </h1>
        <span className="text-xs text-slate-500">AMPL + FastAPI + React</span>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* 左パネル：パラメータと結果 */}
        <aside className="w-72 shrink-0 space-y-5 overflow-y-auto border-r border-slate-200 bg-white p-4">
          <Section title="データ">
            <div className="grid grid-cols-3 gap-1.5">
              <button className={btnCls} onClick={() => customerFile.current?.click()}>顧客 CSV</button>
              <button className={btnCls} onClick={() => warehouseFile.current?.click()}>倉庫 CSV</button>
              <button className={btnCls} onClick={() => supplierFile.current?.click()}>供給 CSV</button>
              <button className={`${btnCls} col-span-3`} onClick={loadSample}>サンプルに戻す</button>
            </div>
            <input ref={customerFile} type="file" accept=".csv" hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) importCsv(f, "customers"); e.target.value = ""; }} />
            <input ref={warehouseFile} type="file" accept=".csv" hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) importCsv(f, "warehouses"); e.target.value = ""; }} />
            <input ref={supplierFile} type="file" accept=".csv" hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) importCsv(f, "suppliers"); e.target.value = ""; }} />
            <p className="text-xs text-slate-500">列: ID, name, lat, lon, demand / capacity / supply</p>
            <dl className="grid grid-cols-2 gap-1 text-sm">
              <dt className="text-slate-500">総供給量</dt><dd className="text-right tabular-nums">{totalSupply.toLocaleString()}</dd>
              <dt className="text-slate-500">総倉庫容量</dt><dd className="text-right tabular-nums">{totalCapacity.toLocaleString()}</dd>
              <dt className="text-slate-500">総需要量</dt><dd className="text-right tabular-nums">{totalDemand.toLocaleString()}</dd>
            </dl>
            {(totalSupply < totalDemand || (params.enforce_capacity && totalCapacity < totalDemand)) && (
              <p className="rounded bg-amber-50 p-2 text-xs text-amber-800">
                供給量または倉庫容量の合計が総需要量より少ないため、未充足を許さないと実行不能になります。
              </p>
            )}
          </Section>

          <Section title="地図にノードを追加">
            <div className="grid grid-cols-2 gap-1">
              {([["none", "なし"], ["customer", "顧客 (C)"], ["warehouse", "倉庫 (W)"], ["supplier", "サプライヤー (S)"]] as const).map(([m, label]) => (
                <button key={m}
                  className={`rounded-md px-2 py-1 text-xs ${addMode === m ? "bg-indigo-600 text-white" : "border border-slate-300 bg-white"}`}
                  onClick={() => setAddMode(m)}>{label}</button>
              ))}
            </div>
            <p className="text-xs text-slate-500">地図をクリックして追加、マーカーをドラッグして移動できます。</p>
          </Section>

          <Section title="パラメータ">
            <label className="block text-sm">
              距離あたりコスト（S → W）
              <input type="number" min={0} step={0.5} className={inputCls}
                value={params.cost_per_unit_distance_sw}
                onChange={(e) => updateParams({ cost_per_unit_distance_sw: Number(e.target.value) })} />
            </label>
            <label className="block text-sm">
              距離あたりコスト（W → C）
              <input type="number" min={0} step={0.5} className={inputCls}
                value={params.cost_per_unit_distance_wc}
                onChange={(e) => updateParams({ cost_per_unit_distance_wc: Number(e.target.value) })} />
            </label>
            <label className="block text-sm">
              距離の単位
              <select className={inputCls} value={params.unit}
                onChange={(e) => updateParams({ unit: e.target.value as Params["unit"] })}>
                <option value="km">km</option>
                <option value="mi">mi</option>
              </select>
            </label>
            <label className="block text-sm">
              ソルバー
              <select className={inputCls} value={params.solver}
                onChange={(e) => updateParams({ solver: e.target.value })}>
                {solvers.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={params.enforce_capacity}
                onChange={(e) => updateParams({ enforce_capacity: e.target.checked })} />
              倉庫の容量制約を有効にする
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={params.allow_shortage}
                onChange={(e) => updateParams({ allow_shortage: e.target.checked })} />
              需要の未充足を許す
            </label>
            {params.allow_shortage && (
              <label className="block text-sm">
                未充足ペナルティ（1単位あたり）
                <input type="number" min={0} className={inputCls} value={params.penalty}
                  onChange={(e) => updateParams({ penalty: Number(e.target.value) })} />
              </label>
            )}
          </Section>

          <button
            className="w-full rounded-md bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            disabled={busy || !solvers.length}
            onClick={runSolve}
          >
            {busy ? "計算中…" : "最適化を実行"}
          </button>

          {error && <p className="rounded bg-red-50 p-2 text-xs break-all text-red-700">{error}</p>}

          {result && (
            <Section title="結果">
              {stale && <p className="rounded bg-amber-50 p-2 text-xs text-amber-800">データが変更されています。再実行してください。</p>}
              <p className={`text-sm font-medium ${solved ? "text-green-700" : "text-red-700"}`}>状態: {result.status}</p>
              {solved && (
                <dl className="grid grid-cols-2 gap-1 text-sm">
                  <dt className="text-slate-500">目的関数値</dt><dd className="text-right tabular-nums">{result.objective!.toLocaleString(undefined, { maximumFractionDigits: 0 })}</dd>
                  <dt className="text-slate-500">輸送コスト</dt><dd className="text-right tabular-nums">{result.transport_cost!.toLocaleString(undefined, { maximumFractionDigits: 0 })}</dd>
                  <dt className="text-slate-500">　S → W</dt><dd className="text-right tabular-nums text-orange-600">{costSW.toLocaleString(undefined, { maximumFractionDigits: 0 })}</dd>
                  <dt className="text-slate-500">　W → C</dt><dd className="text-right tabular-nums text-blue-600">{costWC.toLocaleString(undefined, { maximumFractionDigits: 0 })}</dd>
                  <dt className="text-slate-500">使用アーク数</dt><dd className="text-right tabular-nums">{flows.length}</dd>
                  {shortageTotal > 0 && <><dt className="text-red-600">未充足量</dt><dd className="text-right tabular-nums text-red-600">{shortageTotal.toLocaleString()}</dd></>}
                </dl>
              )}
              <details className="text-xs">
                <summary className="cursor-pointer text-slate-500">ソルバーの出力</summary>
                <pre className="mt-1 overflow-x-auto rounded bg-slate-900 p-2 whitespace-pre-wrap text-slate-100">{result.solver_output}</pre>
              </details>
            </Section>
          )}
        </aside>

        {/* 右側：地図と表 */}
        <main className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-[3]">
            <MapView
              customers={customers}
              suppliers={suppliers}
              warehouses={warehouses}
              flows={stale ? [] : flows}
              shortages={stale ? {} : shortages}
              warehouseThroughputs={stale ? {} : warehouseThroughputs}
              addMode={addMode}
              fitVersion={fitVersion}
              onAdd={addNode}
              onMoveCustomer={(k, lat, lon) => updateCustomers(customers.map((c) => (c._key === k ? { ...c, lat, lon } : c)))}
              onMoveWarehouse={(k, lat, lon) => updateWarehouses(warehouses.map((w) => (w._key === k ? { ...w, lat, lon } : w)))}
              onMoveSupplier={(k, lat, lon) => updateSuppliers(suppliers.map((s) => (s._key === k ? { ...s, lat, lon } : s)))}
            />
          </div>
          <div className="flex min-h-0 flex-[2] flex-col border-t border-slate-200 bg-white">
            <div className="flex items-center gap-1 border-b border-slate-200 px-2">
              {([
                ["customers", `顧客 (${customers.length})`],
                ["warehouses", `倉庫 (${warehouses.length})`],
                ["suppliers", `サプライヤー (${suppliers.length})`],
                ["result", `最適フロー (${flows.length})`],
              ] as const).map(([t, label]) => (
                <button key={t}
                  className={`border-b-2 px-3 py-2 text-sm ${tab === t ? "border-indigo-600 font-medium text-indigo-700" : "border-transparent text-slate-500"}`}
                  onClick={() => setTab(t)}>{label}</button>
              ))}
              <div className="ml-auto flex items-center gap-1.5">
                <button className={btnCls} onClick={() => setFitVersion((v) => v + 1)}>全体を表示</button>
                {tab === "customers" && <button className={btnCls} onClick={() => addRowInTable("customer")}>+ 行を追加</button>}
                {tab === "warehouses" && <button className={btnCls} onClick={() => addRowInTable("warehouse")}>+ 行を追加</button>}
                {tab === "suppliers" && <button className={btnCls} onClick={() => addRowInTable("supplier")}>+ 行を追加</button>}
                {tab === "customers" && <button className={btnCls} onClick={() => downloadCsv("customers.csv", customers)}>CSV ダウンロード</button>}
                {tab === "warehouses" && <button className={btnCls} onClick={() => downloadCsv("warehouses.csv", warehouses)}>CSV ダウンロード</button>}
                {tab === "suppliers" && <button className={btnCls} onClick={() => downloadCsv("suppliers.csv", suppliers)}>CSV ダウンロード</button>}
                {tab === "result" && <button className={btnCls} disabled={!flows.length} onClick={() => downloadCsv("flows.csv", flows)}>CSV ダウンロード</button>}
              </div>
            </div>
            <div className="min-h-0 flex-1">
              {tab === "customers" && <NodeTable rows={customers} quantityField="demand" quantityLabel="需要量" onChange={updateCustomers} />}
              {tab === "warehouses" && <NodeTable rows={warehouses} quantityField="capacity" quantityLabel="容量" onChange={updateWarehouses} />}
              {tab === "suppliers" && <NodeTable rows={suppliers} quantityField="supply" quantityLabel="供給可能量" onChange={updateSuppliers} />}
              {tab === "result" && <ResultTable flows={flows} unit={params.unit} />}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

const inputCls = "mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm";
const btnCls = "rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs hover:bg-slate-50 disabled:opacity-50";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xs font-semibold tracking-wider text-slate-500 uppercase">{title}</h2>
      {children}
    </section>
  );
}
