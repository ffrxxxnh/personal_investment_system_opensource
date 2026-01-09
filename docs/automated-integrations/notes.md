# Research Notes: Automated Data Integrations

This document captures research findings, design decisions, and alternatives considered during planning.

---

## Table of Contents

1. [Current System Analysis](#current-system-analysis)
2. [API Provider Research](#api-provider-research)
3. [Design Decisions](#design-decisions)
4. [Security Considerations](#security-considerations)
5. [Alternative Approaches](#alternative-approaches)
6. [Community Feedback](#community-feedback)

---

## Current System Analysis

### Existing Data Flow

**Path**: `Excel/CSV → Readers → Cleaners → DataManager → SQLite DB`

**Key Files Analyzed**:

| File | Purpose | Lines |
|------|---------|-------|
| `src/data_manager/readers.py` | Read Excel/CSV files | ~400 |
| `src/data_manager/cleaners.py` | Normalize data | ~300 |
| `src/data_manager/manager.py` | Central data hub | ~500 |
| `src/data_manager/db_sync.py` | Sync to SQLite | ~200 |
| `src/data_import/csv_importer.py` | Flexible CSV import | ~300 |

### Existing Connectors

| Connector | Status | Notes |
|-----------|--------|-------|
| `schwab_connector.py` | Placeholder | Framework only, no OAuth |
| `market_data_connector.py` | Partial | Yahoo Finance works, others need keys |
| `google_finance_connector.py` | Working | Exchange rates, no API key needed |

### Data Models

**Transaction table** (most important):
- `transaction_id`, `date`, `asset_id`, `asset_name`
- `transaction_type`, `shares`, `price`, `amount`
- `currency`, `exchange_rate`, `source`, `created_at`

**Holding table**:
- `snapshot_date`, `asset_id`, `shares`, `current_price`
- `market_value`, `cost_basis`, `unrealized_pnl`

**Asset table**:
- `asset_id` (PK), `asset_name`, `asset_type`, `asset_class`
- `metadata_json` for flexible storage

### Pain Points Identified

1. **Manual CSV download** - Users must export from brokers, format in Excel
2. **Column mapping** - Every broker has different column names
3. **Date formats** - MM/DD/YYYY vs DD/MM/YYYY vs YYYY-MM-DD
4. **Currency handling** - Mixed currencies need manual exchange rates
5. **Deduplication** - Re-importing same transactions creates duplicates
6. **Stale prices** - Market values become outdated

---

## API Provider Research

### Cryptocurrency Exchanges

#### CCXT Library

**Pros**:
- Unified API for 100+ exchanges
- Well-maintained (9k+ GitHub stars)
- Handles rate limiting automatically
- Good documentation

**Cons**:
- Large dependency (~10MB)
- Some exchanges have limited API support
- WebSocket support varies

**Recommendation**: Use CCXT. It's the de facto standard.

**Key Methods**:
```python
exchange.fetch_balance()         # Current holdings
exchange.fetch_my_trades()       # Trade history
exchange.fetch_deposits()        # Deposit history
exchange.fetch_withdrawals()     # Withdrawal history
exchange.fetch_ticker('BTC/USDT')  # Current price
```

**Rate Limits by Exchange**:
| Exchange | Requests/min | Notes |
|----------|--------------|-------|
| Binance | 1200 | Weight-based system |
| Coinbase | 10 | Very restrictive |
| Kraken | 15-20 | Per endpoint |
| OKX | 600 | Generous |

#### CoinGecko API (Price Fallback)

- Free tier: 50 calls/min
- Good for historical prices
- No API key needed for basic use
- Use as fallback for exchange-native prices

### Traditional Brokers

#### Interactive Brokers

**API Options**:
1. **Client Portal API** (REST) - Newer, easier
2. **TWS API** (Socket) - Legacy, more features
3. **ib_insync** (Python wrapper) - Simplifies TWS API

**Recommendation**: Start with Client Portal API for simplicity.

**Authentication**:
- Requires IB Gateway running locally
- Or JWT token for direct API access
- OAuth2 not available for retail accounts

**Limitations**:
- 50 requests/second max
- Some endpoints require live trading permissions
- Paper trading account available for testing

**Key Endpoints**:
```
GET /portfolio/accounts
GET /portfolio/{accountId}/positions/0
GET /iserver/account/{accountId}/orders
```

#### Charles Schwab

**API Status**:
- Developer Portal launched 2023
- OAuth2 authentication
- Limited to approved developers initially

**Documentation**: https://developer.schwab.com/

**Authentication Flow**:
1. User clicks "Connect Schwab"
2. Redirect to Schwab OAuth page
3. User logs in and authorizes
4. Callback with auth code
5. Exchange for access token
6. Store refresh token

**Endpoints** (expected):
```
GET /accounts
GET /accounts/{accountId}/positions
GET /accounts/{accountId}/transactions
```

**Fallback Strategy**: Keep CSV import working. If OAuth fails or times out, fall back to CSV seamlessly.

### Market Data Providers

#### Tiingo

**Pricing**:
- Free: 500 unique symbols/month
- Starter ($10/mo): 50k API calls
- Power ($30/mo): Unlimited

**Pros**:
- High-quality data
- Crypto + stocks + forex
- Good historical data
- Fundamentals available

**Cons**:
- Free tier limited
- No real-time for free tier

**Endpoints**:
```
GET /iex/{ticker}/prices
GET /tiingo/daily/{ticker}/prices
GET /tiingo/crypto/prices
```

#### Yahoo Finance (yfinance)

**Pros**:
- Free, no API key
- Good coverage
- Easy to use

**Cons**:
- Unofficial API, may break
- Rate limits not documented
- Data quality varies

**Current Usage**: Already used in `market_data_connector.py`

**Recommendation**: Keep Yahoo as fallback, add Tiingo as primary for users who set up API key.

#### Alpha Vantage

**Pricing**:
- Free: 5 requests/minute, 500/day
- Premium: $50/month

**Pros**:
- Free tier available
- Good for infrequent updates
- Forex and crypto support

**Cons**:
- Very restrictive rate limits
- Slow for bulk updates

**Recommendation**: Use as tertiary fallback only.

---

## Design Decisions

### Decision 1: Plugin Architecture vs. Built-in Connectors

**Options Considered**:

| Option | Pros | Cons |
|--------|------|------|
| All built-in | Simpler, guaranteed quality | Maintenance burden, slow to add new sources |
| All plugins | Maximum extensibility | Security concerns, quality varies |
| Hybrid | Best of both | More complex architecture |

**Decision**: **Hybrid approach**

- Built-in: Major brokers (Schwab, IBKR) and CCXT
- Plugins: Bank integrations, regional services
- Rationale: Core integrations need high quality; community can contribute others

### Decision 2: Authentication Storage

**Options Considered**:

| Option | Security | Complexity | User Experience |
|--------|----------|------------|-----------------|
| Plain text in DB | Low | Low | Good |
| Encrypted in DB | Medium | Medium | Good |
| OS keychain | High | High | Platform-specific |
| External vault | High | High | Overkill for personal use |

**Decision**: **Encrypted in database**

- Use Fernet symmetric encryption (from cryptography package)
- Master key from SECRET_KEY environment variable
- Store encrypted credentials in `plugin_configs` table
- Rationale: Good balance of security and simplicity for personal use

### Decision 3: Sync Frequency

**Options Considered**:

| Frequency | Pros | Cons |
|-----------|------|------|
| Real-time (WebSocket) | Latest data | Complex, high resource use |
| Hourly | Fresh data | Rate limit concerns |
| Daily | Simple, reliable | Stale for active traders |
| Manual | User control | Defeats automation purpose |

**Decision**: **Configurable with daily default**

- Default: Daily sync at user-specified time
- Optional: Hourly for crypto (high volatility)
- Manual sync button always available
- Rationale: Balances freshness with API rate limits

### Decision 4: Error Handling Strategy

**Options**:

1. **Fail fast**: Stop on first error
2. **Best effort**: Continue, log errors
3. **Retry with backoff**: Automatic retry

**Decision**: **Best effort + Retry + Logging**

- Retry transient errors (network, rate limit) with exponential backoff
- Continue processing other sources if one fails
- Log all errors with full context
- Show summary to user (X succeeded, Y failed)

### Decision 5: Data Deduplication

**Problem**: How to avoid importing same transaction twice?

**Options**:

| Method | Reliability | Complexity |
|--------|-------------|------------|
| External ID only | Medium | Low |
| Hash of all fields | High | Medium |
| Date + amount + symbol | Low | Low |

**Decision**: **External ID + Hash fallback**

- Primary: Use source's transaction ID (most reliable)
- Fallback: Hash of (date, symbol, type, amount, source)
- Store source_id in Transaction table
- Check before insert

---

## Security Considerations

### API Key Security

**Requirements**:
1. Never log API keys or secrets
2. Never include in git commits
3. Encrypt at rest in database
4. Use environment variables for local development

**Implementation**:
```python
# Loading from environment
import os
api_key = os.environ.get('BINANCE_API_KEY')

# Encrypted storage
from cryptography.fernet import Fernet
cipher = Fernet(master_key)
encrypted = cipher.encrypt(api_key.encode())
```

### Plugin Sandboxing

**Risks**:
- Malicious code execution
- Credential theft
- System access

**Mitigations**:
1. **Import whitelist**: Only allow safe modules
2. **Code review**: Manual review for community plugins
3. **Signature verification**: Sign official plugins
4. **Capability-based access**: Plugins declare required permissions

**Minimum Viable Security**:
- Warn users about untrusted plugins
- Scan for dangerous patterns (eval, exec, os.system)
- Run in separate process (future enhancement)

### OAuth2 Best Practices

1. Use PKCE for browser flows
2. Store refresh tokens encrypted
3. Validate all redirect URIs
4. Set appropriate token expiry
5. Implement token refresh before expiry

---

## Alternative Approaches

### Rejected: Plaid Integration

**Plaid** provides unified bank/brokerage API.

**Why Rejected**:
- Cost: $500/month minimum for production
- Complexity: Requires business verification
- Overkill: For personal use, direct APIs are sufficient

**When to Reconsider**: If project becomes commercial SaaS

### Rejected: Selenium/Browser Automation

**Idea**: Use browser automation to scrape broker websites

**Why Rejected**:
- Fragile: Breaks when websites change
- ToS violation: Most brokers prohibit scraping
- Maintenance burden: Constant updates needed
- Security risk: Storing login credentials

### Considered: Aggregator Services

**Services**: Yodlee, Finicity, MX

**Why Not Now**:
- Similar cost issues as Plaid
- Aimed at enterprise customers
- May be useful for future commercial version

---

## Community Feedback

### User Survey Results (Hypothetical)

Based on GitHub issues and similar projects:

**Most Requested Integrations**:
1. Interactive Brokers (45%)
2. Binance/Crypto (40%)
3. Schwab (30%)
4. Fidelity (25%)
5. TD Ameritrade (20%)
6. Chinese banks (15%)

**Pain Points Mentioned**:
- "I spend 2 hours every month exporting and formatting data"
- "CSV column names keep changing"
- "My broker added a new field and broke my import"
- "I want to see my crypto in the same dashboard"

### Competitor Analysis

**Portfolio Visualizer** (portfoliovisualizer.com):
- CSV import only
- No API integrations
- Limited customization

**Kubera** (kubera.com):
- Plaid integration
- $150/year subscription
- Good UX, limited analysis

**Lunch Money** (lunchmoney.app):
- Budget focused
- Plaid integration
- $100/year

**Takeaway**: There's a gap for a free, open-source solution with good API integrations and analysis capabilities.

---

## Open Research Questions

### Q1: How to handle tax lot tracking across sources?

**Context**: When assets are transferred between brokers, cost basis may be lost.

**Options**:
1. Require user to manually specify cost basis on transfer
2. Use first-in-first-out (FIFO) as default
3. Try to match based on purchase date and quantity

**Status**: Needs more research. For now, use FIFO default.

### Q2: Should we support real-time streaming?

**Context**: Some users want live portfolio updates.

**Options**:
1. WebSocket connections to exchanges
2. Frequent polling (every minute)
3. Push notifications only

**Status**: Deferred to v2. Daily updates are sufficient for most users.

### Q3: How to handle multi-currency portfolios?

**Context**: User may have USD, EUR, CNY assets.

**Current Approach**: Convert all to base currency using daily rates.

**Open Issues**:
- When to snapshot exchange rates?
- How to handle unrealized currency gains?
- Tax implications of currency conversion?

**Status**: Use end-of-day rates from Google Finance. Document limitations.

---

## References

### Documentation Links

- [CCXT Documentation](https://docs.ccxt.com/)
- [Interactive Brokers API](https://interactivebrokers.github.io/tws-api/)
- [Schwab Developer Portal](https://developer.schwab.com/)
- [Tiingo API Docs](https://api.tiingo.com/documentation/general/overview)
- [OAuth 2.0 RFC](https://datatracker.ietf.org/doc/html/rfc6749)

### Related Projects

- [ccxt](https://github.com/ccxt/ccxt) - Crypto exchange library
- [yfinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance API
- [ib_insync](https://github.com/erdewit/ib_insync) - IB Python wrapper
- [plaid-python](https://github.com/plaid/plaid-python) - Plaid SDK (reference only)

### Articles & Tutorials

- [Building a Portfolio Tracker](https://example.com) - Design patterns
- [Secure Credential Storage in Python](https://example.com) - Best practices
- [OAuth2 for Desktop Apps](https://example.com) - Implementation guide

---

*Last Updated: 2026-01-09*
