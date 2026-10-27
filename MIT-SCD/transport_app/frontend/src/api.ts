import type { Customer, Params, SolveResult, Supplier } from "./types";

let counter = 0;
export const newKey = () => `k${Date.now()}_${counter++}`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ? JSON.stringify(body.detail) : res.statusText);
  }
  return res.json();
}

// 利用可能なソルバー一覧
export const fetchSolvers = () => request<string[]>("/api/solvers");

// サンプルデータ
export async function fetchSample() {
  const data = await request<{ customers: Omit<Customer, "_key">[]; suppliers: Omit<Supplier, "_key">[] }>(
    "/api/sample",
  );
  return {
    customers: data.customers.map((c) => ({ ...c, _key: newKey() })),
    suppliers: data.suppliers.map((s) => ({ ...s, _key: newKey() })),
  };
}

// 輸送問題を解く
export function solve(customers: Customer[], suppliers: Supplier[], params: Params) {
  const strip = <T extends { _key: string }>({ _key, ...rest }: T) => rest;
  return request<SolveResult>("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customers: customers.map(strip), suppliers: suppliers.map(strip), ...params }),
  });
}
