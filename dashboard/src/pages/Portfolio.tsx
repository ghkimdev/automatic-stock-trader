import { useQuery } from '@tanstack/react-query';
import { Area, AreaChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ApiRecord, formatCurrency, formatPercent, getJson } from '../api/client';
import { DataTable } from '../components/DataTable';

export function Portfolio() {
  const { data } = useQuery({ queryKey: ['portfolio'], queryFn: () => getJson<{ positions: ApiRecord[]; value_curve: ApiRecord[]; sector_weights: ApiRecord[] }>('/dashboard/portfolio') });
  return <section className="space-y-4"><h2 className="text-2xl font-bold">Portfolio</h2>
    <DataTable rows={data?.positions ?? []} columns={[
      { key: 'symbol', label: '종목코드' }, { key: 'name', label: '종목명' }, { key: 'quantity', label: '수량' },
      { key: 'avg_price', label: '평균단가', render: formatCurrency }, { key: 'current_price', label: '현재가', render: formatCurrency },
      { key: 'return_rate', label: '수익률', render: formatPercent }, { key: 'valuation_pnl', label: '평가손익', render: formatCurrency }, { key: 'weight', label: '비중', render: formatPercent }
    ]} />
    <div className="grid grid-cols-2 gap-4">
      <div className="card h-80"><h3 className="mb-2 font-semibold">포트폴리오 가치 추이</h3><ResponsiveContainer><AreaChart data={data?.value_curve ?? []}><XAxis dataKey="date"/><YAxis/><Tooltip/><Area dataKey="value" stroke="#60a5fa" fill="#1d4ed8"/></AreaChart></ResponsiveContainer></div>
      <div className="card h-80"><h3 className="mb-2 font-semibold">섹터 비중</h3><ResponsiveContainer><PieChart><Pie data={data?.sector_weights ?? []} dataKey="value" nameKey="sector" label>{(data?.sector_weights ?? []).map((_, i) => <Cell key={i} fill={['#3b82f6','#22c55e','#f97316','#e879f9','#f43f5e'][i % 5]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer></div>
    </div>
  </section>;
}
