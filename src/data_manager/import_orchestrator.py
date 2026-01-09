# Data Import Orchestrator
# src/data_manager/import_orchestrator.py

"""
Unified data import orchestrator for multi-source data integration.

Coordinates data imports from all configured sources (APIs, CSV, plugins),
handles deduplication, validation, and database syncing.

Usage:
    orchestrator = ImportOrchestrator(config)
    results = orchestrator.run_full_sync()
    print(results.summary())
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.database.models import ImportJob
from .connectors.base_connector import (
    BaseConnector,
    ConnectorError,
    AuthenticationError,
    RateLimitError,
    DataFetchError,
)
from .connectors.utils import generate_source_id

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of a single source import."""
    source_type: str
    source_id: str
    success: bool
    records_fetched: int = 0
    records_imported: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    holdings_df: Optional[pd.DataFrame] = None
    transactions_df: Optional[pd.DataFrame] = None


@dataclass
class SyncResults:
    """Results from a full sync operation."""
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    source_results: List[ImportResult] = field(default_factory=list)
    total_records_imported: int = 0
    total_records_updated: int = 0
    total_records_skipped: int = 0
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate human-readable summary."""
        duration = (self.completed_at - self.started_at).total_seconds() if self.completed_at else 0

        lines = [
            f"Sync Job: {self.job_id}",
            f"Duration: {duration:.1f}s",
            f"Sources: {len(self.source_results)}",
            f"Imported: {self.total_records_imported}",
            f"Updated: {self.total_records_updated}",
            f"Skipped: {self.total_records_skipped}",
        ]

        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                lines.append(f"  - {error}")

        return "\n".join(lines)

    @property
    def success(self) -> bool:
        """Check if sync was successful (at least one source succeeded)."""
        return any(r.success for r in self.source_results)


class ImportOrchestrator:
    """
    Orchestrates data imports from multiple sources.

    Handles:
    - Connector initialization and authentication
    - Parallel or sequential data fetching
    - Data deduplication
    - Database syncing
    - Import job tracking

    Attributes:
        config: Configuration dictionary
        connectors: Dictionary of initialized connectors
        db_session: Database session (optional)
    """

    def __init__(
        self,
        config: Dict[str, Any],
        db_session: Optional[Any] = None
    ):
        """
        Initialize import orchestrator.

        Args:
            config: Configuration from data_sources.yaml
            db_session: SQLAlchemy session for database operations
        """
        self.config = config
        self.db_session = db_session
        self.connectors: Dict[str, BaseConnector] = {}
        self._initialized = False

    def initialize_connectors(self) -> Dict[str, Tuple[bool, str]]:
        """
        Initialize and authenticate all configured connectors.

        Returns:
            Dictionary of {source_id: (success, message)}
        """
        results = {}

        # Initialize crypto connectors
        if self.config.get('crypto', {}).get('enabled'):
            result = self._init_ccxt_connector()
            if result:
                results['ccxt'] = result

        # Initialize broker connectors
        brokers = self.config.get('brokers', {})
        for broker_id, broker_config in brokers.items():
            if broker_config.get('enabled'):
                result = self._init_broker_connector(broker_id, broker_config)
                if result:
                    results[broker_id] = result

        # Initialize market data connectors
        market_config = self.config.get('market_data', {})
        for provider in market_config.get('providers', {}).keys():
            provider_config = market_config['providers'][provider]
            if provider_config.get('enabled'):
                result = self._init_market_connector(provider, provider_config)
                if result:
                    results[provider] = result

        self._initialized = True
        return results

    def _init_ccxt_connector(self) -> Optional[Tuple[bool, str]]:
        """Initialize CCXT crypto connector."""
        try:
            from .connectors.ccxt_connector import CCXTConnector

            crypto_config = self.config.get('crypto', {})
            exchanges = crypto_config.get('exchanges', {})

            # Filter enabled exchanges
            enabled_exchanges = {
                ex_id: ex_config
                for ex_id, ex_config in exchanges.items()
                if ex_config.get('enabled')
            }

            if not enabled_exchanges:
                return None

            connector = CCXTConnector({'exchanges': enabled_exchanges})
            success, message = connector.authenticate()

            if success:
                self.connectors['ccxt'] = connector

            return success, message

        except ImportError as e:
            return False, f"CCXT not available: {e}"
        except Exception as e:
            return False, f"Failed to initialize CCXT: {e}"

    def _init_broker_connector(
        self,
        broker_id: str,
        broker_config: Dict[str, Any]
    ) -> Optional[Tuple[bool, str]]:
        """Initialize a broker connector."""
        try:
            if broker_id == 'schwab':
                from .connectors.schwab_connector import SchwabConnector
                connector = SchwabConnector(broker_config)
            elif broker_id == 'ibkr':
                from .connectors.ibkr_connector import IBKRConnector
                connector = IBKRConnector(broker_config)
            else:
                return False, f"Unknown broker: {broker_id}"

            success, message = connector.authenticate()
            if success:
                self.connectors[broker_id] = connector

            return success, message

        except Exception as e:
            return False, f"Failed to initialize {broker_id}: {e}"

    def _init_market_connector(
        self,
        provider: str,
        provider_config: Dict[str, Any]
    ) -> Optional[Tuple[bool, str]]:
        """Initialize a market data connector."""
        try:
            if provider == 'tiingo':
                from .connectors.tiingo_connector import TiingoConnector
                connector = TiingoConnector(provider_config)
                success, message = connector.authenticate()
                if success:
                    self.connectors['tiingo'] = connector
                return success, message

            # Yahoo Finance doesn't need authentication
            elif provider == 'yahoo_finance':
                return True, "Yahoo Finance ready (no auth needed)"

            return None

        except Exception as e:
            return False, f"Failed to initialize {provider}: {e}"

    def run_full_sync(
        self,
        source_filter: Optional[List[str]] = None,
        since_date: Optional[datetime] = None
    ) -> SyncResults:
        """
        Run a full data sync from all enabled sources.

        Args:
            source_filter: Optional list of source IDs to sync
            since_date: Only fetch transactions since this date

        Returns:
            SyncResults with details of the operation
        """
        job_id = str(uuid.uuid4())[:8]
        results = SyncResults(
            job_id=job_id,
            started_at=datetime.now()
        )

        logger.info(f"Starting sync job {job_id}")

        # Initialize connectors if not done
        if not self._initialized:
            init_results = self.initialize_connectors()
            for source_id, (success, message) in init_results.items():
                if not success:
                    results.errors.append(f"{source_id}: {message}")

        # Filter sources if specified
        sources_to_sync = self.connectors
        if source_filter:
            sources_to_sync = {
                k: v for k, v in self.connectors.items()
                if k in source_filter
            }

        # Sync each source
        for source_id, connector in sources_to_sync.items():
            try:
                result = self._sync_source(source_id, connector, since_date)
                results.source_results.append(result)
                results.total_records_imported += result.records_imported
                results.total_records_updated += result.records_updated
                results.total_records_skipped += result.records_skipped

                if not result.success and result.error_message:
                    results.errors.append(f"{source_id}: {result.error_message}")

            except Exception as e:
                logger.error(f"Error syncing {source_id}: {e}")
                results.errors.append(f"{source_id}: {e}")
                results.source_results.append(ImportResult(
                    source_type=connector.metadata.connector_type.value,
                    source_id=source_id,
                    success=False,
                    error_message=str(e)
                ))

        results.completed_at = datetime.now()
        logger.info(f"Sync job {job_id} completed: {results.summary()}")

        # Save import job to database if session available
        if self.db_session:
            self._save_import_job(results)

        return results

    def _sync_source(
        self,
        source_id: str,
        connector: BaseConnector,
        since_date: Optional[datetime] = None
    ) -> ImportResult:
        """Sync data from a single source."""
        start_time = datetime.now()
        result = ImportResult(
            source_type=connector.metadata.connector_type.value,
            source_id=source_id,
            success=False
        )

        try:
            # Fetch holdings
            holdings = connector.get_holdings()
            if holdings is not None and len(holdings) > 0:
                result.holdings_df = holdings
                result.records_fetched += len(holdings)
                logger.info(f"Fetched {len(holdings)} holdings from {source_id}")

            # Fetch transactions
            transactions = connector.get_transactions(since_date=since_date)
            if transactions is not None and len(transactions) > 0:
                result.transactions_df = transactions
                result.records_fetched += len(transactions)
                logger.info(f"Fetched {len(transactions)} transactions from {source_id}")

            # Process and deduplicate
            if result.holdings_df is not None:
                processed = self._process_holdings(result.holdings_df, source_id)
                result.records_imported += processed['imported']
                result.records_updated += processed['updated']
                result.records_skipped += processed['skipped']

            if result.transactions_df is not None:
                processed = self._process_transactions(result.transactions_df, source_id)
                result.records_imported += processed['imported']
                result.records_updated += processed['updated']
                result.records_skipped += processed['skipped']

            result.success = True

        except AuthenticationError as e:
            result.error_message = f"Authentication failed: {e}"
        except RateLimitError as e:
            result.error_message = f"Rate limit exceeded: {e}"
        except DataFetchError as e:
            result.error_message = f"Data fetch failed: {e}"
        except Exception as e:
            result.error_message = f"Unexpected error: {e}"
            logger.exception(f"Error syncing {source_id}")

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    def _process_holdings(
        self,
        holdings: pd.DataFrame,
        source_id: str
    ) -> Dict[str, int]:
        """Process and store holdings data."""
        # For now, just count records
        # TODO: Implement actual database sync with deduplication
        return {
            'imported': len(holdings),
            'updated': 0,
            'skipped': 0
        }

    def _process_transactions(
        self,
        transactions: pd.DataFrame,
        source_id: str
    ) -> Dict[str, int]:
        """Process and store transaction data."""
        # Ensure source_id column exists
        if 'source_id' not in transactions.columns:
            transactions['source_id'] = transactions.apply(
                lambda row: generate_source_id(
                    source_id,
                    date=row.get('date'),
                    symbol=row.get('symbol'),
                    amount=row.get('amount')
                ),
                axis=1
            )

        # TODO: Implement actual database sync with deduplication
        return {
            'imported': len(transactions),
            'updated': 0,
            'skipped': 0
        }

    def _save_import_job(self, results: SyncResults) -> None:
        """Save import job record to database."""
        try:
            status = 'success' if results.success else 'failed'
            if results.errors and results.success:
                status = 'partial'

            job = ImportJob(
                job_id=results.job_id,
                source_type='multi',
                source_id='orchestrator',
                started_at=results.started_at,
                completed_at=results.completed_at,
                duration_seconds=(results.completed_at - results.started_at).total_seconds() if results.completed_at else 0,
                status=status,
                records_fetched=sum(r.records_fetched for r in results.source_results),
                records_imported=results.total_records_imported,
                records_updated=results.total_records_updated,
                records_skipped=results.total_records_skipped,
                error_message='\n'.join(results.errors) if results.errors else None,
                triggered_by='manual'
            )

            self.db_session.add(job)
            self.db_session.commit()
            logger.info(f"Saved import job {results.job_id} to database")

        except Exception as e:
            logger.error(f"Failed to save import job: {e}")

    def get_connector(self, source_id: str) -> Optional[BaseConnector]:
        """Get a specific connector by ID."""
        return self.connectors.get(source_id)

    def health_check_all(self) -> Dict[str, Tuple[bool, str]]:
        """Run health check on all connectors."""
        results = {}
        for source_id, connector in self.connectors.items():
            try:
                healthy, message = connector.health_check()
                results[source_id] = (healthy, message)
            except Exception as e:
                results[source_id] = (False, str(e))
        return results

    def disconnect_all(self) -> None:
        """Disconnect from all sources."""
        for source_id, connector in self.connectors.items():
            try:
                connector.disconnect()
                logger.info(f"Disconnected from {source_id}")
            except Exception as e:
                logger.error(f"Error disconnecting from {source_id}: {e}")

        self.connectors.clear()
        self._initialized = False
