import { useEffect, useRef, useState, type ReactNode } from "react";
import MapView, { type AddMode } from "./components/MapView";
import NodeTable from "./components/NodeTable";
import ResultTable from "./components/ResultTable";
import { fetchSample, fetchSolvers, newKey, solve } from "./api";
import { downloadCsv, parseCsv } from "./csv";
import type { Customer, Params, SolveResult, Supplier } from "./types";

type Tab = "customers" | "suppliers" | "result";

// 既存の ID と重ならない次の ID（C21, S07 など）を作る
function nextId(prefix: string, ids: string[]) {
  let n = ids.length + 1;
  const used = new Set(ids);
  while (used.has(`${prefix}${String(n).padStart(2, "0")}`)) n++;
  return `${prefix}${String(n).padStart(2, "0")}`;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </section>
  );
}

const inputCls = "w-full rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-indigo-500 focus:outline-none";
const btnCls = "rounded-md border border-slate-300 bg-white px-2 py-1 text-sm hover:bg-slate-50 disabled:opacity-50";

export default function App() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [solvers, setSolvers] = useState<string[]>([]);
  const [params, setParams] = useState<Params>({
    cost_per_unit_distance: 1.2,
    unit: "km",
    solver: "highs",
    allow_shortage: false,
    penalty: 10000,
  });
  const [result, setResult] = useState<SolveResult | null>(null);
  const [stale, setStale] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("customers");
  const [addMode, setAddMode] = useState<AddMode>("none");
  const [fitVersion, setFitVersion] = useState(0);
  const customerFile = useRef<HTMLInputElement>(null);
  const supplierFile = useRef<HTMLInputElement>(null);

  const loadSample = async () => {
    try {
      const data = await fetchSample();
      setCustomers(data.customers);
      setSuppliers(data.suppliers);
      setResult(null);
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
  const updateSuppliers = (rows: Supplier[]) => { setSuppliers(rows); setStale(true); };
  const updateParams = (p: Partial<Params>) => { setParams((old) => ({ ...old, ...p })); setStale(true); };

  const totalDemand = customers.reduce((a, c) => a + c.demand, 0);
  const totalSupply = suppliers.reduce((a, s) => a + s.supply, 0);

  const runSolve = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await solve(customers, suppliers, params);
      setResult(r);
      setStale(false);
      if (r.status === "solved") setTab("result");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const importCsv = async (file: File, kind: "customers" | "suppliers") => {
    try {
      if (kind === "customers") {
        updateCustomers(await parseCsv<Customer>(file, ["lat", "lon", "demand"], ["ID", "lat", "lon", "demand"]));
      } else {
        updateSuppliers(await parseCsv<Supplier>(file, ["lat", "lon", "supply"], ["ID", "lat", "lon", "supply"]));
      }
      setFitVersion((v) => v + 1);
      setTab(kind);
    } catch (e) {
      setError(`CSV の読み込みに失敗しました: ${e}`);
    }
  };

  // 地図クリックでノードを追加
  const addNode = (lat: number, lon: number) => {
    const ids = [...customers.map((c) => c.ID), ...suppliers.map((s) => s.ID)];
    if (addMode === "customer") {
      const ID = nextId("C", ids);
      updateCustomers([...customers, { _key: newKey(), ID, name: "", lat, lon, demand: 1000 }]);
      setTab("customers");
    } else if (addMode === "supplier") {
      const ID = nextId("S", ids);
      updateSuppliers([...suppliers, { _key: newKey(), ID, name: "", lat, lon, supply: 10000 }]);
      setTab("suppliers");
    }
  };

  const solved = result?.status === "solved";
  const flows = solved ? result.flows ?? [] : [];
  const shortages = solved ? result.shortages ?? {} : {};
  const shortageTotal = Object.values(shortages).reduce((a, b) => a + b, 0);

  return (
    <div className="flex h-full flex-col bg-slate-100 text-slate-800">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <h1 className="text-lg font-semibold">輸送問題ソルバー <span className="text-sm font-normal text-slate-500">Transportation Problem</span></h1>
        <span className="text-xs text-slate-500">AMPL + FastAPI + React</span>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* 左パネル：パラメータと結果 */}
        <aside className="w-72 shrink-0 space-y-5 overflow-y-auto border-r border-slate-200 bg-white p-4">
          <Section title="データ">
            <div className="grid grid-cols-2 gap-2">
              <button className={btnCls} onClick={() => customerFile.current?.click()}>顧客 CSV</button>
              <button className={btnCls} onClick={() => supplierFile.current?.click()}>サプライヤー CSV</button>
              <button className={`${btnCls} col-span-2`} onClick={loadSample}>サンプルに戻す</button>
            </div>
            <input ref={customerFile} type="file" accept=".csv" hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) importCsv(f, "customers"); e.target.value = ""; }} />
            <input ref={supplierFile} type="file" accept=".csv" hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) importCsv(f, "suppliers"); e.target.value = ""; }} />
            <p className="text-xs text-slate-500">列: ID, name, lat, lon, demand（顧客）/ supply（サプライヤー）</p>
            <dl className="grid grid-cols-2 gap-1 text-sm">
              <dt className="text-slate-500">総供給量</dt><dd className="text-right tabular-nums">{totalSupply.toLocaleString()}</dd>
              <dt className="text-slate-500">総需要量</dt><dd className="text-right tabular-nums">{totalDemand.toLocaleString()}</dd>
            </dl>
            {totalSupply < totalDemand && (
              <p className="rounded bg-amber-50 p-2 text-xs text-amber-800">
                総供給量が総需要量より少ないため、未充足を許さないと実行不能になります。
              </p>
            )}
          </Section>

          <Section title="地図にノードを追加">
            <div className="grid grid-cols-3 gap-1">
              {([["none", "なし"], ["customer", "顧客"], ["supplier", "サプライヤー"]] as const).map(([m, label]) => (
                <button key={m}
                  className={`rounded-md px-2 py-1 text-xs ${addMode === m ? "bg-indigo-600 text-white" : "border border-slate-300 bg-white"}`}
                  onClick={() => setAddMode(m)}>{label}</button>
              ))}
            </div>
            <p className="text-xs text-slate-500">地図をクリックして追加、マーカーをドラッグして移動できます。</p>
          </Section>

          <Section title="パラメータ">
            <label className="block text-sm">
              距離あたり輸送コスト
              <input type="number" min={0} step={0.1} className={inputCls}
                value={params.cost_per_unit_distance}
                onChange={(e) => updateParams({ cost_per_unit_distance: Number(e.target.value) })} />
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
              flows={stale ? [] : flows}
              shortages={stale ? {} : shortages}
              addMode={addMode}
              fitVersion={fitVersion}
              onAdd={addNode}
              onMoveCustomer={(k, lat, lon) => updateCustomers(customers.map((c) => (c._key === k ? { ...c, lat, lon } : c)))}
              onMoveSupplier={(k, lat, lon) => updateSuppliers(suppliers.map((s) => (s._key === k ? { ...s, lat, lon } : s)))}
            />
          </div>
          <div className="flex min-h-0 flex-[2] flex-col border-t border-slate-200 bg-white">
            <div className="flex items-center gap-1 border-b border-slate-200 px-2">
              {([["customers", `顧客 (${customers.length})`], ["suppliers", `サプライヤー (${suppliers.length})`], ["result", `最適フロー (${flows.length})`]] as const).map(([t, label]) => (
                <button key={t}
                  className={`border-b-2 px-3 py-2 text-sm ${tab === t ? "border-indigo-600 font-medium text-indigo-700" : "border-transparent text-slate-500"}`}
                  onClick={() => setTab(t)}>{label}</button>
              ))}
              <div className="ml-auto">
                {tab === "customers" && <button className={btnCls} onClick={() => downloadCsv("customers.csv", customers)}>CSV ダウンロード</button>}
                {tab === "suppliers" && <button className={btnCls} onClick={() => downloadCsv("suppliers.csv", suppliers)}>CSV ダウンロード</button>}
                {tab === "result" && <button className={btnCls} disabled={!flows.length} onClick={() => downloadCsv("flows.csv", flows)}>CSV ダウンロード</button>}
              </div>
            </div>
            <div className="min-h-0 flex-1">
              {tab === "customers" && <NodeTable rows={customers} quantityField="demand" quantityLabel="需要量" onChange={updateCustomers} />}
              {tab === "suppliers" && <NodeTable rows={suppliers} quantityField="supply" quantityLabel="供給可能量" onChange={updateSuppliers} />}
              {tab === "result" && <ResultTable flows={flows} unit={params.unit} />}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
