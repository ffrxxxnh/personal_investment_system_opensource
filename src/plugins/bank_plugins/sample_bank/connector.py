# Sample Bank Plugin Connector
# src/plugins/bank_plugins/sample_bank/connector.py

"""
Sample Bank Plugin - A template for building custom bank integrations.

This module demonstrates the complete structure of a bank integration plugin,
including authentication, data fetching, and error handling.

To create your own plugin:
1. Copy this entire sample_bank directory
2. Rename to your bank name (e.g., icbc, chase, wells_fargo)
3. Update manifest.yaml with your bank's details
4. Implement the actual API calls in this connector

Note: This sample returns demo data. Replace with real API calls for your bank.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import random

import pandas as pd

from src.plugins.base import BankIntegrationPlugin, PluginMetadata, PluginCapability

logger = logging.getLogger(__name__)


class SampleBankPlugin(BankIntegrationPlugin):
    """
    Sample bank integration plugin.

    This is a complete, working example of a bank plugin. It demonstrates:
    - Plugin metadata definition
    - Configuration validation
    - Authentication flow
    - Holdings retrieval
    - Transaction history fetching
    - Error handling patterns

    Attributes:
        plugin_metadata: Plugin information and capabilities
        _session_token: Simulated session token after authentication
        _accounts: List of connected accounts
    """

    # Define plugin metadata (required)
    plugin_metadata = PluginMetadata(
        id="sample_bank",
        name="Sample Bank Integration",
        version="1.0.0",
        author="WealthOS Community",
        description="A template bank integration plugin for demonstration",
        capabilities=[
            PluginCapability.HOLDINGS,
            PluginCapability.TRANSACTIONS,
            PluginCapability.BALANCES,
        ],
        supported_countries=["US", "CN"],
        authentication_type="credentials",
        required_fields=["username", "password"],
        optional_fields=["account_number", "branch_code"],
        documentation_url="https://github.com/your-org/wealthos-plugins/wiki/sample-bank",
    )

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Sample Bank plugin.

        Args:
            config: Configuration dictionary containing:
                - username: Bank login username (required)
                - password: Bank login password (required)
                - account_number: Specific account to sync (optional)
                - branch_code: Branch identifier (optional)
        """
        super().__init__(config)

        # Plugin-specific state
        self._session_token: Optional[str] = None
        self._accounts: List[Dict[str, Any]] = []

        logger.info(f"Initialized {self.plugin_metadata.name} v{self.plugin_metadata.version}")

    def authenticate(self) -> Tuple[bool, str]:
        """
        Authenticate with the bank.

        In a real implementation, this would:
        1. Make an API call to the bank's login endpoint
        2. Handle MFA/2FA if required
        3. Store session tokens securely
        4. Return connection status

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate required configuration
        valid, missing = self.validate_config()
        if not valid:
            return False, f"Missing required fields: {missing}"

        username = self.config.get('username')
        password = self.config.get('password')

        logger.info(f"Authenticating user: {username[:3]}***")

        # === DEMO IMPLEMENTATION ===
        # Replace this with actual bank API calls
        try:
            # Simulate authentication delay
            import time
            time.sleep(0.5)

            # Simulate successful login
            self._session_token = f"demo_token_{random.randint(1000, 9999)}"
            self._authenticated = True

            # Simulate fetching account list
            self._accounts = [
                {
                    "id": "ACC001",
                    "name": "Checking Account",
                    "type": "checking",
                    "currency": "USD",
                },
                {
                    "id": "ACC002",
                    "name": "Savings Account",
                    "type": "savings",
                    "currency": "USD",
                },
            ]

            logger.info(f"Successfully authenticated. Found {len(self._accounts)} accounts.")
            return True, f"Connected to {len(self._accounts)} account(s)"

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False, f"Authentication failed: {str(e)}"

    def get_holdings(self, account_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch current account balances/holdings.

        In a real implementation, this would call the bank's API to get
        current account balances, deposits, and other holdings.

        Args:
            account_id: Optional specific account to query

        Returns:
            DataFrame with holdings data or None
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Call authenticate() first.")
            return None

        logger.info(f"Fetching holdings for account: {account_id or 'all'}")

        # === DEMO IMPLEMENTATION ===
        # Replace with actual bank API calls

        # Filter accounts if specific one requested
        accounts = self._accounts
        if account_id:
            accounts = [a for a in self._accounts if a['id'] == account_id]

        holdings = []
        for account in accounts:
            # Generate demo balance
            balance = round(random.uniform(5000, 50000), 2)

            holdings.append({
                'symbol': account['type'].upper(),
                'name': account['name'],
                'quantity': 1,
                'current_price': balance,
                'market_value': balance,
                'cost_basis': balance,  # For cash, cost = value
                'currency': account['currency'],
                'account_id': account['id'],
            })

        if not holdings:
            return self._create_empty_holdings_df()

        return pd.DataFrame(holdings)

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        since_date: Optional[datetime] = None,
        until_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch transaction history.

        In a real implementation, this would call the bank's API to get
        transaction history within the specified date range.

        Args:
            account_id: Optional specific account to query
            since_date: Start date for transaction range
            until_date: End date for transaction range

        Returns:
            DataFrame with transaction data or None
        """
        if not self.is_authenticated:
            logger.warning("Not authenticated. Call authenticate() first.")
            return None

        # Default date range
        if until_date is None:
            until_date = datetime.now()
        if since_date is None:
            since_date = until_date - timedelta(days=90)

        logger.info(f"Fetching transactions from {since_date.date()} to {until_date.date()}")

        # === DEMO IMPLEMENTATION ===
        # Replace with actual bank API calls

        # Filter accounts
        accounts = self._accounts
        if account_id:
            accounts = [a for a in self._accounts if a['id'] == account_id]

        transactions = []

        # Generate sample transactions
        transaction_types = [
            ('Deposit', 1000, 5000),
            ('Withdrawal', -500, -2000),
            ('Interest', 10, 100),
            ('Transfer', -1000, 1000),
            ('Fee', -5, -50),
        ]

        for account in accounts:
            # Generate 5-15 random transactions per account
            num_transactions = random.randint(5, 15)

            for i in range(num_transactions):
                # Random date in range
                days_ago = random.randint(0, (until_date - since_date).days)
                txn_date = until_date - timedelta(days=days_ago)

                # Random transaction type
                txn_type, min_amt, max_amt = random.choice(transaction_types)
                amount = round(random.uniform(min_amt, max_amt), 2)

                transactions.append({
                    'date': txn_date,
                    'symbol': 'CASH',
                    'name': f'{txn_type} - {account["name"]}',
                    'transaction_type': txn_type,
                    'quantity': 1,
                    'price': abs(amount),
                    'amount': amount,
                    'currency': account['currency'],
                    'fees': 0,
                    'source_id': f"sample_{account['id']}_{i}_{txn_date.strftime('%Y%m%d')}",
                    'account_id': account['id'],
                })

        if not transactions:
            return self._create_empty_transactions_df()

        df = pd.DataFrame(transactions)
        return df.sort_values('date', ascending=False)

    def get_balances(self, account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get account balances (implements PluginCapability.BALANCES).

        Args:
            account_id: Optional specific account to query

        Returns:
            Dictionary with balance information
        """
        if not self.is_authenticated:
            return None

        # Filter accounts
        accounts = self._accounts
        if account_id:
            accounts = [a for a in self._accounts if a['id'] == account_id]

        balances = {}
        for account in accounts:
            balances[account['id']] = {
                'account_name': account['name'],
                'account_type': account['type'],
                'currency': account['currency'],
                'available_balance': round(random.uniform(5000, 50000), 2),
                'current_balance': round(random.uniform(5000, 50000), 2),
                'pending_transactions': round(random.uniform(0, 500), 2),
            }

        return balances

    def health_check(self) -> Tuple[bool, str]:
        """
        Check if the bank connection is healthy.

        Returns:
            Tuple of (healthy, message)
        """
        if not self._session_token:
            return False, "Not authenticated"

        # In a real implementation, make a lightweight API call
        # to verify the session is still valid

        return True, "Connection healthy"

    def disconnect(self) -> bool:
        """
        Logout from the bank and clean up.

        Returns:
            True if successful
        """
        logger.info("Disconnecting from Sample Bank")

        # In a real implementation, call the bank's logout endpoint

        self._session_token = None
        self._accounts = []
        self._authenticated = False

        return True


# =============================================================================
# PLUGIN DEVELOPMENT TIPS
# =============================================================================
#
# 1. AUTHENTICATION
#    - Always validate required config fields first
#    - Handle MFA/2FA flows gracefully
#    - Store tokens securely (never in plain text)
#    - Implement automatic token refresh
#
# 2. ERROR HANDLING
#    - Raise AuthenticationError for login failures
#    - Raise RateLimitError when limits are hit (include retry_after)
#    - Raise DataFetchError for API failures
#    - Log errors with enough context for debugging
#
# 3. DATA FORMAT
#    - Return DataFrames with standard column names
#    - Use the base class helpers: _create_empty_holdings_df(), etc.
#    - Always include source_id for deduplication
#    - Normalize currency codes (USD, CNY, EUR)
#
# 4. RATE LIMITING
#    - Respect the bank's rate limits
#    - Use the RateLimiter utility class
#    - Implement exponential backoff for retries
#
# 5. SECURITY
#    - Never log passwords or full account numbers
#    - Mask sensitive data in logs (e.g., "****1234")
#    - Don't store credentials in plugin code
#    - Validate all input data
#
# =============================================================================
