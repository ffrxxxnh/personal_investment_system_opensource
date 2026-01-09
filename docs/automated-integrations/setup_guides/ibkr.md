# Interactive Brokers (IBKR) Setup Guide

This guide explains how to connect your Interactive Brokers account to WealthOS using the Client Portal API.

## Prerequisites

- An active IBKR account
- [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php) installed (for local access)
- Or access to IBKR Client Portal API (for cloud access)

## Option A: Local IB Gateway (Recommended)

### Step 1: Download IB Gateway

1. Visit [IB Gateway Download](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
2. Download the appropriate version for your OS
3. Install and launch IB Gateway

### Step 2: Configure IB Gateway

1. Launch IB Gateway
2. Log in with your IBKR credentials
3. Select **IB API** as the connection type
4. Note the gateway port (default: 5000)

### Step 3: Enable API Access

In IB Gateway settings:

1. Go to **Configure** → **Settings** → **API**
2. Enable **Enable ActiveX and Socket Clients**
3. Set **Socket port** to 5000
4. Add **127.0.0.1** to trusted IPs
5. Click **Apply**

### Step 4: Connect to WealthOS

1. Open WealthOS → **Integrations** → **Brokers**
2. Click **Connect** on Interactive Brokers
3. Enter Gateway URL: `https://localhost:5000`
4. Leave JWT Token empty for local access
5. Click **Connect**

## Option B: Cloud Access (Advanced)

For cloud-based access without running IB Gateway locally:

### Step 1: Get JWT Token

1. Log in to [Client Portal](https://www.interactivebrokers.com/portal/)
2. Navigate to **Settings** → **API Access**
3. Generate a JWT token
4. Copy the token securely

### Step 2: Connect to WealthOS

1. Open WealthOS → **Integrations** → **Brokers**
2. Click **Connect** on Interactive Brokers
3. Enter Gateway URL: `https://api.ibkr.com`
4. Paste your JWT Token
5. Click **Connect**

## Data Available

Once connected, WealthOS can sync:

| Data Type | Supported |
|-----------|-----------|
| Account Balances | ✅ |
| Stock Holdings | ✅ |
| Option Positions | ✅ |
| Futures Positions | ✅ |
| Trade History | ✅ |
| Dividends | ✅ |
| Corporate Actions | ✅ |

## Troubleshooting

### "Gateway not authenticated"

- Ensure IB Gateway is running and logged in
- Check that the gateway port is correct
- Verify your IBKR session hasn't timed out

### "Connection refused"

- Verify IB Gateway is running
- Check firewall settings allow port 5000
- Ensure SSL verification is disabled for localhost

### "Invalid JWT token"

- Regenerate the JWT token
- Check token hasn't expired
- Verify the gateway URL is correct

### Session Timeout

- IB Gateway sessions timeout after inactivity
- Consider using [IBC](https://github.com/IbcAlpha/IBC) for automated restarts
- Or implement session keep-alive

## Security Notes

1. **Use read-only access** when possible
2. IB Gateway runs locally - no credentials sent to WealthOS servers
3. JWT tokens should be rotated regularly
4. Keep IB Gateway updated to latest version

## Advanced: Headless Mode

For running on a server without GUI:

```bash
# Install IB Gateway in headless mode
./ibgateway -install

# Configure auto-start
./ibgateway --mode=paper --port=5000
```

Consider using [IBC (IB Controller)](https://github.com/IbcAlpha/IBC) for automated login and maintenance.

## Need Help?

- [IBKR Client Portal API Docs](https://interactivebrokers.github.io/cpwebapi/)
- [IBKR API Support](https://www.interactivebrokers.com/en/index.php?f=1560)
- [IBC Project](https://github.com/IbcAlpha/IBC)
