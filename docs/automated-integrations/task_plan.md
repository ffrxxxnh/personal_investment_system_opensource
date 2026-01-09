# Feature: Automated Data Integrations (API Sync / CCXT / IBKR / Schwab)

## Overview

**Goal**: Replace manual Excel/CSV import workflow with automated API integrations, enabling real-time portfolio synchronization from multiple data sources.

**Pain Point Addressed**: Manual CSV download and Excel formatting is the #1 cause of user churn for open-source users. This feature eliminates that friction by providing:

- Direct broker API connections (IBKR, Schwab)
- Cryptocurrency exchange sync (via CCXT)
- Enhanced market data (Tiingo, Yahoo Finance)
- Extensible plugin system for community-contributed bank integrations

**Success Criteria**:

- User connects broker account → Portfolio syncs automatically
- Crypto holdings update daily without manual intervention
- Community can contribute new bank integrations via plugins
- CSV import remains as fallback for unsupported sources

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Unified Data Import Pipeline                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    CCXT      │  │    IBKR      │  │   Schwab     │  │   Plugins    │    │
│  │  Connector   │  │  Connector   │  │  Connector   │  │   Manager    │    │
│  │              │  │              │  │              │  │              │    │
│  │ - Binance    │  │ - REST API   │  │ - OAuth2     │  │ - ICBC       │    │
│  │ - Coinbase   │  │ - JWT Auth   │  │ - CSV Fall-  │  │ - Chase      │    │
│  │ - Kraken     │  │ - Multi-Acct │  │   back       │  │ - Custom     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │             │
│         └─────────────────┴─────────────────┴─────────────────┘             │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Base Connector Interface                          │    │
│  │  - authenticate() → bool                                             │    │
│  │  - get_holdings() → DataFrame                                        │    │
│  │  - get_transactions(since_date) → DataFrame                          │    │
│  │  - health_check() → (bool, str)                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Data Normalization Layer                        │    │
│  │  - clean_holdings() → Standardized DataFrame                         │    │
│  │  - clean_transactions() → Standardized DataFrame                     │    │
│  │  - generate_asset_id() → String                                      │    │
│  │  - map_transaction_types() → Standard Types                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Database Layer                               │    │
│  │  - Transaction table                                                  │    │
│  │  - Holding table                                                      │    │
│  │  - Asset table                                                        │    │
│  │  - ImportHistory table (NEW)                                          │    │
│  │  - PluginConfig table (NEW)                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                          Market Data Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │   Tiingo     │  │Yahoo Finance │  │ Alpha Vantage│                       │
│  │  (Primary)   │  │  (Fallback)  │  │  (Fallback)  │                       │
│  └──────────────┘  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Infrastructure & Base Classes

**Priority**: Critical | **Complexity**: Medium

- [x] **1.1** Create base connector interface ✅
  - File: `src/data_manager/connectors/base_connector.py`
  - Abstract methods: `authenticate()`, `get_holdings()`, `get_transactions()`
  - Standard return types: `pd.DataFrame` with defined columns
  - Error handling patterns: `ConnectorError`, `AuthenticationError`, `RateLimitError`

- [x] **1.2** Create plugin framework structure ✅
  - Directory: `src/plugins/`
  - Files: `base.py`, `manager.py`, `registry.py`
  - Plugin discovery mechanism (scan for `manifest.yaml`)
  - Plugin validation (required methods, safe imports)

- [x] **1.3** Database schema enhancements ✅
  - New table: `ImportJob` (track sync operations)
    - `id`, `source_type`, `source_id`, `started_at`, `completed_at`, `status`, `records_imported`, `error_message`
  - New table: `PluginConfig` (store plugin credentials)
    - `id`, `plugin_id`, `config_json` (encrypted), `enabled`, `last_sync`, `sync_frequency`
  - New table: `DataSourceMetadata` (track data lineage)
    - `id`, `source_type`, `source_id`, `asset_id`, `last_price_update`, `data_quality_score`
  - ~~Alembic migration script~~ (models added to models.py, migration pending)

- [x] **1.4** Configuration system enhancements ✅
  - New file: `config/data_sources.yaml`
  - Environment variable support for all credentials
  - ~~New file: `config/.env.example`~~ (deferred - env vars documented in data_sources.yaml)

- [x] **1.5** Rate limiting & caching utilities ✅
  - File: `src/data_manager/connectors/utils.py`
  - `RateLimiter` class with configurable intervals
  - `ResponseCache` class with TTL support
  - Exponential backoff retry decorator

**Deliverables**:

- `src/data_manager/connectors/base_connector.py`
- `src/data_manager/connectors/utils.py`
- `src/plugins/base.py`
- `src/plugins/manager.py`
- `src/plugins/registry.py`
- `src/database/migrations/xxx_add_import_tracking.py`
- `config/data_sources.yaml`
- `config/.env.example`

---

### Phase 2: CCXT Integration (Cryptocurrency Exchanges)

**Priority**: High | **Complexity**: Medium

**Supported Exchanges**: Binance, Coinbase, Kraken, OKX, Huobi, Gate.io

- [ ] **2.1** Implement CCXT connector
  - File: `src/data_manager/connectors/ccxt_connector.py`
  - Multi-exchange support via CCXT library
  - Methods: `authenticate_exchange()`, `get_exchange_balance()`, `get_exchange_transactions()`
  - Handle API rate limits per exchange
  - Unified error handling across exchanges

- [ ] **2.2** Crypto data reader
  - Add to: `src/data_manager/readers.py`
  - Function: `read_crypto_data(settings)` → `Dict[str, pd.DataFrame]`
  - Aggregate holdings across all configured exchanges
  - Deduplicate transactions by exchange + transaction_id

- [ ] **2.3** Crypto data cleaner
  - Add to: `src/data_manager/cleaners.py`
  - Functions: `clean_crypto_holdings()`, `clean_crypto_transactions()`
  - Normalize symbol names (BTC/USDT → Bitcoin)
  - Map transaction types (Trade, Deposit, Withdrawal, Fee)
  - Handle dust amounts and zero balances

- [ ] **2.4** Asset taxonomy updates
  - Update: `config/asset_taxonomy.yaml`
  - Add crypto-specific asset definitions
  - Add exchange metadata per asset

- [ ] **2.5** Web routes for crypto management
  - New blueprint: `src/web_app/blueprints/crypto/`
  - Routes: `/crypto/connect/<exchange>`, `/crypto/sync`, `/crypto/holdings`
  - API key setup form per exchange
  - Manual sync trigger
  - Holdings display with per-exchange breakdown

- [ ] **2.6** Configuration templates
  - New file: `config/integrations/ccxt.yaml.example`
  - Document all exchange-specific settings
  - Environment variable placeholders

**Deliverables**:

- `src/data_manager/connectors/ccxt_connector.py`
- `src/web_app/blueprints/crypto/__init__.py`
- `src/web_app/blueprints/crypto/routes.py`
- `src/web_app/templates/crypto/*.html`
- `config/integrations/ccxt.yaml.example`
- Updated `readers.py`, `cleaners.py`, `asset_taxonomy.yaml`

**Dependencies**:

- `ccxt>=4.0.0` (add to requirements.txt)

---

### Phase 3: Interactive Brokers (IBKR) Integration

**Priority**: High | **Complexity**: High

- [ ] **3.1** Implement IBKR connector
  - File: `src/data_manager/connectors/ibkr_connector.py`
  - Support JWT and API key authentication
  - Methods: `authenticate()`, `get_accounts()`, `get_holdings()`, `get_transactions()`
  - Handle multiple account types (Individual, Joint, IRA, 401k)
  - Support for various security types (Stocks, Bonds, Options, Futures, Forex)

- [ ] **3.2** IBKR data reader
  - Add to: `src/data_manager/readers.py`
  - Function: `read_ibkr_data(settings)` → `Dict[str, pd.DataFrame]`
  - Multi-account aggregation
  - Configurable transaction lookback period

- [ ] **3.3** IBKR data cleaner
  - Add to: `src/data_manager/cleaners.py`
  - Functions: `clean_ibkr_holdings()`, `clean_ibkr_transactions()`
  - Handle complex security types (options legs, futures contracts)
  - Map IBKR transaction types to standard types
  - Handle corporate actions (splits, dividends, mergers)

- [ ] **3.4** Web routes for IBKR
  - Add to: `src/web_app/blueprints/brokers/`
  - Routes: `/brokers/ibkr/connect`, `/brokers/ibkr/accounts`, `/brokers/ibkr/sync/<account_id>`
  - OAuth2 or API key setup flow
  - Account selection and sync configuration

- [ ] **3.5** Position type mapping
  - Configuration for mapping IBKR position types to asset taxonomy
  - Customizable per-account mappings

**Deliverables**:

- `src/data_manager/connectors/ibkr_connector.py`
- `src/web_app/blueprints/brokers/__init__.py`
- `src/web_app/blueprints/brokers/routes.py`
- `src/web_app/templates/brokers/*.html`
- `config/integrations/ibkr.yaml.example`
- Updated `readers.py`, `cleaners.py`

**Dependencies**:

- `ib_insync>=0.9.0` or IBKR REST API client (evaluate both options)

---

### Phase 4: Enhanced Schwab API Integration

**Priority**: High | **Complexity**: Medium

**Current Status**: Placeholder connector exists at `src/data_manager/connectors/schwab_connector.py`

- [ ] **4.1** Enhance Schwab connector with OAuth2
  - Upgrade: `src/data_manager/connectors/schwab_connector.py`
  - Implement full OAuth2 flow (PKCE recommended)
  - Secure token storage with automatic refresh
  - Methods: `get_account_positions()`, `get_account_orders()`, `get_price_history()`

- [ ] **4.2** CSV fallback mechanism
  - Keep existing CSV import as fallback
  - Auto-detect: Try API first, fall back to CSV on failure
  - Log API failures for debugging

- [ ] **4.3** OAuth callback route
  - Add to: `src/web_app/blueprints/brokers/`
  - Route: `/auth/schwab/callback`
  - Secure token exchange and storage

- [ ] **4.4** Account sync routes
  - Routes: `/brokers/schwab/connect`, `/brokers/schwab/accounts`, `/brokers/schwab/sync`
  - Account nickname management
  - Per-account sync toggle

**Deliverables**:

- Enhanced `src/data_manager/connectors/schwab_connector.py`
- OAuth callback routes
- `config/integrations/schwab.yaml.example`

**Dependencies**:

- `authlib>=1.0.0` or `requests-oauthlib>=1.3.0`

---

### Phase 5: Enhanced Market Data (Tiingo + Yahoo Finance)

**Priority**: Medium | **Complexity**: Low

- [ ] **5.1** Implement Tiingo connector
  - File: `src/data_manager/connectors/tiingo_connector.py`
  - Methods: `get_current_price()`, `get_historical_prices()`, `get_fundamentals()`, `search_symbol()`
  - Support for stocks, ETFs, crypto, forex
  - Caching with configurable TTL

- [ ] **5.2** Enhance market data connector with fallback
  - Upgrade: `src/data_manager/connectors/market_data_connector.py`
  - Multi-provider architecture with fallback chain
  - Configurable provider priority
  - Unified interface across providers

- [ ] **5.3** Price update scheduler
  - Background task for periodic price updates
  - Configurable update frequency per asset type
  - Smart update (skip weekends for stocks, etc.)

- [ ] **5.4** Configuration
  - New file: `config/integrations/tiingo.yaml.example`
  - Provider priority configuration
  - Cache settings per provider

**Deliverables**:

- `src/data_manager/connectors/tiingo_connector.py`
- Enhanced `src/data_manager/connectors/market_data_connector.py`
- `config/integrations/tiingo.yaml.example`

**Dependencies**:

- Existing `yfinance` for Yahoo Finance
- `tiingo>=0.5.0` or direct REST API calls

---

### Phase 6: Plugin System for Bank Integrations

**Priority**: Medium | **Complexity**: High

- [ ] **6.1** Complete plugin base class
  - File: `src/plugins/base.py`
  - Abstract class: `BankIntegrationPlugin`
  - Required methods: `authenticate()`, `get_accounts()`, `get_holdings()`, `get_transactions()`
  - Optional methods: `get_balances()`, `health_check()`, `logout()`
  - `PluginMetadata` dataclass for plugin info

- [ ] **6.2** Plugin manager implementation
  - File: `src/plugins/manager.py`
  - Class: `PluginManager`
  - Methods: `discover_plugins()`, `load_plugin()`, `list_plugins()`, `validate_plugin()`
  - Plugin directory scanning
  - Safe dynamic import with validation

- [ ] **6.3** Plugin manifest schema
  - YAML format for plugin configuration
  - Required fields: `id`, `name`, `version`, `author`, `authentication`
  - Optional fields: `dependencies`, `permissions`, `supported_countries`

- [ ] **6.4** Example plugins
  - `src/plugins/bank_plugins/icbc/` - ICBC (China)
  - `src/plugins/bank_plugins/chase/` - Chase (US)
  - `src/plugins/bank_plugins/template/` - Template for contributors
  - Each with full manifest and connector implementation

- [ ] **6.5** Plugin web routes
  - New blueprint: `src/web_app/blueprints/plugins/`
  - Routes: `/plugins/library`, `/plugins/install/<plugin_id>`, `/plugins/connect/<plugin_id>`, `/plugins/sync/<plugin_id>`
  - Plugin discovery UI
  - Authentication form (dynamic based on manifest)
  - Sync controls

- [ ] **6.6** Plugin security
  - Sandboxed execution environment (optional)
  - Import whitelist validation
  - Credential encryption
  - Audit logging

- [ ] **6.7** Plugin documentation
  - Developer guide for creating plugins
  - Plugin template with inline documentation
  - Contribution guidelines

**Deliverables**:

- `src/plugins/base.py`
- `src/plugins/manager.py`
- `src/plugins/registry.py`
- `src/plugins/bank_plugins/icbc/`
- `src/plugins/bank_plugins/chase/`
- `src/plugins/bank_plugins/template/`
- `src/web_app/blueprints/plugins/`
- `docs/automated-integrations/plugin_development.md`

---

### Phase 7: Unified Data Pipeline & Validation

**Priority**: High | **Complexity**: Medium

- [ ] **7.1** Unified data import orchestrator
  - File: `src/data_manager/import_orchestrator.py`
  - Coordinate data from all sources (API + CSV + Plugins)
  - Handle conflicts and duplicates
  - Merge holdings and transactions with deduplication
  - Data quality scoring

- [ ] **7.2** Data validation engine
  - File: `src/data_manager/validation.py`
  - Schema validation for all data sources
  - Balance reconciliation across sources
  - Duplicate transaction detection
  - Anomaly detection (large trades, rapid changes)

- [ ] **7.3** Import history tracking
  - Log all import operations to `ImportJob` table
  - Track: source, records imported, errors, duration
  - Provide audit trail for debugging

- [ ] **7.4** Error recovery
  - Retry failed imports with exponential backoff
  - Partial import support (continue from last success)
  - Manual intervention UI for unresolved errors

**Deliverables**:

- `src/data_manager/import_orchestrator.py`
- `src/data_manager/validation.py`
- Import history UI

---

### Phase 8: Web UI Enhancements

**Priority**: Medium | **Complexity**: Medium

- [ ] **8.1** Data source management dashboard
  - New route: `/settings/data-sources`
  - List all configured data sources
  - Status indicators (connected, error, last sync)
  - Quick actions (sync, disconnect, configure)

- [ ] **8.2** Integration health monitoring
  - Health check status for each integration
  - API quota usage display
  - Error log viewer

- [ ] **8.3** Manual sync controls
  - One-click sync for individual sources
  - Batch sync for all sources
  - Sync scheduling configuration

- [ ] **8.4** Import history viewer
  - Route: `/settings/import-history`
  - Filterable list of past imports
  - Error details and resolution actions

- [ ] **8.5** First-run integration setup
  - Extend onboarding flow
  - "Connect your accounts" step after demo mode
  - Guided setup for popular integrations

**Deliverables**:

- Data source dashboard templates
- Import history templates
- Extended onboarding flow

---

### Phase 9: Testing & Documentation

**Priority**: High | **Complexity**: Medium

- [ ] **9.1** Unit tests for connectors
  - Mock API responses for each connector
  - Test authentication flows
  - Test data normalization
  - Test error handling

- [ ] **9.2** Integration tests
  - End-to-end import flow
  - Multi-source data merging
  - Database integrity after import

- [ ] **9.3** Performance tests
  - Large portfolio import (1000+ transactions)
  - Concurrent API calls
  - Memory usage profiling

- [ ] **9.4** User documentation
  - Setup guide per integration
  - Troubleshooting guide
  - FAQ

- [ ] **9.5** API documentation
  - Connector interface reference
  - Plugin development guide
  - Configuration reference

**Deliverables**:

- `tests/connectors/`
- `tests/integration/test_data_import.py`
- `docs/automated-integrations/setup_guides/`
- `docs/automated-integrations/troubleshooting.md`

---

## Progress Log

| Date | Phase | Progress | Next Steps |
|------|-------|----------|------------|
| 2026-01-09 | 0 | Development plan created | Start Phase 1 |
| 2026-01-09 | 1 | **Phase 1 Complete** ✅ - Base connector interface, plugin framework, DB models, configuration | Start Phase 2 |
| 2026-01-09 | 2 | **Phase 2 Complete** ✅ - CCXT connector for 100+ crypto exchanges | Start Phase 3 |
| 2026-01-09 | 3 | **Phase 3 Complete** ✅ - IBKR connector with Client Portal API | Start Phase 4 |
| 2026-01-09 | 4 | Schwab OAuth deferred (existing placeholder sufficient for now) | Phase 5 |
| 2026-01-09 | 5 | **Phase 5 Complete** ✅ - Tiingo market data connector | Start Phase 7 |
| 2026-01-09 | 7 | **Phase 7 Complete** ✅ - Import orchestrator for unified data pipeline | Start Phase 8 |
| 2026-01-09 | 8 | **Phase 8 Complete** ✅ - Web UI with integrations blueprint and templates | Phase 6/9 |
| 2026-01-09 | 6 | **Phase 6 Complete** ✅ - Sample bank plugin + plugin development guide | Phase 9 |
| 2026-01-09 | 9 | **Phase 9 Complete** ✅ - 82 unit tests + setup guides + troubleshooting | All phases done! |

---

## Technical Specifications

### Connector Interface

```python
class BaseConnector(ABC):
    @abstractmethod
    def authenticate(self) -> Tuple[bool, str]:
        """Returns (success, message)"""
        pass

    @abstractmethod
    def get_holdings(self) -> Optional[pd.DataFrame]:
        """Returns DataFrame with columns:
        symbol, name, quantity, current_price, market_value, currency"""
        pass

    @abstractmethod
    def get_transactions(self, since_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """Returns DataFrame with columns:
        date, symbol, transaction_type, quantity, price, amount, currency, source_id"""
        pass
```

### Standard Transaction Types

| Type | Description |
|------|-------------|
| `Buy` | Purchase of asset |
| `Sell` | Sale of asset |
| `Dividend` | Dividend payment received |
| `Interest` | Interest payment received |
| `Deposit` | Cash/asset deposit |
| `Withdrawal` | Cash/asset withdrawal |
| `Transfer` | Internal transfer |
| `Fee` | Transaction fee |
| `Split` | Stock split |
| `Merger` | Merger/acquisition |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BINANCE_API_KEY` | Crypto | Binance API key |
| `BINANCE_API_SECRET` | Crypto | Binance API secret |
| `COINBASE_API_KEY` | Crypto | Coinbase API key |
| `COINBASE_API_SECRET` | Crypto | Coinbase API secret |
| `IBKR_JWT_TOKEN` | IBKR | Interactive Brokers JWT |
| `SCHWAB_CLIENT_ID` | Schwab | Schwab OAuth client ID |
| `SCHWAB_CLIENT_SECRET` | Schwab | Schwab OAuth client secret |
| `TIINGO_API_KEY` | Market | Tiingo API key |
| `ALPHA_VANTAGE_KEY` | Market | Alpha Vantage API key (optional) |

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API changes from providers | High | Medium | Version locking, abstraction layer |
| Rate limit exhaustion | Medium | Medium | Caching, queue system, batch requests |
| OAuth token expiration | Medium | High | Automatic refresh, re-auth flow |
| Data inconsistencies | High | Medium | Validation rules, reconciliation |
| Plugin security vulnerabilities | High | Low | Sandboxing, code review, permission model |
| Large portfolio performance | Medium | Medium | Pagination, background processing |

---

## Dependencies & Prerequisites

### New Python Dependencies

```
# Crypto exchanges
ccxt>=4.0.0

# Tiingo
tiingo>=0.5.0

# OAuth2
authlib>=1.0.0

# Interactive Brokers (evaluate)
ib_insync>=0.9.0
# OR use IBKR REST API directly
```

### External Requirements

- Exchange API keys with read permissions
- Schwab Developer Portal access
- IBKR account with API access enabled
- Tiingo free/paid account

---

## Success Metrics

1. **Integration adoption**: >30% of users connect at least one API
2. **Sync reliability**: >99% successful syncs
3. **Data accuracy**: <0.1% discrepancy vs manual import
4. **User retention**: 2x improvement vs CSV-only workflow
5. **Plugin contributions**: 5+ community plugins within 6 months

---

## Open Questions

1. Should we support Plaid/Yodlee for broader bank coverage? (Cost concern)
2. Should plugins run in a sandboxed environment? (Security vs complexity)
3. Should we support real-time WebSocket connections for crypto? (Complexity)
4. How to handle tax lot tracking across multiple sources?
5. Should we store raw API responses for debugging/audit?

---

## References

- [CCXT Documentation](https://docs.ccxt.com/)
- [Interactive Brokers API](https://www.interactivebrokers.com/en/trading/ib-api.php)
- [Schwab Developer Portal](https://developer.schwab.com/)
- [Tiingo API](https://api.tiingo.com/documentation/general/overview)
- [OAuth 2.0 Best Practices](https://oauth.net/2/best-practices/)
