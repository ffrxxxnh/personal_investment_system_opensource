import { test, expect } from '@playwright/test';

test.describe('Reports', () => {
    test.beforeEach(async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').fill('admin');
        await page.getByRole('button', { name: 'Sign In' }).click();
        await expect(page).toHaveURL(/\/$/, { timeout: 15000 });
    });

    test('Compass report should load', async ({ page }) => {
        await page.goto('/compass');
        await expect(page).toHaveURL(/\/compass\/?$/);

        // Wait for content to load
        await page.waitForTimeout(2000);

        // Check for report content (use first() for nested mains)
        const hasContent = await page.locator('main').first().textContent();
        expect(hasContent).toBeTruthy();
    });

    test('Cash Flow report should load', async ({ page }) => {
        await page.goto('/cashflow');
        await expect(page).toHaveURL(/\/cashflow\/?$/);

        // Wait for content to load
        await page.waitForTimeout(2000);

        // Check for report content (use first() for nested mains)
        const hasContent = await page.locator('main').first().textContent();
        expect(hasContent).toBeTruthy();
    });

    test('Simulation report should load', async ({ page }) => {
        await page.goto('/simulation');
        await expect(page).toHaveURL(/\/simulation\/?$/);

        // Wait for content to load
        await page.waitForTimeout(2000);

        // Check for Monte Carlo or simulation-related content (use first() for nested mains)
        const pageContent = await page.locator('main').first().textContent();
        expect(pageContent).toBeTruthy();
    });

    test('Lifetime Performance report should load', async ({ page }) => {
        await page.goto('/performance');
        await expect(page).toHaveURL(/\/performance\/?$/);

        // Wait for content to load
        await page.waitForTimeout(2000);

        // Check for performance content (use first() for nested mains)
        const pageContent = await page.locator('main').first().textContent();
        expect(pageContent).toBeTruthy();
    });

    test('Logic Studio should load', async ({ page }) => {
        await page.goto('/logic-studio');
        await expect(page).toHaveURL(/\/logic-studio\/?$/);

        // Wait for content to load
        await page.waitForTimeout(2000);

        // Check for Logic Studio content (header or tabs)
        await expect(page.getByText(/Logic Studio|Classification Rules|Strategy Tiers|Risk Profiles/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('Wealth page should load with tabs', async ({ page }) => {
        await page.goto('/wealth');
        await expect(page).toHaveURL(/\/wealth\/?$/);

        // Wait for content to load
        await page.waitForTimeout(2000);

        // Check for Wealth page content (header or tabs)
        await expect(page.getByText(/Wealth Dashboard|Net Worth & Health|Cash Flow|YTD/i).first()).toBeVisible({ timeout: 10000 });
    });
});
