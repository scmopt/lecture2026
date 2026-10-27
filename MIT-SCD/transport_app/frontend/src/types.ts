// 顧客（Customer）
export interface Customer {
  _key: string; // 画面内部で行を識別するキー
  ID: string;
  name: string;
  lat: number;
  lon: number;
  demand: number;
}

// サプライヤー（Supplier）
export interface Supplier {
  _key: string;
  ID: string;
  name: string;
  lat: number;
  lon: number;
  supply: number;
}

export type Unit = "km" | "mi";

// 求解パラメータ
export interface Params {
  cost_per_unit_distance: number;
  unit: Unit;
  solver: string;
  allow_shortage: boolean;
  penalty: number;
}

export interface Flow {
  supplier: string;
  customer: string;
  flow: number;
  distance: number;
  unit_cost: number;
  cost: number;
}

export interface SolveResult {
  status: string;
  solver_output: string;
  objective?: number;
  transport_cost?: number;
  flows?: Flow[];
  shortages?: Record<string, number>;
}
