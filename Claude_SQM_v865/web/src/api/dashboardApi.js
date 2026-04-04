import { fetchJson } from './client';

export const getDashboardSummary = () => fetchJson('/dashboard/summary');
export const getDashboardByProduct = () => fetchJson('/dashboard/by-product');
export const getLocationSummary = () => fetchJson('/dashboard/location-summary');
