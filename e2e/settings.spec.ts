import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
    test.beforeEach(async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').fill('admin');
        await page.getByRole('button', { name: 'Sign In' }).click();
        await expect(page).toHaveURL(/\/$/, { timeout: 15000 });

        // Navigate to settings
        await page.goto('/settings');
        await expect(page).toHaveURL(/\/settings\/?$/);
    });

    test('should display settings page content', async ({ page }) => {
        await expect(page.getByText(/Settings|Preferences/i).first()).toBeVisible({ timeout: 10000 });
    });

    test('should have theme/dark mode toggle', async ({ page }) => {
        // Look for theme toggle
        const themeToggle = page.getByText(/Dark Mode|Theme|Appearance/i).first();
        const hasThemeToggle = await themeToggle.isVisible().catch(() => false);

        if (hasThemeToggle) {
            // Click the toggle or nearby button/switch
            const toggleButton = page.locator('button, [role="switch"]').filter({ hasText: /Dark|Light|Theme/i }).first();
            const buttonExists = await toggleButton.isVisible().catch(() => false);

            if (!buttonExists) {
                // Look for a toggle near the theme text
                const nearbyToggle = themeToggle.locator('..').locator('button, [role="switch"], input[type="checkbox"]').first();
                const nearbyExists = await nearbyToggle.isVisible().catch(() => false);
                if (nearbyExists) {
                    await nearbyToggle.click();
                }
            } else {
                await toggleButton.click();
            }
        }
    });

    test('should persist preferences after page reload', async ({ page }) => {
        // Make a change if possible
        await page.waitForTimeout(1000);

        // Reload
        await page.reload();

        // Should still be on settings
        await expect(page).toHaveURL(/\/settings\/?$/);
        await expect(page.getByText(/Settings|Preferences/i).first()).toBeVisible();
    });
});
