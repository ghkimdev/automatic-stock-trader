import type React from 'react';
import type { ApiRecord } from '../api/client';

type Column = { key: string; label: string; render?: (value: unknown, row: ApiRecord) => React.ReactNode };

export function DataTable({ columns, rows }: { columns: Column[]; rows: ApiRecord[] }) {
  return <div className="overflow-x-auto rounded-2xl border border-slate-800">
    <table className="min-w-full bg-slate-900/70">
      <thead><tr>{columns.map((column) => <th className="table-th" key={column.key}>{column.label}</th>)}</tr></thead>
      <tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td className="table-td" key={column.key}>{column.render ? column.render(row[column.key], row) : String(row[column.key] ?? '')}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}
