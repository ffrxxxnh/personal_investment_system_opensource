import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
    test.beforeEach(async ({ page }) => {
        // Clear any existing session
        await page.context().clearCookies();
    });

    test('should redirect unauthenticated user to login', async ({ page }) => {
        await page.goto('/');
        await expect(page).toHaveURL(/\/login/);
    });

    test('should display login form correctly', async ({ page }) => {
        await page.goto('/login');

        // Check page elements
        await expect(page.getByRole('heading', { name: 'WealthOS' })).toBeVisible();
        await expect(page.getByText('Personal Investment System')).toBeVisible();
        await expect(page.getByLabel('Username')).toBeVisible();
        await expect(page.getByLabel('Password')).toBeVisible();
        await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
    });

    test('should show error for invalid credentials', async ({ page }) => {
        await page.goto('/login');

        await page.getByLabel('Username').fill('invalid');
        await page.getByLabel('Password').fill('wrongpassword');
        await page.getByRole('button', { name: 'Sign In' }).click();

        // Wait for error message
        await expect(page.getByText(/Login failed|Invalid/i)).toBeVisible({ timeout: 10000 });
    });

    test('should login successfully with valid credentials', async ({ page }) => {
        await page.goto('/login');

        // Fill login form with default credentials
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').fill('admin');
        await page.getByRole('button', { name: 'Sign In' }).click();

        // Should redirect to dashboard after login (accept both localhost and 127.0.0.1)
        await expect(page).toHaveURL(/\/$/, { timeout: 15000 });

        // Dashboard content should be visible ("Welcome back" greeting)
        await expect(page.getByText(/Welcome back|Net Worth|WealthOS/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should persist session after page refresh', async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').fill('admin');
        await page.getByRole('button', { name: 'Sign In' }).click();
        await expect(page).toHaveURL(/\/$/, { timeout: 15000 });

        // Refresh the page
        await page.reload();

        // Should still be on dashboard (not redirected to login)
        await expect(page).toHaveURL(/\/$/);
    });
});
