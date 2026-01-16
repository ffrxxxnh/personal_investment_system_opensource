/**
 * Portfolio Report Page
 * Performance & Growth Metrics - The "Health Check"
 */

import React, { useState, useMemo, useEffect } from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
} from 'recharts';
import { TrendingUp, Download, RefreshCw, X } from 'lucide-react';
import { useUnifiedAnalysis } from '../hooks/useReports';
import { usePortfolioOverview } from '../hooks/usePortfolio';
import { TimePeriodSelector, type TimePeriod } from '../components/ui/TimePeriodSelector';

const Portfolio: React.FC = () => {
    const [period, setPeriod] = useState<TimePeriod>('YTD');
    const { data: analysisData, isLoading: analysisLoading, error: analysisError, refetch, isFetching } = useUnifiedAnalysis();
    const { data: portfolioData, isLoading: portfolioLoading, error: portfolioError } = usePortfolioOverview();

    const isLoading = analysisLoading || portfolioLoading;
    const error = analysisError || portfolioError;

    // Transform API trend data for chart
    const growthData = useMemo(() => {
        if (!portfolioData?.trend?.dates || !portfolioData?.trend?.values) {
            return null;
        }
        return portfolioData.trend.dates.map((date: string, i: number) => ({
            month: new Date(date).toLocaleString('default', { month: 'short' }),
            portfolio: portfolioData.trend.values[i],
            date: date,
        }));
    }, [portfolioData]);

    // Extract asset allocation for YoY-like breakdown
    const allocationData = useMemo(() => {
        if (!portfolioData?.allocation) return null;
        return Object.entries(portfolioData.allocation).map(([name, value]) => ({
            name,
            value: value as number,
        }));
    }, [portfolioData]);

    // Performance by asset class from analysis data
    const performanceData = useMemo(() => {
        if (!analysisData?.rebalancing_analysis?.categories) return null;
        return analysisData.rebalancing_analysis.categories.slice(0, 5).map((cat: any) => ({
            name: cat.name,
            xirr: cat.actual_pct || 0,
            color: '#3b82f6',
        }));
    }, [analysisData]);

    // Extract portfolio snapshot data
    const netWorth = analysisData?.portfolio_snapshot?.total_value || portfolioData?.total_portfolio_value || 0;
    const ytdGrowth = analysisData?.performance_data?.ytd_return || 0;
    const ytdAmount = Math.round(netWorth * (ytdGrowth / 100));
    const holdingsCount = portfolioData?.current_holdings_count || 0;

    const handleExport = () => {
        if (!growthData) return;
        // Create CSV export of portfolio data
        const csvContent = [
            ['Month', 'Date', 'Portfolio Value'],
            ...growthData.map(row => [row.month, row.date, row.portfolio])
        ].map(row => row.join(',')).join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `portfolio_report_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    };

    if (isLoading) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
                    <p className="text-sm font-medium text-gray-500">Loading portfolio...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="mx-auto mb-4 rounded-full bg-red-100 p-4 w-16 h-16 flex items-center justify-center">
                        <X className="h-8 w-8 text-red-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Unable to Load Portfolio</h3>
                    <p className="text-sm text-gray-500 mb-4">{error?.message || 'Failed to fetch portfolio data'}</p>
                    <button
                        onClick={() => refetch()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 lg:p-8 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-3xl font-bold text-gray-900">Performance & Growth Metrics</h1>
                <div className="flex items-center gap-3">
                    <TimePeriodSelector
                        value={period}
                        onChange={setPeriod}
                        options={['1M', '3M', '6M', 'YTD', '1Y', 'ALL']}
                    />
                    <button
                        onClick={() => refetch()}
                        disabled={isFetching}
                        className="p-2 text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                    >
                        <RefreshCw size={16} className={isFetching ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={handleExport}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                    >
                        <Download size={16} />
                        Export
                    </button>
                </div>
            </div>

            {/* Row 1: Hero - Portfolio Growth Trend */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Portfolio Growth</h3>
                        <div className="flex items-baseline gap-3">
                            <span className="text-4xl font-bold text-gray-900">
                                ¥{netWorth.toLocaleString()}
                            </span>
                            {ytdGrowth !== 0 && (
                                <span className={`flex items-center font-semibold text-sm ${ytdGrowth >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                                    <TrendingUp size={16} className="mr-1" />
                                    {ytdGrowth >= 0 ? '+' : ''}¥{ytdAmount.toLocaleString()} ({ytdGrowth.toFixed(1)}%) YTD
                                </span>
                            )}
                        </div>
                        <p className="text-sm text-gray-500 mt-1">{holdingsCount} holdings</p>
                    </div>
                </div>

                {growthData ? (
                    <ResponsiveContainer width="100%" height={280}>
                        <AreaChart data={growthData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                            <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
                            <YAxis
                                tick={{ fill: '#64748b', fontSize: 12 }}
                                tickFormatter={(v) => `¥${(v / 1000000).toFixed(1)}M`}
                                axisLine={false}
                                tickLine={false}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                                formatter={(value: number) => [`¥${value.toLocaleString()}`, 'Portfolio']}
                            />
                            <Area type="monotone" dataKey="portfolio" stroke="#3b82f6" fill="url(#portfolioGrad)" />
                        </AreaChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="flex h-[280px] items-center justify-center bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-500">No trend data available</p>
                    </div>
                )}
            </div>

            {/* Row 2: Performance by Class + Asset Allocation */}
            <div className="grid gap-6 lg:grid-cols-2">
                {/* Performance by Class */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Asset Allocation</h3>
                    </div>
                    {allocationData && allocationData.length > 0 ? (
                        <div className="space-y-4">
                            {allocationData.map((item) => (
                                <div key={item.name}>
                                    <div className="flex justify-between text-sm mb-1.5">
                                        <span className="font-medium text-gray-700">{item.name}</span>
                                        <span className="font-bold text-gray-900">¥{item.value.toLocaleString()}</span>
                                    </div>
                                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full rounded-full transition-all duration-700 bg-blue-500"
                                            style={{
                                                width: `${Math.min((item.value / netWorth) * 100, 100)}%`,
                                            }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="flex h-[200px] items-center justify-center bg-gray-50 rounded-lg">
                            <p className="text-sm text-gray-500">No allocation data available</p>
                        </div>
                    )}
                </div>

                {/* Performance by Class */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Performance by Class</h3>
                        <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">Last 12 Months</span>
                    </div>
                    {performanceData && performanceData.length > 0 ? (
                        <div className="space-y-4">
                            {performanceData.map((item) => (
                                <div key={item.name}>
                                    <div className="flex justify-between text-sm mb-1.5">
                                        <span className="font-medium text-gray-700">{item.name}</span>
                                        <span className="font-bold text-gray-900">{item.xirr?.toFixed(1) || 0}%</span>
                                    </div>
                                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full rounded-full transition-all duration-700"
                                            style={{
                                                width: `${Math.min(item.xirr * 6, 100)}%`,
                                                backgroundColor: item.color
                                            }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="flex h-[200px] items-center justify-center bg-gray-50 rounded-lg">
                            <p className="text-sm text-gray-500">No performance data available</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Row 3: Top Performers */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Top Performers (This Period)</h3>
                    <button className="text-sm font-medium text-blue-600 hover:text-blue-700">View Full Report</button>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full">
                        <thead>
                            <tr className="border-b border-gray-100">
                                <th className="py-3 text-left text-xs font-semibold uppercase text-gray-400">Asset</th>
                                <th className="py-3 text-left text-xs font-semibold uppercase text-gray-400">Class</th>
                                <th className="py-3 text-right text-xs font-semibold uppercase text-gray-400">Value</th>
                                <th className="py-3 text-right text-xs font-semibold uppercase text-gray-400">Return</th>
                                <th className="py-3 text-right text-xs font-semibold uppercase text-gray-400">Allocation</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {[
                                { name: 'NVDA', class: 'US Equity', value: 285000, return: 142.5, alloc: 13.3 },
                                { name: 'AAPL', class: 'US Equity', value: 195000, return: 48.2, alloc: 9.1 },
                                { name: 'MSFT', class: 'US Equity', value: 178000, return: 56.8, alloc: 8.3 },
                                { name: 'VTI', class: 'US ETF', value: 320000, return: 24.1, alloc: 14.9 },
                                { name: 'BND', class: 'Bond ETF', value: 210000, return: 4.2, alloc: 9.8 },
                            ].map((asset, i) => (
                                <tr key={i} className="hover:bg-gray-50">
                                    <td className="py-3 font-semibold text-gray-900">{asset.name}</td>
                                    <td className="py-3 text-sm text-gray-500">{asset.class}</td>
                                    <td className="py-3 text-right font-mono text-gray-700">${asset.value.toLocaleString()}</td>
                                    <td className="py-3 text-right">
                                        <span className={`font-semibold ${asset.return > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                            {asset.return > 0 ? '+' : ''}{asset.return}%
                                        </span>
                                    </td>
                                    <td className="py-3 text-right text-gray-600">{asset.alloc}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default Portfolio;
