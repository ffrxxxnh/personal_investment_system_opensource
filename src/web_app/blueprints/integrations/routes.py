# Integrations Routes
# src/web_app/blueprints/integrations/routes.py

"""
Web routes for data integrations management.

Provides endpoints for:
- Viewing data source status
- Configuring connectors
- Triggering syncs
- Viewing import history
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
)
from flask_babel import _

from . import integrations_bp

logger = logging.getLogger(__name__)


# =============================================================================
# DASHBOARD
# =============================================================================

@integrations_bp.route('/')
@integrations_bp.route('/dashboard')
def dashboard():
    """
    Data sources dashboard.

    Shows all configured data sources, their status, and last sync times.
    """
    # Get integration status from config
    sources = _get_data_sources_status()

    return render_template(
        'integrations/dashboard.html',
        title=_('Data Integrations'),
        sources=sources,
        last_updated=datetime.now()
    )


@integrations_bp.route('/status')
def status_json():
    """API endpoint for data source status."""
    sources = _get_data_sources_status()
    return jsonify({
        'sources': sources,
        'timestamp': datetime.now().isoformat()
    })


# =============================================================================
# CRYPTO EXCHANGES
# =============================================================================

@integrations_bp.route('/crypto')
def crypto_exchanges():
    """Cryptocurrency exchanges management page."""
    # Get configured exchanges
    exchanges = _get_crypto_exchanges_config()

    return render_template(
        'integrations/crypto.html',
        title=_('Crypto Exchanges'),
        exchanges=exchanges
    )


@integrations_bp.route('/crypto/connect/<exchange_id>', methods=['GET', 'POST'])
def connect_crypto_exchange(exchange_id: str):
    """Connect to a crypto exchange."""
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        api_secret = request.form.get('api_secret')
        password = request.form.get('password')  # For OKX, KuCoin

        if not api_key or not api_secret:
            flash(_('API key and secret are required'), 'error')
            return redirect(url_for('integrations.crypto_exchanges'))

        # Save configuration (encrypted)
        success = _save_exchange_config(exchange_id, {
            'api_key': api_key,
            'api_secret': api_secret,
            'password': password,
            'enabled': True
        })

        if success:
            flash(_('Exchange connected successfully'), 'success')
        else:
            flash(_('Failed to connect exchange'), 'error')

        return redirect(url_for('integrations.crypto_exchanges'))

    # GET - show connection form
    exchange_info = _get_exchange_info(exchange_id)
    return render_template(
        'integrations/connect_exchange.html',
        title=_('Connect %(exchange)s', exchange=exchange_id.capitalize()),
        exchange_id=exchange_id,
        exchange_info=exchange_info
    )


@integrations_bp.route('/crypto/sync/<exchange_id>', methods=['POST'])
def sync_crypto_exchange(exchange_id: str):
    """Trigger sync for a crypto exchange."""
    try:
        result = _trigger_sync('crypto', exchange_id)
        if result['success']:
            flash(_('Sync completed: %(records)d records imported',
                   records=result.get('records_imported', 0)), 'success')
        else:
            flash(_('Sync failed: %(error)s', error=result.get('error', 'Unknown')), 'error')
    except Exception as e:
        logger.error(f"Error syncing {exchange_id}: {e}")
        flash(_('Sync failed: %(error)s', error=str(e)), 'error')

    return redirect(url_for('integrations.crypto_exchanges'))


@integrations_bp.route('/crypto/disconnect/<exchange_id>', methods=['POST'])
def disconnect_crypto_exchange(exchange_id: str):
    """Disconnect a crypto exchange."""
    success = _remove_exchange_config(exchange_id)
    if success:
        flash(_('Exchange disconnected'), 'success')
    else:
        flash(_('Failed to disconnect exchange'), 'error')
    return redirect(url_for('integrations.crypto_exchanges'))


# =============================================================================
# BROKERS
# =============================================================================

@integrations_bp.route('/brokers')
def brokers():
    """Broker connections management page."""
    brokers_config = _get_brokers_config()

    return render_template(
        'integrations/brokers.html',
        title=_('Broker Connections'),
        brokers=brokers_config
    )


@integrations_bp.route('/brokers/connect/<broker_id>', methods=['GET', 'POST'])
def connect_broker(broker_id: str):
    """Connect to a broker."""
    if broker_id == 'schwab':
        # Schwab uses OAuth - redirect to OAuth flow
        return redirect(url_for('integrations.schwab_oauth_start'))
    elif broker_id == 'ibkr':
        # IBKR needs gateway URL and optional JWT
        if request.method == 'POST':
            gateway_url = request.form.get('gateway_url', 'https://localhost:5000')
            jwt_token = request.form.get('jwt_token')

            success = _save_broker_config(broker_id, {
                'gateway_url': gateway_url,
                'jwt_token': jwt_token,
                'enabled': True
            })

            if success:
                flash(_('Broker connected successfully'), 'success')
            else:
                flash(_('Failed to connect broker'), 'error')

            return redirect(url_for('integrations.brokers'))

        return render_template(
            'integrations/connect_ibkr.html',
            title=_('Connect Interactive Brokers')
        )

    flash(_('Unknown broker'), 'error')
    return redirect(url_for('integrations.brokers'))


@integrations_bp.route('/brokers/sync/<broker_id>', methods=['POST'])
def sync_broker(broker_id: str):
    """Trigger sync for a broker."""
    try:
        result = _trigger_sync('broker', broker_id)
        if result['success']:
            flash(_('Sync completed: %(records)d records imported',
                   records=result.get('records_imported', 0)), 'success')
        else:
            flash(_('Sync failed: %(error)s', error=result.get('error', 'Unknown')), 'error')
    except Exception as e:
        logger.error(f"Error syncing {broker_id}: {e}")
        flash(_('Sync failed: %(error)s', error=str(e)), 'error')

    return redirect(url_for('integrations.brokers'))


# =============================================================================
# SCHWAB OAUTH
# =============================================================================

@integrations_bp.route('/auth/schwab/start')
def schwab_oauth_start():
    """Start Schwab OAuth flow."""
    # TODO: Implement OAuth flow
    flash(_('Schwab OAuth not yet implemented'), 'warning')
    return redirect(url_for('integrations.brokers'))


@integrations_bp.route('/auth/schwab/callback')
def schwab_oauth_callback():
    """Handle Schwab OAuth callback."""
    # TODO: Implement OAuth callback
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(_('OAuth error: %(error)s', error=error), 'error')
        return redirect(url_for('integrations.brokers'))

    if code:
        # Exchange code for token
        # TODO: Implement token exchange
        flash(_('Schwab connected successfully'), 'success')

    return redirect(url_for('integrations.brokers'))


# =============================================================================
# IMPORT HISTORY
# =============================================================================

@integrations_bp.route('/history')
def import_history():
    """View import history."""
    # Get recent import jobs from database
    jobs = _get_import_history(limit=50)

    return render_template(
        'integrations/history.html',
        title=_('Import History'),
        jobs=jobs
    )


@integrations_bp.route('/history/<job_id>')
def import_job_detail(job_id: str):
    """View details of a specific import job."""
    job = _get_import_job(job_id)
    if not job:
        flash(_('Import job not found'), 'error')
        return redirect(url_for('integrations.import_history'))

    return render_template(
        'integrations/job_detail.html',
        title=_('Import Job Details'),
        job=job
    )


# =============================================================================
# SYNC ALL
# =============================================================================

@integrations_bp.route('/sync-all', methods=['POST'])
def sync_all():
    """Trigger sync for all enabled sources."""
    try:
        results = _trigger_full_sync()
        total_imported = sum(r.get('records_imported', 0) for r in results)
        flash(_('Full sync completed: %(records)d total records imported',
               records=total_imported), 'success')
    except Exception as e:
        logger.error(f"Error in full sync: {e}")
        flash(_('Sync failed: %(error)s', error=str(e)), 'error')

    return redirect(url_for('integrations.dashboard'))


# =============================================================================
# SETTINGS
# =============================================================================

@integrations_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Integration settings page."""
    if request.method == 'POST':
        # Update settings
        sync_frequency = request.form.get('sync_frequency', 'daily')
        auto_sync = request.form.get('auto_sync') == 'on'

        # Save settings
        # TODO: Implement settings save

        flash(_('Settings saved'), 'success')
        return redirect(url_for('integrations.settings'))

    # Get current settings
    current_settings = _get_integration_settings()

    return render_template(
        'integrations/settings.html',
        title=_('Integration Settings'),
        settings=current_settings
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_data_sources_status() -> List[Dict[str, Any]]:
    """Get status of all configured data sources."""
    sources = []

    # Crypto exchanges
    crypto_config = _get_crypto_exchanges_config()
    for exchange in crypto_config:
        if exchange.get('enabled'):
            sources.append({
                'type': 'crypto',
                'id': exchange['id'],
                'name': exchange['name'],
                'status': exchange.get('status', 'unknown'),
                'last_sync': exchange.get('last_sync'),
                'records': exchange.get('record_count', 0)
            })

    # Brokers
    brokers = _get_brokers_config()
    for broker in brokers:
        if broker.get('enabled'):
            sources.append({
                'type': 'broker',
                'id': broker['id'],
                'name': broker['name'],
                'status': broker.get('status', 'unknown'),
                'last_sync': broker.get('last_sync'),
                'records': broker.get('record_count', 0)
            })

    return sources


def _get_crypto_exchanges_config() -> List[Dict[str, Any]]:
    """Get configured crypto exchanges."""
    # In a real implementation, this would read from database/config
    # For now, return supported exchanges
    return [
        {'id': 'binance', 'name': 'Binance', 'enabled': False, 'status': 'not_configured'},
        {'id': 'coinbase', 'name': 'Coinbase', 'enabled': False, 'status': 'not_configured'},
        {'id': 'kraken', 'name': 'Kraken', 'enabled': False, 'status': 'not_configured'},
        {'id': 'okx', 'name': 'OKX', 'enabled': False, 'status': 'not_configured'},
        {'id': 'kucoin', 'name': 'KuCoin', 'enabled': False, 'status': 'not_configured'},
    ]


def _get_brokers_config() -> List[Dict[str, Any]]:
    """Get configured brokers."""
    return [
        {'id': 'schwab', 'name': 'Charles Schwab', 'enabled': False, 'status': 'not_configured', 'auth_type': 'oauth'},
        {'id': 'ibkr', 'name': 'Interactive Brokers', 'enabled': False, 'status': 'not_configured', 'auth_type': 'gateway'},
    ]


def _get_exchange_info(exchange_id: str) -> Dict[str, Any]:
    """Get info about a specific exchange."""
    exchange_info = {
        'binance': {
            'name': 'Binance',
            'docs_url': 'https://www.binance.com/en/my/settings/api-management',
            'requires_password': False,
            'notes': 'Create a read-only API key in your Binance account settings.'
        },
        'coinbase': {
            'name': 'Coinbase',
            'docs_url': 'https://www.coinbase.com/settings/api',
            'requires_password': False,
            'notes': 'Use API Key authentication (not OAuth).'
        },
        'okx': {
            'name': 'OKX',
            'docs_url': 'https://www.okx.com/account/my-api',
            'requires_password': True,
            'notes': 'OKX requires an API passphrase in addition to key/secret.'
        },
        'kucoin': {
            'name': 'KuCoin',
            'docs_url': 'https://www.kucoin.com/account/api',
            'requires_password': True,
            'notes': 'KuCoin requires an API passphrase.'
        },
    }
    return exchange_info.get(exchange_id, {'name': exchange_id.capitalize()})


def _save_exchange_config(exchange_id: str, config: Dict[str, Any]) -> bool:
    """Save exchange configuration to database."""
    # TODO: Implement actual save with encryption
    logger.info(f"Saving config for exchange {exchange_id}")
    return True


def _remove_exchange_config(exchange_id: str) -> bool:
    """Remove exchange configuration."""
    # TODO: Implement actual remove
    logger.info(f"Removing config for exchange {exchange_id}")
    return True


def _save_broker_config(broker_id: str, config: Dict[str, Any]) -> bool:
    """Save broker configuration."""
    # TODO: Implement actual save
    logger.info(f"Saving config for broker {broker_id}")
    return True


def _trigger_sync(source_type: str, source_id: str) -> Dict[str, Any]:
    """Trigger sync for a specific source."""
    # TODO: Implement actual sync trigger
    logger.info(f"Triggering sync for {source_type}/{source_id}")
    return {'success': True, 'records_imported': 0}


def _trigger_full_sync() -> List[Dict[str, Any]]:
    """Trigger sync for all enabled sources."""
    # TODO: Implement actual full sync
    logger.info("Triggering full sync")
    return []


def _get_import_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent import history from database."""
    # TODO: Query from database
    return []


def _get_import_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get details of a specific import job."""
    # TODO: Query from database
    return None


def _get_integration_settings() -> Dict[str, Any]:
    """Get integration settings."""
    return {
        'sync_frequency': 'daily',
        'auto_sync': False,
        'retry_failed': True,
        'cache_ttl': 300
    }
