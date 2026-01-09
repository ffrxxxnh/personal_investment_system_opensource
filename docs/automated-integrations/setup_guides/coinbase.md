# Coinbase Setup Guide

This guide explains how to connect your Coinbase account to WealthOS.

## Prerequisites

- A Coinbase account
- Completed identity verification
- 2FA enabled (recommended)

## Step 1: Create API Key

1. Log in to [Coinbase](https://www.coinbase.com)
2. Go to **Settings** → **API**
   - Or navigate directly: [API Settings](https://www.coinbase.com/settings/api)
3. Click **+ New API Key**
4. Select the account(s) to grant access
5. Set permissions (see below)
6. Complete 2FA verification
7. Save your **API Key** and **API Secret**

> ⚠️ **Important**: The API Secret is only shown once. Store it securely!

## Step 2: Configure Permissions

Grant these **minimal permissions**:

| Permission | Required | Notes |
|------------|----------|-------|
| wallet:accounts:read | ✅ Yes | View account balances |
| wallet:transactions:read | ✅ Yes | View transaction history |
| wallet:user:read | Optional | View profile info |
| wallet:buys:read | Optional | View purchase history |
| wallet:sells:read | Optional | View sell history |

**Never grant these permissions:**

- `wallet:buys:create` ❌
- `wallet:sells:create` ❌
- `wallet:withdrawals:create` ❌
- `wallet:addresses:create` ❌

## Step 3: Connect to WealthOS

1. Open WealthOS → **Integrations** → **Crypto Exchanges**
2. Click **Connect** on Coinbase
3. Enter your API Key and API Secret
4. Click **Connect Exchange**

## Coinbase vs Coinbase Pro

This guide is for **Coinbase** (retail). For **Coinbase Pro** / **Coinbase Advanced Trade**:

- API keys are created differently
- Different endpoints are used
- Contact support for Pro setup

> Note: Coinbase Pro was rebranded to "Advanced Trade" and integrated into the main Coinbase app.

## Data Available

WealthOS can sync from Coinbase:

| Data Type | Supported |
|-----------|-----------|
| Wallet Balances | ✅ |
| Buy Orders | ✅ |
| Sell Orders | ✅ |
| Crypto Transfers | ✅ |
| Staking Rewards | ✅ |
| Earn Rewards | ✅ |

## Troubleshooting

### "Invalid API credentials"

- Verify API key and secret are copied correctly
- Check that the key hasn't been revoked
- Ensure 2FA was completed during key creation

### "Permission denied"

- Verify required permissions are granted
- Regenerate the API key with correct permissions

### "Rate limit exceeded"

- Coinbase limits to 10,000 requests/hour
- Wait a few minutes and retry
- WealthOS caches responses to minimize API calls

### Missing transactions

- Some transaction types may take 24-48 hours to appear
- Check if the transaction is still pending
- Verify the correct accounts are selected

## Security Best Practices

1. **Use minimal permissions** - Only grant read access
2. **Rotate API keys** - Regenerate every 3-6 months
3. **Monitor API activity** - Check for unauthorized access
4. **Enable 2FA** - Required for API key creation
5. **Delete unused keys** - Remove old or unused API keys

## Multiple Accounts

If you have multiple Coinbase accounts:

1. Create separate API keys for each account
2. Configure each in WealthOS as a separate exchange
3. Holdings will be aggregated in reports

## Need Help?

- [Coinbase API Documentation](https://docs.cloud.coinbase.com/)
- [Coinbase Support](https://help.coinbase.com/)
- [API Key Management](https://www.coinbase.com/settings/api)
