import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Personal Investment System SPA
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
    testDir: './e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    timeout: 30000,

    use: {
        baseURL: 'http://localhost:3000',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],

    /* Run local dev servers before tests */
    webServer: [
        {
            command: 'python main.py run-web --port 5001',
            url: 'http://localhost:5001/api/health',
            reuseExistingServer: !process.env.CI,
            timeout: 60000,
        },
        {
            command: 'npm run dev',
            url: 'http://localhost:3000',
            reuseExistingServer: !process.env.CI,
            timeout: 60000,
        },
    ],
});
