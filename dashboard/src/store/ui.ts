import { create } from 'zustand';

export type MenuKey = 'overview' | 'portfolio' | 'orders' | 'trades' | 'factors' | 'backtest' | 'walkforward' | 'risk' | 'rebalance' | 'logs' | 'admin';

type UiState = { menu: MenuKey; setMenu: (menu: MenuKey) => void };

export const useUiStore = create<UiState>((set) => ({ menu: 'overview', setMenu: (menu) => set({ menu }) }));
