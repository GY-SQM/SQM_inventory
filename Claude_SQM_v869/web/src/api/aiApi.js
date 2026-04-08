import { fetchJson } from './client';

export function getInsights() {
  return fetchJson('/ai/insights');
}

export function getStatusPieData() {
  return fetchJson('/ai/chart/status-pie');
}

export function getInboundTrend() {
  return fetchJson('/ai/chart/inbound-trend');
}
