/**
 * Wealth Dashboard API Response Types
 *
 * TypeScript interfaces for wealth-related API endpoints.
 */

// Chart data structure (shared pattern)
export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string;
  borderColor?: string;
}

export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

// Summary KPIs (YTD with YoY comparison)
export interface WealthSummaryKPIs {
  ytd_income: string;
  ytd_income_yoy: string;
  ytd_expense: string;
  ytd_expense_yoy: string;
  ytd_investment: string;
  ytd_investment_yoy: string;
  ytd_net_cf: string;
  ytd_net_cf_yoy: string;
}

// Balance Sheet section
export interface BalanceSheetData {
  trend_chart: ChartData;
  asset_allocation: {
    labels: string[];
    data: number[];
  };
  ratios_chart: ChartData;
  kpis: {
    total_assets: string;
    total_liabilities: string;
    liability_to_asset: string;
  };
}

// Cash Flow section
export interface CashFlowData {
  income_chart: ChartData;
  expense_chart: ChartData;
  combined_chart: ChartData;
  income_source_chart: ChartData;
  expense_cat_chart: ChartData;
  investment_cat_chart: ChartData;
  expense_stacked_chart: ChartData;
  expense_breakdown: {
    labels: string[];
    data: number[];
  };
  ytd_expense_breakdown: Record<string, { value: number; yoy: string }>;
  net_cash_flow_chart: ChartData;
  income_sources: {
    labels: string[];
    values: number[];
  };
  income_sources_yoy: Record<string, { value: number; yoy: string }>;
  comparisons: {
    mom: PeriodComparison;
    qoq: PeriodComparison;
    ytd: PeriodComparison;
    l12m: PeriodComparison;
  };
  kpis: {
    monthly_avg_income: string;
    monthly_avg_expense: string;
    savings_rate: string;
  };
}

export interface PeriodComparison {
  income_pct: number;
  expense_pct: number;
  investment_pct: number;
  net_pct?: number;
}

// Investment section
export interface InvestmentData {
  portfolio_value: number;
  ytd_return: number;
  allocation_chart: ChartData;
}

// Historical performance
export interface HistoricalData {
  performance_chart: ChartData;
  metrics: {
    xirr: number | null;
    twrr: number | null;
    max_drawdown: number | null;
  };
}

// Full dashboard response from /wealth/api/summary
export interface WealthDashboardResponse {
  summary: WealthSummaryKPIs;
  balance_sheet: BalanceSheetData;
  cash_flow: CashFlowData;
  investment?: InvestmentData;
  forecast?: Record<string, unknown>;
  historical?: HistoricalData;
  error?: string;
}

// Parity check response from /wealth/api/parity
export interface WealthParityResponse {
  excel: {
    date: string;
    total_income: number;
    total_expense: number;
    net_savings: number;
  };
  database: {
    date: string;
    total_income: number;
    total_expense: number;
    net_savings: number;
  };
  deltas: {
    total_income_delta_pct: number;
    total_expense_delta_pct: number;
    net_savings_delta_pct: number;
  };
}
