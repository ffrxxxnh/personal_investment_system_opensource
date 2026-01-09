# Sample Bank Plugin
# src/plugins/bank_plugins/sample_bank/__init__.py

"""
Sample Bank Integration Plugin.

This is a template plugin demonstrating how to build custom bank integrations
for the WealthOS Personal Investment System.

Usage:
    from src.plugins.bank_plugins.sample_bank import SampleBankPlugin

    plugin = SampleBankPlugin({
        'username': 'your_username',
        'password': 'your_password'
    })
    success, message = plugin.authenticate()
    holdings = plugin.get_holdings()
"""

from .connector import SampleBankPlugin

__all__ = ['SampleBankPlugin']
