# Issue: Report Generation Performance (Web App)

## Summary

Reports take **minutes** to load in the web application when testing as a new user with demo data. Expected load time is **2-3 seconds**.

## Status

- **Priority**: High
- **Phase**: Logged for next sprint
- **Assigned**: Unassigned

## Details

| Field | Value |
|-------|-------|
| **Reported** | 2026-01-09 |
| **Environment** | Local development (Flask dev server) |
| **Data** | Demo data (fresh database) |
| **Affected Pages** | All report pages |

## Symptoms

1. User clicks on report page (Portfolio, Compass, etc.)
2. Backend processes for **multiple minutes**
3. Browser shows loading state
4. Eventually, report renders correctly

## Expected Behavior

With demo data (~10 holdings, ~50 transactions), reports should generate in **2-3 seconds max**.

## Potential Root Causes

- [ ] **Database queries**: N+1 query patterns or missing indexes
- [ ] **Analysis pipeline**: Redundant calculations or unoptimized loops
- [ ] **Monte Carlo simulation**: Too many iterations for initial load
- [ ] **FX rate fetching**: Blocking API calls without caching
- [ ] **No caching**: Report results not cached between requests
- [ ] **Full historical analysis**: Processing all time periods vs. lazy loading

## Debug Steps

1. **Profile Flask request**:

   ```bash
   python -m cProfile -o report.prof main.py run-web
   # Then load a report page
   ```

2. **Add timing logs**:

   ```python
   # In report_service.py or engine.py
   import time
   start = time.time()
   # ... processing
   print(f"Step X took {time.time() - start:.2f}s")
   ```

3. **Check database queries**:

   ```python
   # In settings.yaml or app config
   SQLALCHEMY_ECHO: true
   ```

4. **Review analysis engine**:
   - Check `FinancialAnalysisEngine.run_complete_analysis()`
   - Look for expensive operations

## Mitigation Ideas

1. **Implement caching**: Cache report results in database/Redis
2. **Background processing**: Generate reports async, poll for completion
3. **Lazy loading**: Show partial results, load details on demand
4. **Optimize queries**: Add database indexes, batch queries
5. **Reduce Monte Carlo iterations**: Lower default for web vs CLI

## Files to Investigate

- `src/unified_analysis/engine.py`
- `src/web_app/services/report_service.py`
- `src/data_manager/manager.py`
- `src/goal_planning/monte_carlo.py`

## Related Issues

- None

---

*Last updated: 2026-01-09*
