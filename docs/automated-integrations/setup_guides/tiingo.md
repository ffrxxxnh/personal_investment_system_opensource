# Tiingo Setup Guide

This guide explains how to set up Tiingo for market data in WealthOS.

## What is Tiingo?

Tiingo provides high-quality financial data including:

- Real-time and historical stock prices
- ETF prices
- Cryptocurrency prices
- Fundamental data
- News feeds

## Step 1: Create a Tiingo Account

1. Visit [Tiingo](https://www.tiingo.com/)
2. Click **Sign Up**
3. Enter your email and password
4. Verify your email address

## Step 2: Get Your API Token

1. Log in to [Tiingo](https://www.tiingo.com/)
2. Go to [API Token page](https://api.tiingo.com/account/api/token)
3. Copy your API token

> Your token looks like: `a1b2c3d4e5f6g7h8i9j0...`

## Step 3: Configure WealthOS

### Option A: Environment Variable (Recommended)

Add to your environment:

```bash
export TIINGO_API_KEY="your_api_token_here"
```

Or add to `.env` file:

```
TIINGO_API_KEY=your_api_token_here
```

### Option B: Web UI

1. Open WealthOS → **Integrations** → **Settings**
2. Find **Market Data Providers**
3. Select **Tiingo**
4. Paste your API token
5. Click **Save**

## API Limits

### Free Tier

| Feature | Limit |
|---------|-------|
| Requests/hour | 500 |
| Requests/day | 50,000 |
| Historical data | 5 years |
| Real-time data | End of day only |

### Paid Tier

For real-time data and higher limits, consider [Tiingo Pro](https://api.tiingo.com/pricing).

## Data Available

| Data Type | Endpoint | Free Tier |
|-----------|----------|-----------|
| Stock Prices | `/iex/*` | ✅ End-of-day |
| Historical Prices | `/tiingo/daily/*` | ✅ 5 years |
| Crypto Prices | `/tiingo/crypto/*` | ✅ |
| Fundamentals | `/tiingo/fundamentals/*` | ✅ |
| News | `/tiingo/news` | ✅ |

## Verify Setup

Test your API key:

```bash
curl -H "Authorization: Token YOUR_API_KEY" \
  "https://api.tiingo.com/api/test"
```

Expected response:

```json
{"message":"You successfully sent a request"}
```

## Troubleshooting

### "Invalid token"

- Verify the token is copied correctly
- Check for extra spaces or newlines
- Regenerate the token if needed

### "Rate limit exceeded"

- Free tier has limits; wait before retrying
- Consider caching responses
- Upgrade to paid tier for higher limits

### "Symbol not found"

- Verify the ticker symbol is correct
- Some OTC stocks may not be available
- Crypto symbols use format: `btcusd`, `ethusd`

## Best Practices

1. **Cache responses** - WealthOS caches by default for 5 minutes
2. **Batch requests** - Request multiple symbols at once when possible
3. **Use end-of-day data** - Sufficient for portfolio tracking
4. **Monitor usage** - Check your usage at [Tiingo Dashboard](https://api.tiingo.com/account/usage)

## Integration with WealthOS

Once configured, Tiingo provides:

- **Real-time portfolio valuation** using current prices
- **Historical performance charts** using price history
- **Asset search** for adding new positions
- **Benchmark comparisons** using index prices

## Need Help?

- [Tiingo API Documentation](https://api.tiingo.com/documentation/general/overview)
- [Tiingo Support](https://www.tiingo.com/about/contact)
- [Tiingo Status](https://status.tiingo.com/)
