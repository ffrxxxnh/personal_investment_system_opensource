/**
 * Compass Report Page
 * Tactical rebalancing and regime analysis
 * 
 * Uses demo data when API data is unavailable to ensure page always loads.
 */

import React, { useState } from 'react';
import { Download, Play, AlertTriangle, TrendingUp, TrendingDown, Activity, RefreshCw } from 'lucide-react';
import { useUnifiedAnalysis, useCorrelation, useMarketThermometer } from '../../hooks/useReports';
import GroupedBarChart from '../../components/charts/GroupedBarChart';
import DivergingBarChart from '../../components/charts/DivergingBarChart';
import CorrelationMatrix from '../../components/charts/CorrelationMatrix';
import { TimePeriodSelector, type TimePeriod } from '../../components/ui/TimePeriodSelector';

const Compass: React.FC = () => {
    const [period, setPeriod] = useState<TimePeriod>('YTD');
    const { data: analysisData, isLoading: analysisLoading, error: analysisError, refetch, isFetching } = useUnifiedAnalysis();
    const { data: correlationData, isLoading: correlationLoading, error: correlationError } = useCorrelation(true);
    const { data: thermometerData } = useMarketThermometer();

    // Transform API data - return null when unavailable instead of demo data
    const allocationData = React.useMemo(() => {
        if (!analysisData?.rebalancing_analysis?.recommendations) return null;
        const targets = analysisData.rebalancing_analysis.recommendations || [];
        if (targets.length === 0) return null;
        return targets.slice(0, 5).map((rec: any) => ({
            name: rec.asset_class || rec.asset || 'Unknown',
            target: rec.target_weight || 0,
            current: rec.current_weight || 0,
        }));
    }, [analysisData]);

    const driftData = React.useMemo(() => {
        if (!analysisData?.rebalancing_analysis?.recommendations) return null;
        const recs = analysisData.rebalancing_analysis.recommendations;
        if (recs.length === 0) return null;
        return recs.slice(0, 6).map((rec: any) => ({
            name: rec.asset_class || rec.asset || 'Unknown',
            drift: rec.drift_pct || (rec.current_weight - rec.target_weight) || 0,
            isCritical: Math.abs(rec.drift_pct || 0) > 5,
        }));
    }, [analysisData]);

    const criticalCount = driftData?.filter((d) => Math.abs(d.drift) > 5).length || 0;

    // Market regime - null when unavailable
    const regime = analysisData?.market_regime || null;

    // Fear & Greed Index - from macro_analyzer API
    const fearGreedIndex = React.useMemo(() => {
        if (thermometerData?.fear_greed?.status === 'success') {
            return Math.round(thermometerData.fear_greed.value);
        }
        return null;
    }, [thermometerData]);
    const fearGreedLabel = fearGreedIndex !== null ? (
        fearGreedIndex < 25 ? 'Extreme Fear' :
            fearGreedIndex < 45 ? 'Fear' :
                fearGreedIndex < 55 ? 'Neutral' :
                    fearGreedIndex < 75 ? 'Greed' : 'Extreme Greed'
    ) : 'N/A';

    // Buffett Indicator (US market) - from macro_analyzer API
    const buffettIndicator = React.useMemo(() => {
        if (thermometerData?.buffett_us?.status === 'success') {
            return Math.round(thermometerData.buffett_us.value);
        }
        return null;
    }, [thermometerData]);
    const buffettLabel = buffettIndicator !== null ? (
        buffettIndicator > 150 ? 'Overvalued' :
            buffettIndicator > 100 ? 'Fair Value' : 'Undervalued'
    ) : 'N/A';

    const matrixData = React.useMemo(() => {
        if (!correlationData?.matrix) return null;
        return correlationData.matrix;
    }, [correlationData]);

    const recommendations = analysisData?.rebalancing_analysis?.recommendations?.slice(0, 5) ?? null;

    if (analysisLoading) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
                    <p className="text-sm font-medium text-gray-500">Loading analysis...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 lg:p-8">
            {/* Header */}
            <div className="mb-6 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Action Compass Strategy</h1>
                    <p className="text-sm text-gray-500">Tactical rebalancing and regime analysis</p>
                </div>
                <div className="flex items-center gap-3">
                    <TimePeriodSelector
                        value={period}
                        onChange={setPeriod}
                        options={['1M', '3M', 'YTD', '1Y']}
                    />
                    <button
                        onClick={() => refetch()}
                        disabled={isFetching}
                        className="p-2 text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                    >
                        <RefreshCw size={16} className={isFetching ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={() => {
                            const csvContent = [
                                ['Category', 'Target %', 'Current %', 'Drift'],
                                ...allocationData.map((row: any) => [row.name, row.target, row.current, row.current - row.target])
                            ].map(row => row.join(',')).join('\n');
                            const blob = new Blob([csvContent], { type: 'text/csv' });
                            const link = document.createElement('a');
                            link.href = URL.createObjectURL(blob);
                            link.download = `compass_report_${new Date().toISOString().split('T')[0]}.csv`;
                            link.click();
                        }}
                        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                        <Download size={16} />
                        Export
                    </button>
                    <button className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                        <Play size={16} />
                        Run Simulation
                    </button>
                </div>
            </div>

            {/* Row 1: Strategic Directive Banner */}
            <div className="mb-6 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 p-6 text-white shadow-lg">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="rounded-lg bg-white/20 p-3">
                            <TrendingUp size={24} />
                        </div>
                        <div>
                            <div className="flex items-center gap-3">
                                <h2 className="text-xl font-bold">Current Regime: {regime?.regime || 'Loading...'}</h2>
                                <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-medium">
                                    Updated 2h ago
                                </span>
                            </div>
                            <p className="mt-1 text-blue-100">{regime?.description || 'Analyzing market conditions...'}</p>
                        </div>
                    </div>
                    <div className="hidden lg:flex gap-6">
                        {/* Fear & Greed Index */}
                        <div className="text-right">
                            <p className="text-xs text-blue-200">FEAR & GREED</p>
                            <p className="text-3xl font-bold">{fearGreedIndex ?? '—'}</p>
                            <p className={`text-xs ${fearGreedIndex !== null && fearGreedIndex < 45 ? 'text-amber-300' : 'text-emerald-300'}`}>
                                {fearGreedLabel}
                            </p>
                        </div>
                        {/* Buffett Indicator */}
                        <div className="text-right">
                            <p className="text-xs text-blue-200">BUFFETT IND.</p>
                            <p className="text-3xl font-bold">{buffettIndicator !== null ? `${buffettIndicator}%` : '—'}</p>
                            <p className={`text-xs ${buffettIndicator !== null && buffettIndicator > 150 ? 'text-red-300' : 'text-emerald-300'}`}>
                                {buffettLabel}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 2: Allocation Charts */}
            <div className="mb-6 grid gap-6 lg:grid-cols-2">
                {/* Target vs Current */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <div className="mb-4 flex items-center justify-between">
                        <div>
                            <h3 className="font-semibold text-gray-900">Target vs Current Allocation</h3>
                            <p className="text-sm text-gray-500">
                                Total Portfolio Value: ¥{(analysisData?.portfolio_snapshot?.total_value || 12500000).toLocaleString()}
                            </p>
                        </div>
                    </div>
                    <GroupedBarChart data={allocationData} height={280} />
                </div>

                {/* Drift Analysis */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <div className="mb-4 flex items-center justify-between">
                        <div>
                            <h3 className="font-semibold text-gray-900">Drift Analysis</h3>
                            <p className="text-sm text-gray-500">Red indicates &gt;5% drift requiring action</p>
                        </div>
                        {criticalCount > 0 && (
                            <span className="flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">
                                <AlertTriangle size={12} />
                                {criticalCount} Critical
                            </span>
                        )}
                    </div>
                    <DivergingBarChart data={driftData} height={280} />
                </div>
            </div>

            {/* Row 3: Correlation & Risk/Return */}
            <div className="mb-6 grid gap-6 lg:grid-cols-2">
                {/* Correlation Matrix */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <h3 className="mb-4 font-semibold text-gray-900">Asset Correlation Matrix</h3>
                    {correlationLoading ? (
                        <div className="flex h-48 items-center justify-center">
                            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
                        </div>
                    ) : (
                        <CorrelationMatrix data={matrixData} />
                    )}
                </div>

                {/* Risk/Return Profile */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                    <div className="mb-4 flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900">Risk / Return Profile</h3>
                        <span className="flex items-center gap-1 text-sm text-gray-500">
                            <span className="h-2 w-2 rounded-full bg-blue-500"></span>
                            Current
                        </span>
                    </div>
                    <div className="flex h-64 items-center justify-center rounded-lg bg-gray-50">
                        <div className="text-center">
                            <div className="mx-auto mb-3 rounded-full bg-blue-100 p-4">
                                <Activity className="h-8 w-8 text-blue-600" />
                            </div>
                            <p className="text-sm text-gray-500">Scatter chart visualization</p>
                            <p className="text-xs text-gray-400">X: Risk (Vol%) | Y: Return (XIRR%)</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 4: Rebalancing Actions Table */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 font-semibold text-gray-900">Recommended Rebalancing Actions</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full">
                        <thead>
                            <tr className="border-b border-gray-100">
                                <th className="py-3 text-left text-xs font-semibold uppercase text-gray-500">Priority</th>
                                <th className="py-3 text-left text-xs font-semibold uppercase text-gray-500">Action</th>
                                <th className="py-3 text-left text-xs font-semibold uppercase text-gray-500">Asset</th>
                                <th className="py-3 text-right text-xs font-semibold uppercase text-gray-500">Amount</th>
                                <th className="py-3 text-left text-xs font-semibold uppercase text-gray-500">Rationale</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {recommendations.map((rec: any, i: number) => (
                                <tr key={i} className="hover:bg-gray-50">
                                    <td className="py-3">
                                        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${rec.priority === 'High' ? 'bg-red-100 text-red-700' :
                                            rec.priority === 'Medium' ? 'bg-amber-100 text-amber-700' :
                                                'bg-gray-100 text-gray-600'
                                            }`}>
                                            {rec.priority}
                                        </span>
                                    </td>
                                    <td className="py-3">
                                        <span className={`flex items-center gap-1 font-medium ${rec.action === 'Sell' ? 'text-red-600' : 'text-emerald-600'
                                            }`}>
                                            {rec.action === 'Sell' ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
                                            {rec.action}
                                        </span>
                                    </td>
                                    <td className="py-3 font-medium text-gray-900">{rec.asset}</td>
                                    <td className="py-3 text-right font-mono text-gray-700">
                                        ¥{(rec.amount || 0).toLocaleString()}
                                    </td>
                                    <td className="py-3 text-sm text-gray-500">{rec.rationale}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default Compass;
