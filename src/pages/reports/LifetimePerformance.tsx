/**
 * Lifetime Performance Report
 * The "Scorecard" - Total realized profits, tax efficiency, and individual asset track records
 * 
 * Two Views:
 * 1. Gains Analysis - KPIs and charts for realized vs unrealized gains
 * 2. Asset Performance - Table view with individual asset track records
 */

import React, { useState, useMemo } from 'react';
import { Download, Filter, Search, TrendingUp, BarChart3, Table, RefreshCw, X } from 'lucide-react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from 'recharts';
import { useLifetimePerformance } from '../../hooks/useReports';
import type { AssetPerformance } from '../../api/types/reports';

type ViewType = 'gains' | 'table';

interface FilterState {
    status: 'all' | 'ACTIVE' | 'CLOSED';
    assetClass: string;
}

const LifetimePerformance: React.FC = () => {
    // API data hook
    const { data, isLoading, error, refetch, isFetching } = useLifetimePerformance();

    // UI state
    const [view, setView] = useState<ViewType>('gains');
    const [searchQuery, setSearchQuery] = useState('');
    const [showFilter, setShowFilter] = useState(false);
    const [filters, setFilters] = useState<FilterState>({ status: 'all', assetClass: 'all' });
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    // Extract data from API response
    const totalRealized = data?.gains_summary?.total_realized || 0;
    const totalUnrealized = data?.gains_summary?.total_unrealized || 0;
    const totalGains = totalRealized + totalUnrealized;
    const weightedXirr = data?.gains_summary?.weighted_xirr || 0;
    const gainsBreakdown = data?.gains_breakdown || [];
    const subclassData = data?.subclass_breakdown || [];
    const assetData = data?.asset_performance || [];
    const activeAssets = data?.active_assets || 0;
    const totalAssets = data?.total_assets || 0;

    // Get unique asset classes for filter dropdown
    const assetClasses = useMemo(() => {
        const classes = new Set(assetData.map((a: AssetPerformance) => a.asset_class));
        return ['all', ...Array.from(classes)];
    }, [assetData]);

    // Filter assets based on search and filters
    const filteredAssets = useMemo(() => {
        return assetData.filter((asset: AssetPerformance) => {
            const matchesSearch = asset.name.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesStatus = filters.status === 'all' || asset.status === filters.status;
            const matchesClass = filters.assetClass === 'all' || asset.asset_class === filters.assetClass;
            return matchesSearch && matchesStatus && matchesClass;
        });
    }, [assetData, searchQuery, filters]);

    // Pagination
    const totalPages = Math.ceil(filteredAssets.length / itemsPerPage);
    const paginatedAssets = useMemo(() => {
        const start = (currentPage - 1) * itemsPerPage;
        return filteredAssets.slice(start, start + itemsPerPage);
    }, [filteredAssets, currentPage, itemsPerPage]);

    // Reset to page 1 when filters change
    React.useEffect(() => {
        setCurrentPage(1);
    }, [searchQuery, filters]);

    // Export handler
    const handleExport = () => {
        const headers = ['Asset Name', 'Asset Class', 'Sub Class', 'Holding Period', 'Status', 'Total Invested', 'Current Value', 'Realized Gain', 'Unrealized Gain', 'Total Gain', 'Return %'];
        const csvContent = [
            headers.join(','),
            ...filteredAssets.map((a: AssetPerformance) => [
                `"${a.name}"`,
                a.asset_class,
                a.sub_class,
                a.holding_period,
                a.status,
                a.total_invested,
                a.current_value,
                a.realized_gain,
                a.unrealized_gain,
                a.total_gain,
                a.return_pct
            ].join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `lifetime_performance_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    };

    // Loading state
    if (isLoading) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
                    <p className="text-sm font-medium text-gray-500">Loading performance data...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (error || !data) {
        return (
            <div className="flex h-[60vh] items-center justify-center">
                <div className="text-center">
                    <div className="mx-auto mb-4 rounded-full bg-red-100 p-4 w-16 h-16 flex items-center justify-center">
                        <X className="h-8 w-8 text-red-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Unable to Load Data</h3>
                    <p className="text-sm text-gray-500 mb-4">{error?.message || 'Failed to fetch performance data'}</p>
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
        <div className="p-6 lg:p-8">
            {/* Header with Tab Navigation */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">
                            {view === 'gains' ? 'Realized vs. Unrealized Gains Analysis' : 'Lifetime Asset Performance'}
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        {/* View Toggle */}
                        <div className="flex rounded-lg border border-gray-200 bg-white p-1">
                            <button
                                onClick={() => setView('gains')}
                                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${view === 'gains' ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:text-gray-900'
                                    }`}
                            >
                                <BarChart3 size={16} />
                                Gains Analysis
                            </button>
                            <button
                                onClick={() => setView('table')}
                                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${view === 'table' ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:text-gray-900'
                                    }`}
                            >
                                <Table size={16} />
                                Performance Table
                            </button>
                        </div>
                    </div>
                </div>
                <div className="h-1 w-full bg-gradient-to-r from-blue-500 to-blue-300 rounded-full"></div>
            </div>

            {view === 'gains' ? (
                /* VIEW 1: Gains Analysis */
                <>
                    {/* Row 1: KPI Cards */}
                    <div className="mb-6 grid gap-6 lg:grid-cols-3">
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm text-center">
                            <p className="text-3xl font-bold text-emerald-600">¥{totalRealized.toLocaleString()}</p>
                            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mt-2">Total Realized Gains</p>
                        </div>
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm text-center">
                            <p className="text-3xl font-bold text-blue-600">¥{totalUnrealized.toLocaleString()}</p>
                            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mt-2">Total Unrealized Gains</p>
                        </div>
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm text-center">
                            <p className="text-3xl font-bold text-gray-900">¥{totalGains.toLocaleString()}</p>
                            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mt-2">Total Gains</p>
                        </div>
                    </div>

                    {/* Row 2: Charts */}
                    <div className="grid gap-6 lg:grid-cols-2">
                        {/* Gains Breakdown */}
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                            <h3 className="font-semibold text-gray-900 mb-4">Gains Breakdown</h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={gainsBreakdown} layout="horizontal">
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                    <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} />
                                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(v) => `¥${(v / 1000).toFixed(0)}k`} axisLine={false} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                                        formatter={(value: number) => [`¥${value.toLocaleString()}`, '']}
                                    />
                                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                        {gainsBreakdown.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Sub-Class Level Breakdown */}
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-gray-900">Sub-Class Level Realized vs Unrealized</h3>
                                <div className="flex gap-4 text-sm">
                                    <span className="flex items-center gap-2">
                                        <span className="h-3 w-3 rounded-sm bg-[#22c55e]"></span>
                                        Realized Gains
                                    </span>
                                    <span className="flex items-center gap-2">
                                        <span className="h-3 w-3 rounded-sm bg-blue-500"></span>
                                        Unrealized Gains
                                    </span>
                                </div>
                            </div>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={subclassData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                    <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} angle={-45} textAnchor="end" height={80} />
                                    <YAxis tick={{ fill: '#64748b', fontSize: 12 }} tickFormatter={(v) => `¥${(v / 1000).toFixed(0)}k`} axisLine={false} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                                        formatter={(value: number) => [`¥${value.toLocaleString()}`, '']}
                                    />
                                    <Bar dataKey="realized" name="Realized" stackId="a" fill="#22c55e" />
                                    <Bar dataKey="unrealized" name="Unrealized" stackId="a" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </>
            ) : (
                /* VIEW 2: Asset Performance Table */
                <>
                    {/* Header Controls */}
                    <div className="mb-4 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setView('gains')}
                                className="px-3 py-1.5 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
                            >
                                Hide Table
                            </button>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="relative">
                                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="Search assets..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                                />
                            </div>
                            <button
                                onClick={() => refetch()}
                                disabled={isFetching}
                                className="p-2 text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                            >
                                <RefreshCw size={16} className={isFetching ? 'animate-spin' : ''} />
                            </button>
                            <button
                                onClick={() => setShowFilter(!showFilter)}
                                className={`flex items-center gap-2 px-3 py-2 text-sm font-medium border rounded-lg transition-colors ${showFilter ? 'bg-blue-50 text-blue-600 border-blue-200' : 'text-gray-600 border-gray-200 hover:bg-gray-50'
                                    }`}
                            >
                                <Filter size={16} />
                                Filter
                            </button>
                            <button
                                onClick={handleExport}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                            >
                                <Download size={16} />
                                Export CSV
                            </button>
                        </div>
                    </div>

                    {/* Data Table */}
                    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="min-w-full">
                                <thead>
                                    <tr className="border-b border-gray-100 bg-gray-50">
                                        <th className="py-3 px-4 text-left text-xs font-semibold uppercase text-gray-500">Asset Name</th>
                                        <th className="py-3 px-4 text-left text-xs font-semibold uppercase text-gray-500">Asset Class</th>
                                        <th className="py-3 px-4 text-left text-xs font-semibold uppercase text-gray-500">Holding Period</th>
                                        <th className="py-3 px-4 text-center text-xs font-semibold uppercase text-gray-500">Status</th>
                                        <th className="py-3 px-4 text-right text-xs font-semibold uppercase text-gray-500">Total Invested</th>
                                        <th className="py-3 px-4 text-right text-xs font-semibold uppercase text-gray-500">Current Value</th>
                                        <th className="py-3 px-4 text-right text-xs font-semibold uppercase text-gray-500">Profit/Loss</th>
                                        <th className="py-3 px-4 text-right text-xs font-semibold uppercase text-gray-500">Return %</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100 text-xs">
                                    {paginatedAssets.map((asset: AssetPerformance, i: number) => (
                                        <tr key={i} className="hover:bg-gray-50 transition-colors">
                                            <td className="py-3 px-4 font-medium text-gray-900">{asset.name}</td>
                                            <td className="py-3 px-4 text-gray-600">{asset.asset_class}</td>
                                            <td className="py-3 px-4 text-gray-600">{asset.holding_period}</td>
                                            <td className="py-3 px-4 text-center">
                                                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${asset.status === 'ACTIVE'
                                                    ? 'bg-emerald-100 text-emerald-700'
                                                    : 'bg-gray-100 text-gray-600'
                                                    }`}>
                                                    {asset.status}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-right font-mono text-gray-700">¥{asset.total_invested.toLocaleString()}</td>
                                            <td className="py-3 px-4 text-right font-mono text-gray-700">
                                                {asset.current_value > 0 ? `¥${asset.current_value.toLocaleString()}` : '—'}
                                            </td>
                                            <td className={`py-3 px-4 text-right font-mono font-semibold ${asset.total_gain >= 0 ? 'text-emerald-600' : 'text-red-600'
                                                }`}>
                                                ¥{asset.total_gain.toLocaleString()}
                                            </td>
                                            <td className={`py-3 px-4 text-right font-semibold ${asset.return_pct >= 0 ? 'text-emerald-600' : 'text-red-600'
                                                }`}>
                                                {asset.return_pct >= 0 ? '+' : ''}{asset.return_pct.toFixed(2)}%
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
                            <p className="text-sm text-gray-500">
                                Showing {Math.min((currentPage - 1) * itemsPerPage + 1, filteredAssets.length)} to {Math.min(currentPage * itemsPerPage, filteredAssets.length)} of {filteredAssets.length} assets
                            </p>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                    className="px-3 py-1 text-sm text-gray-400 hover:text-gray-600 disabled:opacity-50"
                                >&lt;</button>
                                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(page => (
                                    <button
                                        key={page}
                                        onClick={() => setCurrentPage(page)}
                                        className={`px-3 py-1 text-sm rounded ${page === currentPage
                                                ? 'font-medium text-white bg-blue-600'
                                                : 'text-gray-600 hover:bg-gray-100'
                                            }`}
                                    >
                                        {page}
                                    </button>
                                ))}
                                <button
                                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                    className="px-3 py-1 text-sm text-gray-400 hover:text-gray-600 disabled:opacity-50"
                                >&gt;</button>
                            </div>
                        </div>
                    </div>

                    {/* Footer Summary Cards */}
                    <div className="mt-6 grid gap-6 lg:grid-cols-3">
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Total Lifetime Gain</p>
                            <p className="text-3xl font-bold text-emerald-600">+¥{totalGains.toLocaleString()}</p>
                            <p className="text-xs text-gray-500 mt-1">Combined realized & unrealized</p>
                        </div>
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Weighted XIRR</p>
                            <p className="text-3xl font-bold text-blue-600">{weightedXirr.toFixed(2)}%</p>
                            <p className="text-xs text-gray-500 mt-1">Overall portfolio performance</p>
                        </div>
                        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Active Assets</p>
                            <p className="text-3xl font-bold text-gray-900">{activeAssets} / {totalAssets}</p>
                            <p className="text-xs text-gray-500 mt-1">Current holding distribution</p>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default LifetimePerformance;
