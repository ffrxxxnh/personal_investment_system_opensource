# Binance Setup Guide

This guide explains how to connect your Binance account to WealthOS.

## Prerequisites

- A Binance account
- Completed [KYC verification](https://www.binance.com/en/my/settings/profile)
- 2FA enabled on your account

## Step 1: Create API Key

1. Log in to [Binance](https://www.binance.com)
2. Go to **Account** → **API Management**
   - Or navigate directly: [API Management](https://www.binance.com/en/my/settings/api-management)
3. Click **Create API**
4. Choose **System generated** (recommended)
5. Enter a label like "WealthOS Read-Only"
6. Complete 2FA verification
7. Save your **API Key** and **Secret Key**

> ⚠️ **Important**: This is the only time you'll see the Secret Key. Store it securely!

## Step 2: Configure API Permissions

For security, configure these **minimal permissions**:

| Permission | Required | Notes |
|------------|----------|-------|
| Enable Reading | ✅ Yes | Required for balance/history |
| Enable Spot & Margin Trading | ❌ No | Not needed |
| Enable Futures | ❌ No | Not needed |
| Enable Withdrawals | ❌ No | **Never enable this!** |
| Enable Internal Transfer | ❌ No | Not needed |

## Step 3: Set IP Whitelist (Recommended)

For enhanced security:

1. In API settings, click **Edit restrictions**
2. Select **Restrict access to trusted IPs only**
3. Add your home/server IP addresses
4. Save changes

## Step 4: Connect to WealthOS

1. Open WealthOS → **Integrations** → **Crypto Exchanges**
2. Click **Connect** on Binance
3. Enter your API Key and Secret Key
4. Click **Connect Exchange**

## Verification

After connecting:

- Click **Sync** to test the connection
- Verify your balances appear correctly
- Check that transaction history is imported

## Troubleshooting

### "Invalid API-key, IP, or permissions"

- Verify API key is copied correctly (no extra spaces)
- Check if IP whitelist is blocking your connection
- Ensure "Enable Reading" permission is enabled

### "Signature verification failed"

- Double-check the Secret Key
- Regenerate the API key if needed

### Rate Limit Errors

- Binance has rate limits (1200/min for most endpoints)
- Wait a few minutes and try again

## Security Best Practices

1. **Never enable withdrawal permissions**
2. Use IP whitelist when possible
3. Rotate API keys periodically (every 3-6 months)
4. Don't share API keys
5. Delete unused API keys

## Need Help?

- [Binance API Documentation](https://binance-docs.github.io/apidocs/spot/en/)
- [Binance Support](https://www.binance.com/en/support)
