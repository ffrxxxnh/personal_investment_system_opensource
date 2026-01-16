"""
Lifetime Performance Service

Calculates realized vs unrealized gains, asset performance metrics,
and sub-class breakdowns for the Lifetime Performance report.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd

from src.data_manager.manager import DataManager
from src.data_manager.historical_manager import HistoricalDataManager
from src.portfolio_lib.taxonomy_manager import TaxonomyManager

logger = logging.getLogger(__name__)


class LifetimePerformanceService:
    """
    Service to calculate lifetime investment performance metrics.

    Provides:
    - Realized vs unrealized gains breakdown
    - Sub-class level performance analysis
    - Individual asset performance scorecard
    - Weighted portfolio XIRR
    """

    def __init__(self, config_path: str = 'config/settings.yaml'):
        """
        Initialize the service with data managers.

        Args:
            config_path: Path to settings.yaml configuration
        """
        self.config_path = config_path
        self.data_manager = DataManager(config_path=config_path)
        self.historical_manager = HistoricalDataManager(config_path=config_path)
        self.taxonomy_manager = TaxonomyManager()

        # Color palette for charts
        self.colors = {
            'realized': '#22c55e',    # Green
            'unrealized': '#3b82f6',  # Blue
        }

        # Sub-class color palette
        self.subclass_colors = [
            '#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
            '#8b5cf6', '#06b6d4', '#ec4899', '#64748b'
        ]

    def get_performance_data(self) -> Dict[str, Any]:
        """
        Calculate and return all lifetime performance data.

        Returns:
            Dict containing:
            - gains_summary: Total realized/unrealized gains and XIRR
            - gains_breakdown: Chart data for realized vs unrealized
            - subclass_breakdown: Gains by sub-class
            - asset_performance: Individual asset performance table
            - active_assets: Count of currently held assets
            - total_assets: Total assets ever held
            - currency: Base currency
            - generated_at: Timestamp
        """
        try:
            # Get current holdings and transactions
            holdings = self.data_manager.get_holdings(latest_only=True)
            transactions = self.data_manager.get_transactions()

            if holdings is None or holdings.empty:
                logger.warning("No holdings data available for lifetime performance")
                return self._empty_response()

            # Calculate performance for each asset
            asset_performance = self._calculate_asset_performance(holdings, transactions)

            # Aggregate gains
            total_realized = sum(a.get('realized_gain', 0) for a in asset_performance)
            total_unrealized = sum(a.get('unrealized_gain', 0) for a in asset_performance)
            total_gains = total_realized + total_unrealized

            # Calculate weighted XIRR (simplified - use return %)
            weighted_xirr = self._calculate_weighted_xirr(asset_performance)

            # Build sub-class breakdown
            subclass_breakdown = self._build_subclass_breakdown(asset_performance)

            # Count active vs total assets
            active_count = sum(1 for a in asset_performance if a.get('status') == 'ACTIVE')
            total_count = len(asset_performance)

            # Build response
            return {
                'status': 'success',
                'gains_summary': {
                    'total_realized': total_realized,
                    'total_unrealized': total_unrealized,
                    'total_gains': total_gains,
                    'weighted_xirr': weighted_xirr,
                },
                'gains_breakdown': [
                    {'name': 'Realized Gains', 'value': total_realized, 'color': self.colors['realized']},
                    {'name': 'Unrealized Gains', 'value': total_unrealized, 'color': self.colors['unrealized']},
                ],
                'subclass_breakdown': subclass_breakdown,
                'asset_performance': asset_performance,
                'active_assets': active_count,
                'total_assets': total_count,
                'currency': 'CNY',
                'generated_at': datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error calculating lifetime performance: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'gains_summary': None,
                'gains_breakdown': [],
                'subclass_breakdown': [],
                'asset_performance': [],
                'generated_at': datetime.now().isoformat(),
            }

    def _calculate_asset_performance(
        self,
        holdings: pd.DataFrame,
        transactions: Optional[pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        Calculate performance metrics for each asset.

        Args:
            holdings: Current holdings DataFrame
            transactions: Historical transactions DataFrame

        Returns:
            List of asset performance dictionaries
        """
        performance_list = []

        # Group by Asset_Name for unique assets
        asset_col = 'Asset_Name' if 'Asset_Name' in holdings.columns else 'Asset_ID'

        for asset_name in holdings[asset_col].unique():
            asset_holdings = holdings[holdings[asset_col] == asset_name]

            # Get latest holding record
            latest = asset_holdings.iloc[-1] if len(asset_holdings) > 0 else None
            if latest is None:
                continue

            # Extract values
            current_value = float(latest.get('Market_Value_CNY', 0) or latest.get('Market_Value', 0) or 0)
            cost_basis = float(latest.get('Cost_Basis_CNY', 0) or latest.get('Cost_Basis', 0) or 0)

            # Calculate unrealized gain
            unrealized_gain = current_value - cost_basis if cost_basis > 0 else 0

            # Get asset classification
            asset_class = latest.get('Asset_Class', '股票')
            sub_class = latest.get('Sub_Class', 'Unknown')

            # Determine status (ACTIVE if current value > 0)
            status = 'ACTIVE' if current_value > 0 else 'CLOSED'

            # Calculate realized gains from transactions
            realized_gain = 0
            first_txn_date = None

            if transactions is not None and not transactions.empty:
                # Filter transactions for this asset
                txn_col = 'Asset_Name' if 'Asset_Name' in transactions.columns else 'Asset_ID'
                if txn_col in transactions.columns:
                    asset_txns = transactions[transactions[txn_col] == asset_name]
                    if len(asset_txns) > 0:
                        # Get first transaction date for holding period
                        first_txn_date = asset_txns.index.min() if isinstance(asset_txns.index, pd.DatetimeIndex) else None
                        if first_txn_date is None and 'Date' in asset_txns.columns:
                            first_txn_date = pd.to_datetime(asset_txns['Date']).min()

                        # Calculate realized gains from sells
                        sell_txns = asset_txns[asset_txns.get('Transaction_Type', pd.Series()) == 'Sell']
                        if len(sell_txns) > 0:
                            # Simplified: use Realized_Gain column if available
                            if 'Realized_Gain' in sell_txns.columns:
                                realized_gain = float(sell_txns['Realized_Gain'].sum())
                            elif 'Gain_Loss' in sell_txns.columns:
                                realized_gain = float(sell_txns['Gain_Loss'].sum())

            # Calculate holding period
            holding_period = self._calculate_holding_period(first_txn_date)

            # Calculate return percentage
            total_invested = cost_basis if cost_basis > 0 else (current_value - unrealized_gain)
            total_gain = unrealized_gain + realized_gain
            return_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0

            performance_list.append({
                'name': str(asset_name),
                'asset_class': str(asset_class),
                'sub_class': str(sub_class),
                'holding_period': holding_period,
                'status': status,
                'total_invested': round(total_invested, 2),
                'current_value': round(current_value, 2),
                'cost_basis': round(cost_basis, 2),
                'realized_gain': round(realized_gain, 2),
                'unrealized_gain': round(unrealized_gain, 2),
                'total_gain': round(total_gain, 2),
                'return_pct': round(return_pct, 2),
            })

        # Sort by total gain descending
        performance_list.sort(key=lambda x: x.get('total_gain', 0), reverse=True)

        return performance_list

    def _calculate_holding_period(self, first_date: Optional[pd.Timestamp]) -> str:
        """
        Calculate human-readable holding period from first transaction date.

        Args:
            first_date: First transaction date

        Returns:
            String like "4y 7m" or "1m 22d"
        """
        if first_date is None:
            return "Unknown"

        try:
            first_date = pd.to_datetime(first_date)
            now = pd.Timestamp.now()

            delta = relativedelta(now, first_date)

            if delta.years > 0:
                return f"{delta.years}y {delta.months}m"
            elif delta.months > 0:
                return f"{delta.months}m {delta.days}d"
            else:
                return f"{delta.days}d"
        except Exception:
            return "Unknown"

    def _calculate_weighted_xirr(self, asset_performance: List[Dict]) -> float:
        """
        Calculate weighted average return across all assets.

        Args:
            asset_performance: List of asset performance dicts

        Returns:
            Weighted XIRR as percentage
        """
        total_invested = sum(a.get('total_invested', 0) for a in asset_performance)

        if total_invested <= 0:
            return 0.0

        # Weight each asset's return by its investment size
        weighted_return = sum(
            a.get('return_pct', 0) * a.get('total_invested', 0)
            for a in asset_performance
        )

        return round(weighted_return / total_invested, 2)

    def _build_subclass_breakdown(self, asset_performance: List[Dict]) -> List[Dict[str, Any]]:
        """
        Aggregate gains by sub-class for chart breakdown.

        Args:
            asset_performance: List of asset performance dicts

        Returns:
            List of sub-class breakdown dicts
        """
        # Group by sub_class
        subclass_gains = {}

        for asset in asset_performance:
            sub_class = asset.get('sub_class', 'Unknown')
            if sub_class not in subclass_gains:
                subclass_gains[sub_class] = {'realized': 0, 'unrealized': 0}

            subclass_gains[sub_class]['realized'] += asset.get('realized_gain', 0)
            subclass_gains[sub_class]['unrealized'] += asset.get('unrealized_gain', 0)

        # Convert to list and sort by total gains
        breakdown = []
        for idx, (sub_class, gains) in enumerate(sorted(
            subclass_gains.items(),
            key=lambda x: x[1]['realized'] + x[1]['unrealized'],
            reverse=True
        )):
            breakdown.append({
                'name': sub_class,
                'realized': round(gains['realized'], 2),
                'unrealized': round(gains['unrealized'], 2),
                'total': round(gains['realized'] + gains['unrealized'], 2),
                'color': self.subclass_colors[idx % len(self.subclass_colors)],
            })

        return breakdown

    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response structure when no data available."""
        return {
            'status': 'success',
            'gains_summary': {
                'total_realized': 0,
                'total_unrealized': 0,
                'total_gains': 0,
                'weighted_xirr': 0,
            },
            'gains_breakdown': [
                {'name': 'Realized Gains', 'value': 0, 'color': self.colors['realized']},
                {'name': 'Unrealized Gains', 'value': 0, 'color': self.colors['unrealized']},
            ],
            'subclass_breakdown': [],
            'asset_performance': [],
            'active_assets': 0,
            'total_assets': 0,
            'currency': 'CNY',
            'generated_at': datetime.now().isoformat(),
        }
