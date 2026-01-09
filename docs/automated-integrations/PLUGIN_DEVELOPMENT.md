# Plugin Development Guide

This guide explains how to create custom data source plugins for the WealthOS Personal Investment System.

## Overview

Plugins extend WealthOS to connect with additional data sources like banks, regional brokers, or specialized financial services. The plugin system provides:

- **Secure loading** - Plugins are validated before execution
- **Standard interface** - All plugins implement the same base class
- **Automatic discovery** - Drop-in installation without code changes
- **Isolation** - Plugins run in the main process but with restricted imports

## Quick Start

### 1. Create Plugin Directory

```bash
mkdir -p src/plugins/bank_plugins/my_bank
```

### 2. Create manifest.yaml

```yaml
id: my_bank
name: My Bank Integration
version: 1.0.0
author: Your Name
description: Connect to My Bank for holdings and transactions

capabilities:
  - HOLDINGS
  - TRANSACTIONS

supported_countries:
  - US

authentication_type: credentials

required_fields:
  - username
  - password

optional_fields:
  - account_number
```

### 3. Create connector.py

```python
from src.plugins.base import BankIntegrationPlugin, PluginMetadata, PluginCapability

class MyBankPlugin(BankIntegrationPlugin):
    plugin_metadata = PluginMetadata(
        id="my_bank",
        name="My Bank Integration",
        version="1.0.0",
        author="Your Name",
        description="Connect to My Bank",
        capabilities=[PluginCapability.HOLDINGS, PluginCapability.TRANSACTIONS],
        supported_countries=["US"],
        authentication_type="credentials",
        required_fields=["username", "password"],
    )

    def authenticate(self):
        # Implement authentication
        pass

    def get_holdings(self, account_id=None):
        # Return holdings DataFrame
        pass

    def get_transactions(self, account_id=None, since_date=None, until_date=None):
        # Return transactions DataFrame
        pass
```

### 4. Create \_\_init\_\_.py

```python
from .connector import MyBankPlugin
__all__ = ['MyBankPlugin']
```

## Plugin Structure

```
src/plugins/bank_plugins/
└── my_bank/
    ├── __init__.py      # Package init, exports plugin class
    ├── manifest.yaml    # Plugin metadata (required)
    ├── connector.py     # Main plugin implementation
    └── utils.py         # Optional helper functions
```

## Required Files

### manifest.yaml

| Field | Required | Description |
|-------|----------|-------------|
| `id` | ✅ | Unique plugin identifier (lowercase, underscores) |
| `name` | ✅ | Display name |
| `version` | ✅ | Semantic version (e.g., "1.0.0") |
| `author` | ✅ | Plugin author name |
| `description` | ✅ | Brief description |
| `capabilities` | ✅ | List of supported features |
| `authentication_type` | ✅ | `api_key`, `oauth`, or `credentials` |
| `required_fields` | ✅ | Configuration fields required |
| `supported_countries` | ❌ | ISO country codes |
| `optional_fields` | ❌ | Additional config fields |
| `documentation_url` | ❌ | Help documentation link |

### connector.py

Must define a class that:

1. Extends `BankIntegrationPlugin`
2. Sets `plugin_metadata` class attribute
3. Implements required abstract methods

## Plugin Capabilities

Declare what your plugin can do:

| Capability | Description |
|------------|-------------|
| `HOLDINGS` | Fetch current account holdings/balances |
| `TRANSACTIONS` | Fetch transaction history |
| `BALANCES` | Get detailed balance breakdown |
| `TRANSFERS` | Initiate transfers (advanced) |
| `STATEMENTS` | Download account statements |
| `REAL_TIME` | Support real-time data updates |

## Implementing Methods

### authenticate()

```python
def authenticate(self) -> Tuple[bool, str]:
    """
    Authenticate with the data source.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # 1. Validate config
    valid, missing = self.validate_config()
    if not valid:
        return False, f"Missing: {missing}"
    
    # 2. Make API call
    try:
        response = requests.post(
            "https://api.mybank.com/auth",
            json={
                "username": self.config["username"],
                "password": self.config["password"],
            }
        )
        
        if response.status_code == 200:
            self._token = response.json()["token"]
            self._authenticated = True
            return True, "Connected successfully"
        else:
            return False, "Invalid credentials"
            
    except Exception as e:
        return False, f"Connection error: {e}"
```

### get_holdings()

```python
def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Fetch current holdings.
    
    Must return DataFrame with columns:
    - symbol: Asset identifier
    - name: Asset display name
    - quantity: Amount held
    - current_price: Current price
    - market_value: Total value (quantity * price)
    - currency: Currency code (USD, CNY, etc.)
    - account_id: Source account identifier
    """
    if not self.is_authenticated:
        return None
    
    # Fetch from API
    response = self._api_call("/accounts/holdings")
    
    # Transform to standard format
    holdings = []
    for item in response["holdings"]:
        holdings.append({
            "symbol": item["ticker"],
            "name": item["description"],
            "quantity": item["shares"],
            "current_price": item["price"],
            "market_value": item["shares"] * item["price"],
            "currency": "USD",
            "account_id": item["account_id"],
        })
    
    return pd.DataFrame(holdings)
```

### get_transactions()

```python
def get_transactions(
    self,
    account_id: Optional[str] = None,
    since_date: Optional[datetime] = None,
    until_date: Optional[datetime] = None
) -> Optional[pd.DataFrame]:
    """
    Fetch transaction history.
    
    Must return DataFrame with columns:
    - date: Transaction date (datetime)
    - symbol: Asset identifier
    - name: Description
    - transaction_type: Buy, Sell, Deposit, Withdrawal, etc.
    - quantity: Amount
    - price: Unit price
    - amount: Total amount
    - currency: Currency code
    - fees: Transaction fees
    - source_id: Unique ID for deduplication
    - account_id: Source account
    """
    if not self.is_authenticated:
        return None
    
    # Build date range params
    params = {}
    if since_date:
        params["start_date"] = since_date.strftime("%Y-%m-%d")
    if until_date:
        params["end_date"] = until_date.strftime("%Y-%m-%d")
    
    # Fetch from API
    response = self._api_call("/transactions", params=params)
    
    # Transform
    transactions = []
    for txn in response["transactions"]:
        transactions.append({
            "date": datetime.fromisoformat(txn["date"]),
            "symbol": txn.get("symbol", "CASH"),
            "name": txn["description"],
            "transaction_type": self._map_transaction_type(txn["type"]),
            "quantity": txn.get("quantity", 0),
            "price": txn.get("price", 0),
            "amount": txn["amount"],
            "currency": "USD",
            "fees": txn.get("fees", 0),
            "source_id": f"mybank_{txn['id']}",  # Important for deduplication!
            "account_id": txn["account_id"],
        })
    
    return pd.DataFrame(transactions)
```

## Error Handling

Use the provided exception classes:

```python
from src.data_manager.connectors.base_connector import (
    AuthenticationError,
    RateLimitError,
    DataFetchError,
)

# Authentication failure
raise AuthenticationError("Invalid credentials", source="my_bank")

# Rate limit exceeded
raise RateLimitError("Too many requests", retry_after=60)

# API failure
raise DataFetchError("Failed to fetch data", source="my_bank", endpoint="/holdings")
```

## Utility Classes

### RateLimiter

```python
from src.data_manager.connectors.utils import RateLimiter

class MyBankPlugin(BankIntegrationPlugin):
    def __init__(self, config):
        super().__init__(config)
        self._limiter = RateLimiter(calls_per_minute=30)
    
    def _api_call(self, endpoint):
        self._limiter.wait()  # Blocks if rate limit would be exceeded
        return requests.get(f"https://api.mybank.com{endpoint}")
```

### ResponseCache

```python
from src.data_manager.connectors.utils import ResponseCache

class MyBankPlugin(BankIntegrationPlugin):
    def __init__(self, config):
        super().__init__(config)
        self._cache = ResponseCache(ttl_seconds=300)
    
    def get_holdings(self, account_id=None):
        cache_key = f"holdings_{account_id}"
        
        # Check cache first
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Fetch and cache
        holdings = self._fetch_holdings(account_id)
        self._cache.set(cache_key, holdings)
        
        return holdings
```

## Security Guidelines

### DO ✅

- Validate all configuration before use
- Use HTTPS for all API calls
- Mask sensitive data in logs: `logger.info(f"User: {username[:3]}***")`
- Implement proper error handling
- Clean up resources in `disconnect()`

### DON'T ❌

- Log passwords or full account numbers
- Store credentials in plugin code
- Use `eval()`, `exec()`, or `subprocess`
- Import unsafe modules (blocked by plugin loader)
- Hardcode API endpoints (use config)

## Testing Your Plugin

### Unit Test

```python
import pytest
from src.plugins.bank_plugins.my_bank import MyBankPlugin

def test_authenticate_success():
    plugin = MyBankPlugin({
        "username": "test_user",
        "password": "test_pass",
    })
    
    success, message = plugin.authenticate()
    
    assert success is True
    assert "Connected" in message

def test_validate_config_missing_password():
    plugin = MyBankPlugin({"username": "test"})
    
    valid, missing = plugin.validate_config()
    
    assert valid is False
    assert "password" in missing
```

### Integration Test

```python
def test_full_sync_flow():
    plugin = MyBankPlugin(config)
    
    # Authenticate
    success, _ = plugin.authenticate()
    assert success
    
    # Get holdings
    holdings = plugin.get_holdings()
    assert holdings is not None
    assert len(holdings) > 0
    
    # Get transactions
    transactions = plugin.get_transactions()
    assert transactions is not None
    
    # Disconnect
    plugin.disconnect()
    assert not plugin.is_authenticated
```

## Distribution

To share your plugin:

1. Package as a ZIP file containing the plugin directory
2. Include a README with setup instructions
3. Document any external dependencies
4. Provide sample configuration

## Example Plugins

See the sample plugin for a complete working example:

- `src/plugins/bank_plugins/sample_bank/`

## Support

- GitHub Issues: Report bugs and feature requests
- Discussions: Ask questions and share plugins
- Wiki: Additional documentation and examples
