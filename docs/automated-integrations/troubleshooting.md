# Troubleshooting Guide

Common issues and solutions for data integrations in WealthOS.

## Quick Diagnostics

### Health Check

Run the built-in health check:

```python
from src.data_manager.import_orchestrator import ImportOrchestrator

orchestrator = ImportOrchestrator(config)
orchestrator.initialize_connectors()

# Check all connectors
health = orchestrator.health_check_all()
for source, (healthy, message) in health.items():
    print(f"{source}: {'✅' if healthy else '❌'} {message}")
```

## Authentication Issues

### "Invalid API key"

**Symptoms**: Authentication fails immediately with "invalid key" error.

**Solutions**:

1. Verify the key is copied correctly (no extra spaces)
2. Check key hasn't expired or been revoked
3. Ensure the key has required permissions
4. Regenerate the API key

### "Signature verification failed"

**Symptoms**: Request fails with HMAC/signature error.

**Solutions**:

1. Verify the Secret Key is correct
2. Check your system clock is synchronized
3. Ensure you're using the correct API version

```bash
# Sync system clock (Linux/Mac)
sudo ntpdate time.apple.com
```

### "OAuth token expired"

**Symptoms**: Previously working connection fails.

**Solutions**:

1. Re-authenticate through the OAuth flow
2. Check if refresh token is still valid
3. Verify OAuth credentials haven't changed

### "IP address not whitelisted"

**Symptoms**: Authentication fails with IP restriction error.

**Solutions**:

1. Find your current IP: `curl ifconfig.me`
2. Add IP to whitelist in exchange settings
3. Consider removing IP restrictions if using dynamic IP

## Connection Issues

### "Connection refused"

**Symptoms**: Can't reach the API endpoint.

**Solutions**:

1. Check internet connectivity
2. Verify firewall isn't blocking the connection
3. Try with a VPN (some exchanges block certain regions)
4. Check API status page for outages

### "SSL certificate verification failed"

**Symptoms**: HTTPS connection fails with certificate error.

**Solutions**:

1. Update your system's CA certificates
2. Check system date/time is correct
3. Verify you're connecting to the correct URL

```bash
# Update CA certificates (Ubuntu)
sudo update-ca-certificates

# Update CA certificates (Mac)
brew install ca-certificates
```

### "Timeout waiting for response"

**Symptoms**: Requests hang and eventually timeout.

**Solutions**:

1. Increase timeout values in connector config
2. Check API endpoint status
3. Try a different network
4. Reduce request frequency

## Rate Limiting

### "Too many requests" / HTTP 429

**Symptoms**: Requests fail with rate limit error.

**Solutions**:

1. Wait before retrying (respect `retry_after` header)
2. Reduce sync frequency
3. Use built-in rate limiter:

```python
from src.data_manager.connectors.utils import RateLimiter

limiter = RateLimiter(calls_per_minute=30)
limiter.wait()  # Call before each request
```

### "Weight limit exceeded"

**Symptoms**: Binance-specific error about request weight.

**Solutions**:

1. Reduce number of concurrent requests
2. Use batch endpoints instead of individual calls
3. Wait 1 minute for weight to reset

## Data Issues

### "Missing transactions"

**Symptoms**: Some transactions don't appear after sync.

**Solutions**:

1. Check date range parameters
2. Verify transaction status (pending vs. completed)
3. Check for pagination issues
4. Manually verify transactions exist in source

### "Duplicate transactions"

**Symptoms**: Same transaction appears multiple times.

**Solutions**:

1. Check `source_id` is being set correctly
2. Verify deduplication logic in importer
3. Clear and re-sync affected date range

### "Incorrect balances"

**Symptoms**: Holdings don't match exchange balances.

**Solutions**:

1. Force refresh (clear cache and re-sync)
2. Check for pending deposits/withdrawals
3. Verify API returns all account types
4. Check currency conversion rates

### "Symbol mapping errors"

**Symptoms**: Assets show with wrong names or missing.

**Solutions**:

1. Update asset taxonomy configuration
2. Add missing symbol mappings
3. Check for exchange-specific symbol formats

## Plugin Issues

### "Plugin failed to load"

**Symptoms**: Plugin not appearing in available plugins.

**Solutions**:

1. Verify manifest.yaml exists and is valid YAML
2. Check connector.py has no syntax errors
3. Ensure plugin class extends BankIntegrationPlugin
4. Check for missing dependencies

```python
# Validate plugin syntax
from src.plugins.manager import PluginManager

manager = PluginManager()
valid, issues = manager.validate_plugin("my_plugin")
print(issues)
```

### "Plugin blocked by security check"

**Symptoms**: Plugin fails security validation.

**Solutions**:

1. Remove any `eval()`, `exec()`, or `subprocess` calls
2. Remove imports of blocked modules
3. Review plugin code for security issues

### "PluginMetadata not found"

**Symptoms**: Plugin loads but can't be used.

**Solutions**:

1. Ensure connector class has `plugin_metadata` attribute
2. Verify it's a `PluginMetadata` instance
3. Check all required fields are set

## Database Issues

### "ImportJob table doesn't exist"

**Symptoms**: Database error on sync.

**Solutions**:

1. Run database migrations:

```bash
alembic upgrade head
```

1. Or create tables manually:

```python
from src.database.base import engine
from src.database.models import Base

Base.metadata.create_all(engine)
```

### "Credential decryption failed"

**Symptoms**: Can't read stored credentials.

**Solutions**:

1. Verify encryption key hasn't changed
2. Re-enter credentials through UI
3. Check database file permissions

## Logging

Enable detailed logging for debugging:

```python
import logging

# Enable debug logging for connectors
logging.getLogger('src.data_manager.connectors').setLevel(logging.DEBUG)

# Enable debug logging for plugins
logging.getLogger('src.plugins').setLevel(logging.DEBUG)
```

Or set via environment:

```bash
export LOG_LEVEL=DEBUG
```

## Getting Help

If you're still stuck:

1. **Check logs**: `logs/web_app.log` and console output
2. **Search issues**: Look for similar issues on GitHub
3. **Gather information**:
   - Exact error message
   - Steps to reproduce
   - Config (with secrets removed)
   - Relevant log output
4. **Report issue**: Create a GitHub issue with above info

## Common Error Reference

| Error Code | Meaning | Common Solution |
|------------|---------|-----------------|
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Verify API credentials |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Verify endpoint/symbol |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | API issue, retry later |
| 502 | Bad Gateway | Network/proxy issue |
| 503 | Unavailable | API maintenance |
