# Deprecated Templates

These templates have been replaced by the React SPA frontend and are no longer actively used.

## Deprecation Date
2026-01-14

## React SPA Replacements

| Deprecated Template | React Route | Component |
|---------------------|-------------|-----------|
| `dashboard/index.html` | `/` | `Dashboard.tsx` |
| `dashboard/health.html` | `/health` | Pending |
| `dashboard/parity.html` | `/parity` | Pending |
| `data_workbench/*.html` | `/workbench` | `DataWorkbench.tsx` |
| `logic_studio/*.html` | `/logic-studio` | `LogicStudio.tsx` |
| `reports/portfolio.html` | `/portfolio` | `Portfolio.tsx` |
| `reports/cashflow.html` | `/cashflow` | `CashFlow.tsx` |
| `reports/compass.html` | `/compass` | `Compass.tsx` |
| `reports/simulation.html` | `/simulation` | `Simulation.tsx` |
| `reports/annual.html` | Pending | - |
| `reports/attribution.html` | Pending | - |
| `reports/thermometer.html` | Pending | - |
| `wealth/dashboard.html` | `/wealth` | `Wealth.tsx` |
| `wealth/parity.html` | `/wealth` | Part of `Wealth.tsx` |
| `index.html` | `/` | `Dashboard.tsx` |
| `verify.html` | - | Removed |
| `test_components.html` | - | Removed (dev tool) |

## Still Active Templates

The following templates are still in use:

- `base.html` - Base layout for remaining Flask pages
- `errors/404.html`, `errors/500.html` - Error pages
- `auth/login.html` - Fallback login page
- `integrations/*` - Integration management (not yet migrated)
- `onboarding/*` - First-run experience
- `assets/list.html` - Asset list (not yet migrated)
- `transactions/*` - Transaction CRUD (not yet migrated)
- `macros/components.html` - Shared Jinja2 macros

## Cleanup Instructions

These templates can be permanently deleted once:
1. All React routes are verified working in production
2. Fallback Flask routes are removed
3. Integration and transaction pages are migrated to React
