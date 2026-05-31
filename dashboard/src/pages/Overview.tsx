import { useQuery } from '@tanstack/react-query';
import { getJson, formatCurrency, formatPercent } from '../api/client';

type OverviewPayload = { account: Record<string, number>; portfolio: Record<string, number>; system: Record<string, unknown> };

export function Overview() {
  const { data } = useQuery({ queryKey: ['overview'], queryFn: () => getJson<OverviewPayload>('/dashboard/overview'), refetchInterval: 5000 });
  const account = data?.account ?? {};
  const portfolio = data?.portfolio ?? {};
  const system = data?.system ?? {};
  return <section className="space-y-4">
    <h2 className="text-2xl font-bold">Overview</h2>
    <div className="grid grid-cols-4 gap-4">
      <Metric label="총 자산" value={formatCurrency(account.total_assets)} />
      <Metric label="예수금" value={formatCurrency(account.cash)} />
      <Metric label="평가손익" value={formatCurrency(account.valuation_pnl)} />
      <Metric label="수익률" value={formatPercent(account.return_rate)} />
    </div>
    <div className="grid grid-cols-3 gap-4">
      <Metric label="보유 종목 수" value={String(portfolio.holding_count ?? 0)} />
      <Metric label="현금 비중" value={formatPercent(portfolio.cash_weight)} />
      <Metric label="투자 비중" value={formatPercent(portfolio.invested_weight)} />
    </div>
    <div className="card grid grid-cols-4 gap-3 text-sm">
      {['db_status', 'api_status', 'broker_status', 'scheduler_status', 'strategy_enabled', 'emergency_stop', 'trading_mode'].map((key) => <div key={key}><p className="text-slate-400">{key}</p><p className="font-semibold">{String(system[key] ?? '-')}</p></div>)}
    </div>
  </section>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="card"><p className="text-sm text-slate-400">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>; }
