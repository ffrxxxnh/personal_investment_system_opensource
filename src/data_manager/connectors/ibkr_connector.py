# IBKR Interactive Brokers Connector
# src/data_manager/connectors/ibkr_connector.py

"""
Interactive Brokers connector for brokerage account integration.

Supports the IBKR Client Portal API (REST-based).
Provides access to account holdings, transactions, and market data.

Usage:
    config = {
        'gateway_url': 'https://localhost:5000',
        'jwt_token': 'your_jwt_token',  # Or use local gateway
    }
    connector = IBKRConnector(config)
    success, msg = connector.authenticate()
    holdings = connector.get_holdings()
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import pandas as pd

from .base_connector import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorType,
    AuthenticationError,
    DataFetchError,
    RateLimitError,
    ConfigurationError,
)
from .utils import RateLimiter, ResponseCache, retry_with_backoff

logger = logging.getLogger(__name__)

# Check if requests is available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None  # type: ignore


class IBKRConnector(BaseConnector):
    """
    Interactive Brokers connector using Client Portal API.

    The Client Portal API is a REST-based API that requires either:
    1. A local IB Gateway running (for self-hosted)
    2. A JWT token for cloud-based access

    Attributes:
        gateway_url: Base URL for the IBKR gateway
        accounts: List of linked account IDs
        cache: Response cache
        rate_limiter: Rate limiter instance
    """

    metadata = ConnectorMetadata(
        name="Interactive Brokers",
        connector_type=ConnectorType.BROKER,
        version="1.0.0",
        description="Connect to IBKR accounts for stocks, options, futures, and more",
        supported_assets=["stocks", "etfs", "options", "futures", "bonds", "forex"],
        requires_oauth=False,
        requires_api_key=True,
        rate_limit_per_minute=50,
        documentation_url="https://interactivebrokers.github.io/cpwebapi/"
    )

    # Transaction type mappings from IBKR to standard types
    TRANSACTION_TYPE_MAP = {
        'BUY': 'Buy',
        'SELL': 'Sell',
        'DIV': 'Dividend',
        'INT': 'Interest',
        'DEP': 'Deposit',
        'WITH': 'Withdrawal',
        'FEE': 'Fee',
        'SPLIT': 'Split',
        'MERGER': 'Merger',
        'TRANSFER': 'Transfer',
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IBKR connector.

        Args:
            config: Dictionary with:
                - gateway_url: IBKR gateway URL (default: https://localhost:5000)
                - jwt_token: JWT token for cloud access (optional)
                - account_filter: List of account IDs to sync (optional)
                - cache_ttl: Cache TTL in seconds (default 300)
                - verify_ssl: Verify SSL certificates (default False for local gateway)
        """
        super().__init__(config)

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library not installed. Run: pip install requests")

        self.gateway_url = config.get('gateway_url', 'https://localhost:5000')
        self.jwt_token = config.get('jwt_token')
        self.account_filter = config.get('account_filter', [])
        self.verify_ssl = config.get('verify_ssl', False)  # Local gateway uses self-signed cert

        self.accounts: List[str] = []
        self.cache = ResponseCache(ttl_seconds=config.get('cache_ttl', 300))
        self.rate_limiter = RateLimiter(calls_per_minute=50, calls_per_second=5.0)
        self._session: Optional[requests.Session] = None

    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with IBKR gateway.

        Returns:
            Tuple of (success, message)
        """
        self._session = requests.Session()

        # Set JWT token if provided
        if self.jwt_token:
            self._session.headers.update({
                'Authorization': f'Bearer {self.jwt_token}'
            })

        # Disable SSL warnings for local gateway
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Test connection and get accounts
        try:
            # First, check if gateway is accessible
            response = self._session.get(
                urljoin(self.gateway_url, '/v1/api/iserver/auth/status'),
                verify=self.verify_ssl,
                timeout=10
            )

            if response.status_code != 200:
                return False, f"Gateway returned {response.status_code}"

            auth_status = response.json()
            if not auth_status.get('authenticated'):
                return False, "Gateway not authenticated. Please login via IB Gateway first."

            # Get linked accounts
            accounts_response = self._session.get(
                urljoin(self.gateway_url, '/v1/api/portfolio/accounts'),
                verify=self.verify_ssl,
                timeout=10
            )

            if accounts_response.status_code == 200:
                accounts_data = accounts_response.json()
                self.accounts = [acc.get('id') for acc in accounts_data if acc.get('id')]

                # Apply account filter if specified
                if self.account_filter:
                    self.accounts = [a for a in self.accounts if a in self.account_filter]

                if not self.accounts:
                    return False, "No accounts found or all filtered out"

                self._authenticated = True
                return True, f"Connected to {len(self.accounts)} account(s)"
            else:
                return False, f"Failed to get accounts: {accounts_response.status_code}"

        except requests.RequestException as e:
            return False, f"Connection error: {e}"

    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch holdings from IBKR accounts.

        Args:
            account_id: Specific account to query (None for all)

        Returns:
            DataFrame with holdings
        """
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated. Call authenticate() first.")

        all_holdings: List[pd.DataFrame] = []
        accounts_to_query = [account_id] if account_id else self.accounts

        for acct in accounts_to_query:
            try:
                holdings = self._fetch_account_holdings(acct)
                if holdings is not None and len(holdings) > 0:
                    all_holdings.append(holdings)
            except Exception as e:
                logger.error(f"Failed to fetch holdings for account {acct}: {e}")

        if not all_holdings:
            return self._create_empty_holdings_df()

        return pd.concat(all_holdings, ignore_index=True)

    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def _fetch_account_holdings(self, account_id: str) -> Optional[pd.DataFrame]:
        """Fetch holdings for a single account."""
        # Check cache
        cache_key = f"holdings_{account_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        self.rate_limiter.wait()

        try:
            response = self._session.get(
                urljoin(self.gateway_url, f'/v1/api/portfolio/{account_id}/positions/0'),
                verify=self.verify_ssl,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"IBKR returned {response.status_code} for positions")
                return None

            positions = response.json()
            if not positions:
                return None

            holdings = []
            for pos in positions:
                holdings.append({
                    'symbol': pos.get('ticker', pos.get('conid', 'UNKNOWN')),
                    'name': pos.get('contractDesc', pos.get('ticker', 'Unknown')),
                    'quantity': pos.get('position', 0),
                    'current_price': pos.get('mktPrice', 0),
                    'market_value': pos.get('mktValue', 0),
                    'cost_basis': pos.get('avgCost', 0) * pos.get('position', 0),
                    'currency': pos.get('currency', 'USD'),
                    'account_id': account_id,
                })

            df = pd.DataFrame(holdings)
            self.cache.set(cache_key, df)
            return df

        except requests.RequestException as e:
            raise DataFetchError(f"Failed to fetch positions: {e}", "ibkr")

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch transactions from IBKR accounts.

        Args:
            account_id: Specific account to query (None for all)
            since_date: Start date for transactions
            until_date: End date for transactions

        Returns:
            DataFrame with transactions
        """
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated. Call authenticate() first.")

        all_transactions: List[pd.DataFrame] = []
        accounts_to_query = [account_id] if account_id else self.accounts

        for acct in accounts_to_query:
            try:
                txns = self._fetch_account_transactions(acct, since_date, until_date)
                if txns is not None and len(txns) > 0:
                    all_transactions.append(txns)
            except Exception as e:
                logger.error(f"Failed to fetch transactions for account {acct}: {e}")

        if not all_transactions:
            return self._create_empty_transactions_df()

        result = pd.concat(all_transactions, ignore_index=True)
        return result.sort_values('date', ascending=False)

    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def _fetch_account_transactions(
        self,
        account_id: str,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Fetch transactions for a single account."""
        self.rate_limiter.wait()

        # Default date range
        if until_date is None:
            until_date = datetime.now()
        if since_date is None:
            since_date = until_date - timedelta(days=365)

        try:
            # IBKR uses flex queries for historical data
            # For real-time, we use the orders endpoint
            response = self._session.get(
                urljoin(self.gateway_url, f'/v1/api/iserver/account/trades'),
                params={
                    'days': (until_date - since_date).days
                },
                verify=self.verify_ssl,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"IBKR returned {response.status_code} for trades")
                return None

            trades = response.json()
            if not trades:
                return None

            transactions = []
            for trade in trades:
                trans_type = self.TRANSACTION_TYPE_MAP.get(
                    trade.get('side', '').upper(),
                    trade.get('side', 'Unknown')
                )

                transactions.append({
                    'date': datetime.fromtimestamp(trade.get('trade_time_r', 0) / 1000) if trade.get('trade_time_r') else datetime.now(),
                    'symbol': trade.get('symbol', 'UNKNOWN'),
                    'name': trade.get('description', trade.get('symbol', 'Unknown')),
                    'transaction_type': trans_type,
                    'quantity': abs(trade.get('size', 0)),
                    'price': trade.get('price', 0),
                    'amount': trade.get('net_amount', 0),
                    'currency': trade.get('currency', 'USD'),
                    'fees': trade.get('commission', 0),
                    'source_id': f"ibkr_{trade.get('execution_id', '')}",
                    'account_id': account_id,
                })

            return pd.DataFrame(transactions)

        except requests.RequestException as e:
            raise DataFetchError(f"Failed to fetch transactions: {e}", "ibkr")

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get information about connected accounts."""
        if not self.is_authenticated:
            return None

        accounts_info = {}
        for account_id in self.accounts:
            try:
                response = self._session.get(
                    urljoin(self.gateway_url, f'/v1/api/portfolio/{account_id}/meta'),
                    verify=self.verify_ssl,
                    timeout=10
                )

                if response.status_code == 200:
                    meta = response.json()
                    accounts_info[account_id] = {
                        'account_id': account_id,
                        'account_type': meta.get('accountType', 'Unknown'),
                        'base_currency': meta.get('baseCurrency', 'USD'),
                        'status': 'connected',
                    }
            except Exception as e:
                logger.error(f"Failed to get meta for {account_id}: {e}")

        return accounts_info

    def health_check(self) -> Tuple[bool, str]:
        """Check if IBKR gateway is accessible."""
        if not self._session:
            return False, "Not authenticated"

        try:
            response = self._session.get(
                urljoin(self.gateway_url, '/v1/api/iserver/auth/status'),
                verify=self.verify_ssl,
                timeout=5
            )
            if response.status_code == 200:
                status = response.json()
                if status.get('authenticated'):
                    return True, "IBKR gateway healthy and authenticated"
                return False, "IBKR gateway not authenticated"
            return False, f"Gateway returned {response.status_code}"
        except requests.RequestException as e:
            return False, f"Connection error: {e}"

    def disconnect(self) -> bool:
        """Close the session."""
        if self._session:
            self._session.close()
            self._session = None
        self.accounts = []
        self._authenticated = False
        self.cache.clear()
        return True
