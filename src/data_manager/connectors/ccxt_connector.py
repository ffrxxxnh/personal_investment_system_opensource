# CCXT Cryptocurrency Exchange Connector
# src/data_manager/connectors/ccxt_connector.py

"""
CCXT-based connector for cryptocurrency exchanges.

Supports: Binance, Coinbase, Kraken, OKX, Huobi, Gate.io, and 100+ others
via the unified CCXT library.

Usage:
    config = {
        'exchanges': {
            'binance': {
                'api_key': 'xxx',
                'api_secret': 'xxx',
                'enabled': True
            }
        }
    }
    connector = CCXTConnector(config)
    success, msg = connector.authenticate()
    holdings = connector.get_holdings()
"""

import logging
from datetime import datetime
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

# Check if CCXT is available
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    ccxt = None  # type: ignore


class CCXTConnector(BaseConnector):
    """
    Multi-exchange cryptocurrency connector using CCXT library.

    Provides unified interface to fetch holdings and transactions from
    100+ cryptocurrency exchanges.

    Attributes:
        exchanges: Dictionary of authenticated exchange instances
        cache: Response cache for reducing API calls
    """

    metadata = ConnectorMetadata(
        name="CCXT Crypto Exchanges",
        connector_type=ConnectorType.CRYPTO_EXCHANGE,
        version="1.0.0",
        description="Connect to 100+ cryptocurrency exchanges via CCXT",
        supported_assets=["crypto"],
        requires_oauth=False,
        requires_api_key=True,
        rate_limit_per_minute=60,
        documentation_url="https://docs.ccxt.com/"
    )

    # Supported exchanges with specific configurations
    EXCHANGE_CONFIGS: Dict[str, Dict[str, Any]] = {
        'binance': {'rateLimit': 1200, 'enableRateLimit': True},
        'coinbase': {'rateLimit': 350, 'enableRateLimit': True},
        'kraken': {'rateLimit': 3000, 'enableRateLimit': True},
        'okx': {'rateLimit': 100, 'enableRateLimit': True},
        'huobi': {'rateLimit': 500, 'enableRateLimit': True},
        'gateio': {'rateLimit': 900, 'enableRateLimit': True},
        'kucoin': {'rateLimit': 334, 'enableRateLimit': True},
        'bybit': {'rateLimit': 100, 'enableRateLimit': True},
    }

    # Common crypto name mappings
    CRYPTO_NAMES: Dict[str, str] = {
        'BTC': 'Bitcoin',
        'ETH': 'Ethereum',
        'BNB': 'Binance Coin',
        'SOL': 'Solana',
        'ADA': 'Cardano',
        'XRP': 'Ripple',
        'DOT': 'Polkadot',
        'DOGE': 'Dogecoin',
        'AVAX': 'Avalanche',
        'MATIC': 'Polygon',
        'LINK': 'Chainlink',
        'UNI': 'Uniswap',
        'ATOM': 'Cosmos',
        'LTC': 'Litecoin',
        'ETC': 'Ethereum Classic',
        'XLM': 'Stellar',
        'ALGO': 'Algorand',
        'NEAR': 'NEAR Protocol',
        'FTM': 'Fantom',
        'SAND': 'The Sandbox',
        'MANA': 'Decentraland',
        'APE': 'ApeCoin',
        'SHIB': 'Shiba Inu',
        'CRO': 'Cronos',
        # Stablecoins
        'USDT': 'Tether',
        'USDC': 'USD Coin',
        'BUSD': 'Binance USD',
        'DAI': 'Dai',
        'TUSD': 'TrueUSD',
        'USDP': 'Pax Dollar',
    }

    # Stablecoins (always valued at ~$1)
    STABLECOINS = {'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'FRAX', 'GUSD'}

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CCXT connector.

        Args:
            config: Dictionary with structure:
                {
                    'exchanges': {
                        '<exchange_id>': {
                            'api_key': str,
                            'api_secret': str,
                            'password': str (optional, for some exchanges),
                            'enabled': bool,
                            'sandbox': bool (optional, for testing)
                        }
                    },
                    'cache_ttl': int (optional, seconds)
                }
        """
        super().__init__(config)

        if not CCXT_AVAILABLE:
            raise ImportError(
                "CCXT library not installed. Run: pip install ccxt"
            )

        self.exchanges: Dict[str, Any] = {}  # exchange_id -> ccxt.Exchange
        self.cache = ResponseCache(ttl_seconds=config.get('cache_ttl', 300))
        self._rate_limiters: Dict[str, RateLimiter] = {}

    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with all configured exchanges.

        Returns:
            Tuple of (all_success: bool, message: str)
        """
        exchanges_config = self.config.get('exchanges', {})
        if not exchanges_config:
            return False, "No exchanges configured"

        results: List[Tuple[str, bool, str]] = []

        for exchange_id, ex_config in exchanges_config.items():
            if not ex_config.get('enabled', True):
                logger.debug(f"Skipping disabled exchange: {exchange_id}")
                continue

            try:
                success, msg = self._authenticate_exchange(exchange_id, ex_config)
                results.append((exchange_id, success, msg))
            except Exception as e:
                logger.error(f"Failed to authenticate {exchange_id}: {e}")
                results.append((exchange_id, False, str(e)))

        # Build summary
        successful = [r[0] for r in results if r[1]]
        failed = [(r[0], r[2]) for r in results if not r[1]]

        if not results:
            return False, "No exchanges to authenticate"

        self._authenticated = len(successful) > 0

        if failed:
            fail_msg = "; ".join([f"{ex}: {msg}" for ex, msg in failed])
            if successful:
                return True, f"Connected to {successful}. Failed: {fail_msg}"
            return False, f"All connections failed: {fail_msg}"

        return True, f"Connected to {len(successful)} exchange(s): {successful}"

    def _authenticate_exchange(
        self,
        exchange_id: str,
        ex_config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Authenticate with a single exchange.

        Args:
            exchange_id: Exchange identifier (e.g., 'binance')
            ex_config: Exchange configuration

        Returns:
            Tuple of (success, message)

        Raises:
            AuthenticationError: If authentication fails
        """
        if exchange_id not in ccxt.exchanges:
            raise AuthenticationError(f"Unknown exchange: {exchange_id}", exchange_id)

        # Get exchange class
        exchange_class = getattr(ccxt, exchange_id)

        # Build exchange config
        config = {
            'apiKey': ex_config.get('api_key'),
            'secret': ex_config.get('api_secret'),
            **self.EXCHANGE_CONFIGS.get(exchange_id, {'enableRateLimit': True})
        }

        # Add password if required (e.g., OKX, KuCoin)
        if 'password' in ex_config:
            config['password'] = ex_config['password']

        # Use sandbox/testnet if specified
        if ex_config.get('sandbox'):
            config['sandbox'] = True

        # Instantiate exchange
        exchange = exchange_class(config)

        # Test connection by fetching balance
        try:
            balance = exchange.fetch_balance()
            self.exchanges[exchange_id] = exchange

            # Create rate limiter for this exchange
            rate_limit = self.EXCHANGE_CONFIGS.get(exchange_id, {}).get('rateLimit', 1000)
            calls_per_second = 1000 / rate_limit if rate_limit > 0 else 1
            self._rate_limiters[exchange_id] = RateLimiter(
                calls_per_minute=60,
                calls_per_second=calls_per_second
            )

            logger.info(f"Successfully authenticated with {exchange_id}")
            return True, "OK"

        except ccxt.AuthenticationError as e:
            raise AuthenticationError(f"Authentication failed: {e}", exchange_id)
        except ccxt.ExchangeError as e:
            raise AuthenticationError(f"Exchange error: {e}", exchange_id)

    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch holdings from all authenticated exchanges.

        Args:
            account_id: If provided, only fetch from this exchange

        Returns:
            DataFrame with columns: symbol, name, quantity, current_price,
            market_value, currency, exchange
        """
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated. Call authenticate() first.")

        all_holdings: List[pd.DataFrame] = []

        exchanges_to_query = (
            [account_id] if account_id else list(self.exchanges.keys())
        )

        for exchange_id in exchanges_to_query:
            if exchange_id not in self.exchanges:
                logger.warning(f"Exchange {exchange_id} not authenticated")
                continue

            try:
                holdings = self._fetch_exchange_holdings(exchange_id)
                if holdings is not None and len(holdings) > 0:
                    all_holdings.append(holdings)
            except Exception as e:
                logger.error(f"Failed to fetch holdings from {exchange_id}: {e}")

        if not all_holdings:
            return self._create_empty_holdings_df()

        result = pd.concat(all_holdings, ignore_index=True)
        return result

    def _fetch_exchange_holdings(self, exchange_id: str) -> Optional[pd.DataFrame]:
        """Fetch holdings from a single exchange."""
        exchange = self.exchanges[exchange_id]

        # Check cache
        cache_key = f"holdings_{exchange_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Apply rate limiting
        if exchange_id in self._rate_limiters:
            self._rate_limiters[exchange_id].wait()

        # Fetch balance
        try:
            balance = exchange.fetch_balance()
        except ccxt.RateLimitExceeded as e:
            raise RateLimitError(f"Rate limit exceeded: {e}", retry_after=60)
        except ccxt.NetworkError as e:
            raise DataFetchError(f"Network error: {e}", exchange_id)

        # Filter non-zero balances
        holdings = []
        for symbol, data in balance.get('total', {}).items():
            if data and float(data) > 0:
                # Skip very small dust amounts
                if float(data) < 0.00001:
                    continue

                # Get current price
                price = self._get_price(exchange, symbol)

                holdings.append({
                    'symbol': symbol,
                    'name': self._get_asset_name(symbol),
                    'quantity': float(data),
                    'current_price': price or 0,
                    'market_value': float(data) * (price or 0),
                    'cost_basis': None,  # Not available from most exchanges
                    'currency': 'USD',
                    'account_id': exchange_id,
                })

        if not holdings:
            return None

        df = pd.DataFrame(holdings)
        self.cache.set(cache_key, df)
        return df

    def _get_price(self, exchange: Any, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        # Stablecoins are always ~$1
        if symbol in self.STABLECOINS:
            return 1.0

        try:
            # Try common quote currencies
            for quote in ['USDT', 'USD', 'BUSD', 'USDC']:
                pair = f"{symbol}/{quote}"
                if pair in exchange.markets:
                    ticker = exchange.fetch_ticker(pair)
                    return ticker.get('last') or ticker.get('close')

            return None
        except Exception as e:
            logger.debug(f"Could not fetch price for {symbol}: {e}")
            return None

    def _get_asset_name(self, symbol: str) -> str:
        """Map symbol to full asset name."""
        return self.CRYPTO_NAMES.get(symbol, symbol)

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch transaction history from all authenticated exchanges.

        Args:
            account_id: If provided, only fetch from this exchange
            since_date: Start date for transactions
            until_date: End date for transactions

        Returns:
            DataFrame with columns: date, symbol, name, transaction_type,
            quantity, price, amount, currency, fees, source_id, exchange
        """
        if not self.is_authenticated:
            raise DataFetchError("Not authenticated. Call authenticate() first.")

        all_transactions: List[pd.DataFrame] = []

        exchanges_to_query = (
            [account_id] if account_id else list(self.exchanges.keys())
        )

        # Convert dates to timestamps
        since_ts = int(since_date.timestamp() * 1000) if since_date else None

        for exchange_id in exchanges_to_query:
            if exchange_id not in self.exchanges:
                logger.warning(f"Exchange {exchange_id} not authenticated")
                continue

            try:
                txns = self._fetch_exchange_transactions(exchange_id, since_ts)
                if txns is not None and len(txns) > 0:
                    # Filter by until_date if provided
                    if until_date:
                        txns = txns[txns['date'] <= until_date]
                    all_transactions.append(txns)
            except Exception as e:
                logger.error(f"Failed to fetch transactions from {exchange_id}: {e}")

        if not all_transactions:
            return self._create_empty_transactions_df()

        result = pd.concat(all_transactions, ignore_index=True)
        return result.sort_values('date', ascending=False)

    def _fetch_exchange_transactions(
        self,
        exchange_id: str,
        since_ts: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """Fetch transactions from a single exchange."""
        exchange = self.exchanges[exchange_id]
        transactions = []

        # Apply rate limiting
        if exchange_id in self._rate_limiters:
            self._rate_limiters[exchange_id].wait()

        try:
            # Fetch trades
            if exchange.has.get('fetchMyTrades'):
                trades = exchange.fetch_my_trades(since=since_ts, limit=1000)
                for trade in trades:
                    symbol = trade['symbol'].split('/')[0] if trade.get('symbol') else 'UNKNOWN'
                    transactions.append({
                        'date': datetime.fromtimestamp(trade['timestamp'] / 1000),
                        'symbol': symbol,
                        'name': self._get_asset_name(symbol),
                        'transaction_type': 'Buy' if trade['side'] == 'buy' else 'Sell',
                        'quantity': trade.get('amount', 0),
                        'price': trade.get('price', 0),
                        'amount': trade.get('cost', 0),
                        'currency': 'USD',
                        'fees': trade.get('fee', {}).get('cost', 0) if trade.get('fee') else 0,
                        'source_id': f"{exchange_id}_{trade.get('id', '')}",
                        'account_id': exchange_id,
                    })

            # Fetch deposits
            if exchange.has.get('fetchDeposits'):
                try:
                    deposits = exchange.fetch_deposits(since=since_ts, limit=500)
                    for deposit in deposits:
                        if deposit.get('status') == 'ok':
                            symbol = deposit.get('currency', 'UNKNOWN')
                            transactions.append({
                                'date': datetime.fromtimestamp(deposit['timestamp'] / 1000) if deposit.get('timestamp') else datetime.now(),
                                'symbol': symbol,
                                'name': self._get_asset_name(symbol),
                                'transaction_type': 'Deposit',
                                'quantity': deposit.get('amount', 0),
                                'price': 0,
                                'amount': deposit.get('amount', 0),
                                'currency': 'USD',
                                'fees': deposit.get('fee', {}).get('cost', 0) if deposit.get('fee') else 0,
                                'source_id': f"{exchange_id}_dep_{deposit.get('id', '')}",
                                'account_id': exchange_id,
                            })
                except Exception as e:
                    logger.debug(f"Could not fetch deposits from {exchange_id}: {e}")

            # Fetch withdrawals
            if exchange.has.get('fetchWithdrawals'):
                try:
                    withdrawals = exchange.fetch_withdrawals(since=since_ts, limit=500)
                    for withdrawal in withdrawals:
                        if withdrawal.get('status') == 'ok':
                            symbol = withdrawal.get('currency', 'UNKNOWN')
                            transactions.append({
                                'date': datetime.fromtimestamp(withdrawal['timestamp'] / 1000) if withdrawal.get('timestamp') else datetime.now(),
                                'symbol': symbol,
                                'name': self._get_asset_name(symbol),
                                'transaction_type': 'Withdrawal',
                                'quantity': withdrawal.get('amount', 0),
                                'price': 0,
                                'amount': withdrawal.get('amount', 0),
                                'currency': 'USD',
                                'fees': withdrawal.get('fee', {}).get('cost', 0) if withdrawal.get('fee') else 0,
                                'source_id': f"{exchange_id}_wth_{withdrawal.get('id', '')}",
                                'account_id': exchange_id,
                            })
                except Exception as e:
                    logger.debug(f"Could not fetch withdrawals from {exchange_id}: {e}")

        except ccxt.RateLimitExceeded as e:
            raise RateLimitError(f"Rate limit exceeded: {e}", retry_after=60)
        except ccxt.NetworkError as e:
            raise DataFetchError(f"Network error: {e}", exchange_id)

        if not transactions:
            return None

        return pd.DataFrame(transactions)

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get information about connected exchanges."""
        if not self.is_authenticated:
            return None

        accounts = {}
        for exchange_id, exchange in self.exchanges.items():
            accounts[exchange_id] = {
                'account_id': exchange_id,
                'account_type': 'Crypto Exchange',
                'base_currency': 'USD',
                'status': 'connected',
                'exchange_name': exchange.name,
                'has_trading': exchange.has.get('createOrder', False),
                'has_deposits': exchange.has.get('fetchDeposits', False),
                'has_withdrawals': exchange.has.get('fetchWithdrawals', False),
            }

        return accounts

    def health_check(self) -> Tuple[bool, str]:
        """Check if all exchanges are accessible."""
        if not self.exchanges:
            return False, "No exchanges connected"

        issues = []
        for exchange_id, exchange in self.exchanges.items():
            try:
                exchange.fetch_time()
            except Exception as e:
                issues.append(f"{exchange_id}: {e}")

        if issues:
            return False, f"Issues: {'; '.join(issues)}"

        return True, f"All {len(self.exchanges)} exchange(s) healthy"

    def disconnect(self) -> bool:
        """Disconnect from all exchanges."""
        self.exchanges.clear()
        self._rate_limiters.clear()
        self.cache.clear()
        self._authenticated = False
        logger.info("Disconnected from all exchanges")
        return True

    def get_supported_exchanges(self) -> List[str]:
        """Get list of supported exchange IDs."""
        if not CCXT_AVAILABLE:
            return []
        return list(ccxt.exchanges)
