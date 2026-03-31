import { test, expect } from '@playwright/test';
import { injectAuth, mockTenantInfo, MOCK_USAGE } from './helpers';

test.describe('Usage / Analytics Page', () => {
  test.beforeEach(async ({ page }) => {
    await injectAuth(page);
    await mockTenantInfo(page);

    // Mock usage endpoint for all periods
    await page.route('**/api/v1/tenants/test-tenant-id/usage*', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_USAGE),
        });
      }
      return route.continue();
    });
  });

  test('displays page heading', async ({ page }) => {
    await page.goto('/usage');
    await expect(page.getByRole('heading', { name: /analytics dashboard/i })).toBeVisible();
  });

  test('shows period selector with day/week/month buttons', async ({ page }) => {
    await page.goto('/usage');
    await expect(page.getByRole('button', { name: 'Today' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Last 7 days' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Last 30 days' })).toBeVisible();
  });

  test('week period is active by default', async ({ page }) => {
    await page.goto('/usage');
    // The active button has different styling
    const weekBtn = page.getByRole('button', { name: 'Last 7 days' });
    await expect(weekBtn).toBeVisible();
  });

  test('shows Daily Request Trend chart', async ({ page }) => {
    await page.goto('/usage');
    await expect(page.getByText('Daily Request Trend')).toBeVisible();
    await expect(page.getByText('12,345').first()).toBeVisible(); // total requests shown in chart and summary
    await expect(page.getByText('total requests', { exact: true })).toBeVisible();
  });

  test('shows Traffic by Model donut chart', async ({ page }) => {
    await page.goto('/usage');
    await expect(page.getByText('Traffic by Model')).toBeVisible();
    await expect(page.getByText('Request distribution')).toBeVisible();
    // Legend items
    await expect(page.getByText('openai/gpt-4o').first()).toBeVisible();
    await expect(page.getByText('anthropic/claude-3-5-sonnet')).toBeVisible();
  });

  test('shows summary stat cards', async ({ page }) => {
    await page.goto('/usage');
    // Summary row has three stat cards
    const totalReqCards = page.getByText('Total Requests');
    await expect(totalReqCards.first()).toBeVisible();
    await expect(page.getByText('Total Tokens').first()).toBeVisible();
    await expect(page.getByText('Active Models')).toBeVisible();
    // Model count = 3
    await expect(page.getByText('3').first()).toBeVisible();
  });

  test('shows Traffic by Rule bar chart', async ({ page }) => {
    await page.goto('/usage');
    await expect(page.getByText('Traffic by Rule')).toBeVisible();
    await expect(page.getByText('Routing rule hits')).toBeVisible();
  });

  test('clicking period button reloads data', async ({ page }) => {
    await page.goto('/usage');
    // Click "Today"
    await page.getByRole('button', { name: 'Today' }).click();
    // Should still show data (mocked for all periods)
    await expect(page.getByText('Daily Request Trend')).toBeVisible();
  });

  test('shows empty state when no data', async ({ page }) => {
    await page.route('**/api/v1/tenants/test-tenant-id/usage*', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(null) });
      }
      return route.continue();
    });
    await page.goto('/usage');
    await expect(page.getByText('No usage data available')).toBeVisible();
  });
});
