/**
 * Wealth Dashboard Data Hooks
 *
 * React Query hooks for fetching wealth dashboard data from the Flask backend.
 */

import { useQuery } from '@tanstack/react-query';
import api from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import type { WealthDashboardResponse, WealthParityResponse } from '../api/types';

// Query keys for cache management
export const WEALTH_QUERY_KEYS = {
  dashboard: ['wealth', 'dashboard'] as const,
  parity: ['wealth', 'parity'] as const,
};

/**
 * Fetch comprehensive wealth dashboard data
 *
 * Returns YTD summary, balance sheet, cash flow analysis, and historical data.
 */
export function useWealthDashboard() {
  return useQuery({
    queryKey: WEALTH_QUERY_KEYS.dashboard,
    queryFn: async () => {
      const result = await api.get<WealthDashboardResponse>(ENDPOINTS.WEALTH_SUMMARY);

      if (!result.success) {
        throw new Error(result.error.message);
      }

      return result.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000,   // 30 minutes
    retry: 2,
    refetchOnWindowFocus: false,
  });
}

/**
 * Fetch data parity check
 *
 * Compares Excel source data with database values for validation.
 * Only fetched when explicitly enabled.
 */
export function useWealthParity(enabled: boolean = false) {
  return useQuery({
    queryKey: WEALTH_QUERY_KEYS.parity,
    queryFn: async () => {
      const result = await api.get<WealthParityResponse>(ENDPOINTS.WEALTH_PARITY);

      if (!result.success) {
        throw new Error(result.error.message);
      }

      return result.data;
    },
    enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - doesn't change often
    retry: 1,
  });
}
