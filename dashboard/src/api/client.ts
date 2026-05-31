export type ApiRecord = Record<string, unknown>;

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export async function postJson<T>(path: string, body?: ApiRecord): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export const formatCurrency = (value: unknown) => Number(value ?? 0).toLocaleString('ko-KR', { maximumFractionDigits: 0 });
export const formatPercent = (value: unknown) => `${(Number(value ?? 0) * 100).toFixed(2)}%`;
