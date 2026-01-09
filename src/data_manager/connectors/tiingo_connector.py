# Tiingo Market Data Connector
# src/data_manager/connectors/tiingo_connector.py

"""
Tiingo market data connector for stocks, ETFs, crypto, and forex.

Tiingo provides high-quality financial data with a generous free tier.
This connector implements the market data provider interface.

Usage:
    config = {'api_key': 'your_tiingo_api_key'}
    connector = TiingoConnector(config)
    connector.authenticate()
    price = connector.get_current_price('AAPL')
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

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


class TiingoConnector(BaseConnector):
    """
    Tiingo market data connector.

    Provides current and historical prices for stocks, ETFs, crypto, and forex.
    Implements fallback logic and caching to optimize API usage.

    Attributes:
        api_key: Tiingo API key
        base_url: Tiingo API base URL
        cache: Response cache
        rate_limiter: Rate limiter instance
    """

    metadata = ConnectorMetadata(
        name="Tiingo Market Data",
        connector_type=ConnectorType.MARKET_DATA,
        version="1.0.0",
        description="High-quality market data for stocks, ETFs, and crypto",
        supported_assets=["stocks", "etfs", "crypto", "forex"],
        requires_oauth=False,
        requires_api_key=True,
        rate_limit_per_minute=500,  # Free tier
        documentation_url="https://api.tiingo.com/documentation/general/overview"
    )

    BASE_URL = "https://api.tiingo.com"
    IEX_URL = "https://api.tiingo.com/iex"
    CRYPTO_URL = "https://api.tiingo.com/tiingo/crypto"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Tiingo connector.

        Args:
            config: Dictionary with:
                - api_key: Tiingo API key (required)
                - cache_ttl: Cache TTL in seconds (default 300)
        """
        super().__init__(config)

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library not installed. Run: pip install requests")

        self.api_key = config.get('api_key')
        self.cache = ResponseCache(ttl_seconds=config.get('cache_ttl', 300))
        self.rate_limiter = RateLimiter(
            calls_per_minute=config.get('rate_limit', 500),
            calls_per_second=10.0
        )
        self._session: Optional[requests.Session] = None

    def authenticate(self) -> Tuple[bool, str]:
        """
        Verify Tiingo API key.

        Returns:
            Tuple of (success, message)
        """
        if not self.api_key:
            return False, "API key not configured"

        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        })

        # Test API key with a simple request
        try:
            response = self._session.get(
                f"{self.BASE_URL}/api/test",
                timeout=10
            )
            if response.status_code == 200:
                self._authenticated = True
                return True, "Tiingo API key validated"
            elif response.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"API test failed: {response.status_code}"

        except requests.RequestException as e:
            return False, f"Connection error: {e}"

    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Market data provider - no holdings to fetch."""
        return None

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Market data provider - no transactions to fetch."""
        return None

    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', 'btcusd')

        Returns:
            Current price or None if not found
        """
        # Check cache first
        cache_key = f"price_{symbol}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Apply rate limiting
        self.rate_limiter.wait()

        # Determine if crypto or stock
        if self._is_crypto(symbol):
            price = self._get_crypto_price(symbol)
        else:
            price = self._get_stock_price(symbol)

        if price is not None:
            self.cache.set(cache_key, price)

        return price

    def _get_stock_price(self, symbol: str) -> Optional[float]:
        """Get stock/ETF price from IEX endpoint."""
        if not self._session:
            raise DataFetchError("Not authenticated")

        try:
            response = self._session.get(
                f"{self.IEX_URL}/{symbol}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0].get('last') or data[0].get('tngoLast')
            elif response.status_code == 404:
                logger.debug(f"Symbol not found: {symbol}")
            elif response.status_code == 429:
                raise RateLimitError("Tiingo rate limit exceeded", retry_after=60)

            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def _get_crypto_price(self, symbol: str) -> Optional[float]:
        """Get crypto price from Tiingo crypto endpoint."""
        if not self._session:
            raise DataFetchError("Not authenticated")

        # Normalize crypto symbol (e.g., BTC -> btcusd)
        normalized = symbol.lower()
        if not normalized.endswith('usd'):
            normalized = f"{normalized}usd"

        try:
            response = self._session.get(
                f"{self.CRYPTO_URL}/prices",
                params={'tickers': normalized},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price_data = data[0].get('priceData', [])
                    if price_data:
                        return price_data[0].get('close')
            elif response.status_code == 429:
                raise RateLimitError("Tiingo rate limit exceeded", retry_after=60)

            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching crypto price for {symbol}: {e}")
            return None

    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def get_historical_prices(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        frequency: str = 'daily'
    ) -> Optional[pd.DataFrame]:
        """
        Get historical prices for a symbol.

        Args:
            symbol: Ticker symbol
            start_date: Start date (default: 1 year ago)
            end_date: End date (default: today)
            frequency: 'daily', 'weekly', 'monthly', 'annually'

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, adjClose
        """
        if not self._session:
            raise DataFetchError("Not authenticated")

        # Defaults
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # Apply rate limiting
        self.rate_limiter.wait()

        try:
            if self._is_crypto(symbol):
                return self._get_crypto_history(symbol, start_date, end_date)
            else:
                return self._get_stock_history(symbol, start_date, end_date, frequency)

        except requests.RequestException as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return None

    def _get_stock_history(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str
    ) -> Optional[pd.DataFrame]:
        """Get historical stock prices."""
        response = self._session.get(
            f"{self.BASE_URL}/tiingo/daily/{symbol}/prices",
            params={
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'resampleFreq': frequency
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                return df
        elif response.status_code == 429:
            raise RateLimitError("Tiingo rate limit exceeded", retry_after=60)

        return None

    def _get_crypto_history(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Get historical crypto prices."""
        normalized = symbol.lower()
        if not normalized.endswith('usd'):
            normalized = f"{normalized}usd"

        response = self._session.get(
            f"{self.CRYPTO_URL}/prices",
            params={
                'tickers': normalized,
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'resampleFreq': '1day'
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                price_data = data[0].get('priceData', [])
                if price_data:
                    df = pd.DataFrame(price_data)
                    df['date'] = pd.to_datetime(df['date'])
                    return df
        elif response.status_code == 429:
            raise RateLimitError("Tiingo rate limit exceeded", retry_after=60)

        return None

    def search_symbol(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for symbols by name or ticker.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching symbols with metadata
        """
        if not self._session:
            return []

        self.rate_limiter.wait()

        try:
            response = self._session.get(
                f"{self.BASE_URL}/tiingo/utilities/search/{query}",
                params={'limit': limit},
                timeout=10
            )

            if response.status_code == 200:
                return response.json()

            return []

        except requests.RequestException as e:
            logger.error(f"Error searching for {query}: {e}")
            return []

    def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get fundamental data for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Dictionary with fundamental metrics
        """
        if not self._session:
            return None

        self.rate_limiter.wait()

        try:
            response = self._session.get(
                f"{self.BASE_URL}/tiingo/fundamentals/{symbol}/daily",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None

            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching fundamentals for {symbol}: {e}")
            return None

    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency."""
        crypto_symbols = {
            'BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'XRP', 'DOT', 'DOGE', 'AVAX',
            'MATIC', 'LINK', 'UNI', 'ATOM', 'LTC', 'ETC', 'XLM', 'ALGO',
            'NEAR', 'FTM', 'SAND', 'MANA', 'APE', 'SHIB', 'CRO',
            'USDT', 'USDC', 'BUSD', 'DAI'
        }
        return symbol.upper() in crypto_symbols or symbol.lower().endswith('usd')

    def health_check(self) -> Tuple[bool, str]:
        """Check if Tiingo API is accessible."""
        if not self._session:
            return False, "Not authenticated"

        try:
            response = self._session.get(f"{self.BASE_URL}/api/test", timeout=5)
            if response.status_code == 200:
                return True, "Tiingo API healthy"
            return False, f"API returned {response.status_code}"
        except requests.RequestException as e:
            return False, f"Connection error: {e}"

    def disconnect(self) -> bool:
        """Close the session."""
        if self._session:
            self._session.close()
            self._session = None
        self._authenticated = False
        self.cache.clear()
        return True
