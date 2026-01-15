import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
    test.beforeEach(async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').fill('admin');
        await page.getByRole('button', { name: 'Sign In' }).click();
        await expect(page).toHaveURL(/\/$/, { timeout: 15000 });
    });

    test('should display sidebar navigation', async ({ page }) => {
        // Check sidebar elements
        await expect(page.getByRole('navigation')).toBeVisible();

        // Check for main nav items (allow partial matches)
        await expect(page.locator('nav').getByText(/Dashboard/i).first()).toBeVisible();
        await expect(page.locator('nav').getByText(/Portfolio/i).first()).toBeVisible();
    });

    test('should navigate to Dashboard', async ({ page }) => {
        await page.locator('nav').getByText(/Dashboard/i).first().click();
        await expect(page).toHaveURL(/\/$/);
    });

    test('should navigate to Portfolio page', async ({ page }) => {
        await page.locator('nav').getByText(/Portfolio/i).first().click();
        await expect(page).toHaveURL(/\/portfolio\/?$/);
        await expect(page.getByText(/Portfolio|Holdings|Assets/i).first()).toBeVisible();
    });

    test('should navigate to Wealth page', async ({ page }) => {
        await page.locator('nav').getByText(/Wealth/i).first().click();
        await expect(page).toHaveURL(/\/wealth\/?$/);
    });

    test('should navigate to Settings page', async ({ page }) => {
        await page.locator('nav').getByText(/Settings/i).first().click();
        await expect(page).toHaveURL(/\/settings\/?$/);
        await expect(page.getByText(/Settings|Preferences/i).first()).toBeVisible();
    });

    test('should navigate to report pages', async ({ page }) => {
        // Navigate to Compass
        await page.goto('/compass');
        await expect(page.getByText(/Compass|Market|Analysis/i).first()).toBeVisible({ timeout: 10000 });

        // Navigate to Cash Flow
        await page.goto('/cashflow');
        await expect(page.getByText(/Cash Flow|Income|Expenses/i).first()).toBeVisible({ timeout: 10000 });

        // Navigate to Simulation
        await page.goto('/simulation');
        await expect(page.getByText(/Simulation|Monte Carlo|Goal/i).first()).toBeVisible({ timeout: 10000 });

        // Navigate to Performance
        await page.goto('/performance');
        await expect(page.getByText(/Performance|Lifetime|Returns/i).first()).toBeVisible({ timeout: 10000 });
    });
});
