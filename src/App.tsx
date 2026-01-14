import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { PreferencesProvider } from './contexts/PreferencesContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';

// Lazy-loaded page components for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const DataWorkbench = lazy(() => import('./pages/DataWorkbench'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Wealth = lazy(() => import('./pages/Wealth'));
const Settings = lazy(() => import('./pages/Settings'));
const Login = lazy(() => import('./pages/Login'));
const LogicStudio = lazy(() => import('./pages/LogicStudio'));

// Lazy-loaded report pages
const Compass = lazy(() => import('./pages/reports/Compass'));
const CashFlow = lazy(() => import('./pages/reports/CashFlow'));
const Simulation = lazy(() => import('./pages/reports/Simulation'));
const LifetimePerformance = lazy(() => import('./pages/reports/LifetimePerformance'));

// Loading spinner component
const PageLoader: React.FC = () => (
    <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Loading...</p>
        </div>
    </div>
);

// Create a client with default options
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 30 * 60 * 1000,   // 30 minutes
            retry: 2,
            refetchOnWindowFocus: false,
        },
    },
});

const App: React.FC = () => {
    return (
        <PreferencesProvider>
            <AuthProvider>
                <QueryClientProvider client={queryClient}>
                    <BrowserRouter>
                        <Suspense fallback={<PageLoader />}>
                            <Routes>
                                {/* Public route - Login */}
                                <Route path="/login" element={<Login />} />

                                {/* Protected routes - require authentication */}
                                <Route element={
                                    <ProtectedRoute>
                                        <Layout />
                                    </ProtectedRoute>
                                }>
                                    <Route path="/" element={<Dashboard />} />
                                    <Route path="/workbench" element={<DataWorkbench />} />
                                    <Route path="/portfolio" element={<Portfolio />} />
                                    <Route path="/wealth" element={<Wealth />} />

                                    {/* Report Pages */}
                                    <Route path="/compass" element={<Compass />} />
                                    <Route path="/cashflow" element={<CashFlow />} />
                                    <Route path="/simulation" element={<Simulation />} />
                                    <Route path="/performance" element={<LifetimePerformance />} />

                                    {/* Logic Studio */}
                                    <Route path="/logic-studio" element={<LogicStudio />} />

                                    {/* Settings */}
                                    <Route path="/settings" element={<Settings />} />

                                    {/* Catch-all */}
                                    <Route path="*" element={<Navigate to="/" replace />} />
                                </Route>
                            </Routes>
                        </Suspense>
                    </BrowserRouter>
                </QueryClientProvider>
            </AuthProvider>
        </PreferencesProvider>
    );
};

export default App;
