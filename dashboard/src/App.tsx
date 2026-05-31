import { Layout } from './components/Layout';
import { useUiStore } from './store/ui';
import { Overview } from './pages/Overview';
import { Portfolio } from './pages/Portfolio';
import { Admin, Backtest, Factors, Logs, Orders, Rebalance, Risk, Trades, WalkForward } from './pages/Tables';

export function App() {
  const menu = useUiStore((state) => state.menu);
  const pages = { overview: <Overview />, portfolio: <Portfolio />, orders: <Orders />, trades: <Trades />, factors: <Factors />, backtest: <Backtest />, walkforward: <WalkForward />, risk: <Risk />, rebalance: <Rebalance />, logs: <Logs />, admin: <Admin /> };
  return <Layout>{pages[menu]}</Layout>;
}
