import Papa from "papaparse";
import { newKey } from "./api";

// CSV ファイルを読み込み、指定した列を持つ行の配列に変換する
export function parseCsv<T>(file: File, numericCols: string[], requiredCols: string[]): Promise<T[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      transformHeader: (h) => h.replace(/^﻿/, "").trim(),
      complete: (res) => {
        const cols = res.meta.fields ?? [];
        const missing = requiredCols.filter((c) => !cols.includes(c));
        if (missing.length) {
          reject(new Error(`列が足りません: ${missing.join(", ")}`));
          return;
        }
        const rows: T[] = [];
        for (let idx = 0; idx < res.data.length; idx++) {
          const r = res.data[idx];
          const row: Record<string, unknown> = { _key: newKey(), name: "" };
          for (const c of requiredCols) {
            if (numericCols.includes(c)) {
              const val = Number(r[c]);
              if (r[c] === "" || r[c] === undefined || !Number.isFinite(val)) {
                reject(new Error(`${idx + 2}行目の列 "${c}" が数値ではありません: "${r[c] ?? ""}"`));
                return;
              }
              row[c] = val;
            } else {
              row[c] = String(r[c] ?? "").trim();
            }
          }
          if (r.name !== undefined) row.name = String(r.name).trim();
          rows.push(row as T);
        }
        resolve(rows);
      },
      error: reject,
    });
  });
}

// 行の配列を CSV としてダウンロードする
export function downloadCsv(filename: string, rows: object[]) {
  const data = rows.map((r) => Object.fromEntries(Object.entries(r).filter(([k]) => k !== "_key")));
  const blob = new Blob(["﻿" + Papa.unparse(data)], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
