import type React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ApiRecord, formatCurrency, formatPercent, getJson, postJson } from '../api/client';
import { DataTable } from '../components/DataTable';

export function Orders() {
  const { data } = useQuery({ queryKey: ['orders'], queryFn: () => getJson<{ orders: ApiRecord[] }>('/dashboard/orders?period=7d'), refetchInterval: 3000 });
  return <Page title="Orders"><DataTable rows={data?.orders ?? []} columns={[{key:'order_time',label:'주문시간'},{key:'symbol',label:'종목'},{key:'side',label:'매수/매도'},{key:'order_quantity',label:'주문수량'},{key:'filled_quantity',label:'체결수량'},{key:'filled_price',label:'체결가격', render: formatCurrency},{key:'status',label:'상태'}]} /></Page>;
}

export function Trades() {
  const { data } = useQuery({ queryKey: ['trades'], queryFn: () => getJson<{ trades: ApiRecord[]; statistics: ApiRecord }>('/dashboard/trades') });
  return <Page title="Trades"><div className="grid grid-cols-4 gap-3">{Object.entries(data?.statistics ?? {}).map(([k,v]) => <div className="card" key={k}><p className="text-slate-400">{k}</p><p className="text-xl font-bold">{k.includes('rate') || k.includes('factor') ? formatPercent(v) : formatCurrency(v)}</p></div>)}</div><DataTable rows={data?.trades ?? []} columns={[{key:'entry_date',label:'진입일'},{key:'exit_date',label:'청산일'},{key:'holding_days',label:'보유기간'},{key:'return_rate',label:'수익률', render: formatPercent},{key:'profit',label:'손익금액', render: formatCurrency}]} /></Page>;
}

export function Factors() {
  const { data } = useQuery({ queryKey: ['factors'], queryFn: () => getJson<{ top20: ApiRecord[] }>('/dashboard/factors') });
  return <Page title="Factors"><DataTable rows={data?.top20 ?? []} columns={[{key:'symbol',label:'종목'},{key:'momentum',label:'Momentum Score'},{key:'value',label:'Value Score'},{key:'quality',label:'Quality Score'},{key:'score',label:'Total Score'}]} /></Page>;
}

export function Backtest() {
  const { data } = useQuery({ queryKey: ['backtest'], queryFn: () => getJson<{ metrics: ApiRecord; equity_curve: ApiRecord[]; drawdown: ApiRecord[]; annual_returns: ApiRecord; monthly_returns: ApiRecord }>('/dashboard/backtest?start=2020-01-01&end=2024-12-31'), retry: false });
  return <Page title="Backtest"><div className="grid grid-cols-5 gap-3">{['CAGR','MDD','Sharpe Ratio','Sortino Ratio','Calmar Ratio'].map((key) => <div className="card" key={key}><p className="text-slate-400">{key}</p><p className="text-xl font-bold">{formatPercent(data?.metrics?.[key])}</p></div>)}</div><div className="grid grid-cols-2 gap-4"><Chart title="Equity Curve" data={data?.equity_curve ?? []} dataKey="value"/><Chart title="Drawdown" data={data?.drawdown ?? []} dataKey="value"/></div><DataTable rows={Object.entries(data?.annual_returns ?? {}).map(([year, value]) => ({year, value}))} columns={[{key:'year',label:'연도'},{key:'value',label:'수익률', render: formatPercent}]} /></Page>;
}

export function WalkForward() {
  const { data } = useQuery({ queryKey: ['walkforward'], queryFn: () => getJson<{ windows: ApiRecord[]; average: ApiRecord }>('/dashboard/walkforward?start_year=2014&end_year=2024'), retry: false });
  return <Page title="Walk Forward Analysis"><div className="grid grid-cols-3 gap-3">{Object.entries(data?.average ?? {}).map(([k,v]) => <div className="card" key={k}><p className="text-slate-400">평균 {k}</p><p className="text-xl font-bold">{formatPercent(v)}</p></div>)}</div><DataTable rows={data?.windows ?? []} columns={[{key:'train_start',label:'Train Start'},{key:'train_end',label:'Train End'},{key:'test_start',label:'Test Start'},{key:'test_end',label:'Test End'},{key:'CAGR',label:'CAGR', render: formatPercent},{key:'MDD',label:'MDD', render: formatPercent},{key:'Sharpe Ratio',label:'Sharpe'}]} /></Page>;
}

export function Risk() {
  const { data } = useQuery({ queryKey: ['risk'], queryFn: () => getJson<ApiRecord>('/dashboard/risk'), refetchInterval: 5000 });
  return <Page title="Risk Dashboard"><div className="grid grid-cols-5 gap-3">{['current_mdd','concentration','cash_weight','sector_concentration','volatility'].map((key) => <div className="card" key={key}><p className="text-slate-400">{key}</p><p className="text-xl font-bold">{formatPercent(data?.[key])}</p></div>)}</div><div className="card"><h3 className="mb-2 font-semibold">경고</h3>{((data?.warnings as string[]) ?? []).map((warning) => <p className="text-red-300" key={warning}>{warning}</p>)}</div></Page>;
}

export function Rebalance() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ['rebalance'], queryFn: () => getJson<{ orders: ApiRecord[]; current_portfolio: ApiRecord[]; expected_portfolio: ApiRecord[] }>('/dashboard/rebalance') });
  const run = useMutation({ mutationFn: () => postJson('/dashboard/rebalance?execute=true'), onSuccess: () => qc.invalidateQueries({ queryKey: ['rebalance'] }) });
  return <Page title="Rebalance Center"><button className="btn" onClick={() => run.mutate()}>리밸런싱 실행</button><DataTable rows={data?.orders ?? []} columns={[{key:'symbol',label:'종목'},{key:'side',label:'매수/매도'},{key:'quantity',label:'수량'},{key:'target_weight',label:'목표비중', render: formatPercent},{key:'estimated_price',label:'예상가격', render: formatCurrency}]} /></Page>;
}

export function Logs() {
  const { data } = useQuery({ queryKey: ['logs'], queryFn: () => getJson<{ lines: string[] }>('/dashboard/logs?log_name=system.log') });
  return <Page title="System Logs"><pre className="card max-h-[640px] overflow-auto text-xs">{(data?.lines ?? []).join('\n')}</pre></Page>;
}

export function Admin() {
  const qc = useQueryClient();
  const control = useMutation({ mutationFn: (action: string) => postJson(`/dashboard/strategy/${action}`), onSuccess: () => qc.invalidateQueries() });
  return <Page title="Admin"><div className="flex gap-3"><button className="btn" onClick={() => control.mutate('resume')}>전략 재개</button><button className="btn" onClick={() => control.mutate('stop')}>전략 중지</button><button className="btn" onClick={() => control.mutate('paper')}>Paper Trading</button><button className="btn" onClick={() => control.mutate('live')}>실거래 전환</button><button className="btn-danger" onClick={() => control.mutate('emergency_stop')}>Emergency Stop</button></div></Page>;
}

function Page({ title, children }: { title: string; children: React.ReactNode }) { return <section className="space-y-4"><h2 className="text-2xl font-bold">{title}</h2>{children}</section>; }
function Chart({ title, data, dataKey }: { title: string; data: ApiRecord[]; dataKey: string }) { return <div className="card h-80"><h3 className="mb-2 font-semibold">{title}</h3><ResponsiveContainer><LineChart data={data}><XAxis dataKey="date"/><YAxis/><Tooltip/><Line dataKey={dataKey} stroke="#60a5fa" dot={false}/></LineChart></ResponsiveContainer></div>; }
