import type React from 'react';
import type { MenuKey } from '../store/ui';
import { useUiStore } from '../store/ui';

const menus: Array<[MenuKey, string]> = [
  ['overview', 'Overview'], ['portfolio', 'Portfolio'], ['orders', 'Orders'], ['trades', 'Trades'],
  ['factors', 'Factors'], ['backtest', 'Backtest'], ['walkforward', 'Walk Forward'], ['risk', 'Risk'],
  ['rebalance', 'Rebalance Center'], ['logs', 'System Logs'], ['admin', 'Admin']
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { menu, setMenu } = useUiStore();
  return <div className="min-h-screen">
    <aside className="fixed inset-y-0 left-0 w-64 border-r border-slate-800 bg-slate-950 p-4">
      <h1 className="mb-6 text-xl font-bold">Korea Quant</h1>
      <nav className="space-y-1">
        {menus.map(([key, label]) => <button key={key} onClick={() => setMenu(key)} className={`w-full rounded-xl px-3 py-2 text-left text-sm ${menu === key ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>{label}</button>)}
      </nav>
    </aside>
    <main className="ml-64 p-6">{children}</main>
  </div>;
}
