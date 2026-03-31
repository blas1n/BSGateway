import { test, expect } from '@playwright/test';
import { injectAuth, mockTenantInfo, mockGet, mockPost, MOCK_RULES } from './helpers';

test.describe('Rules Page', () => {
  test.beforeEach(async ({ page }) => {
    await injectAuth(page);
    await mockTenantInfo(page);
    await mockGet(page, '/rules', MOCK_RULES);
  });

  test('displays page heading and description', async ({ page }) => {
    await page.goto('/rules');
    await expect(page.getByRole('heading', { name: /routing rules/i })).toBeVisible();
    await expect(page.getByText(/configure intelligent traffic distribution/i)).toBeVisible();
    await expect(page.getByText('2 rules configured.')).toBeVisible();
  });

  test('shows rules table with correct column headers', async ({ page }) => {
    await page.goto('/rules');
    const headers = page.locator('thead th');
    await expect(headers).toHaveCount(5); // Name, Target Model, Priority, Status, Actions
    await expect(page.getByRole('columnheader', { name: 'Name' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Target Model' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Priority' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();
  });

  test('renders rule rows with names and models', async ({ page }) => {
    await page.goto('/rules');
    await expect(page.getByText('High Priority Router')).toBeVisible();
    await expect(page.getByText('Default Fallback')).toBeVisible();
    await expect(page.getByText('openai/gpt-4o', { exact: true })).toBeVisible();
    await expect(page.getByText('openai/gpt-4o-mini')).toBeVisible();
  });

  test('shows default badge on default rule', async ({ page }) => {
    await page.goto('/rules');
    await expect(page.getByText('default', { exact: true })).toBeVisible();
  });

  test('shows priority badges (P1, P5)', async ({ page }) => {
    await page.goto('/rules');
    await expect(page.getByText('P1')).toBeVisible();
    await expect(page.getByText('P5')).toBeVisible();
  });

  test('shows conditions count on rule with conditions', async ({ page }) => {
    await page.goto('/rules');
    await expect(page.getByText('1 condition')).toBeVisible();
  });

  test('Create Rule button opens modal', async ({ page }) => {
    await page.goto('/rules');
    await page.getByRole('button', { name: /create rule/i }).click();
    await expect(page.getByRole('heading', { name: /create routing rule/i })).toBeVisible();
  });

  test('create modal has name input, target model input, and priority slider', async ({ page }) => {
    await page.goto('/rules');
    await page.getByRole('button', { name: /create rule/i }).click();

    await expect(page.getByPlaceholder(/high priority customer router/i)).toBeVisible();
    await expect(page.getByPlaceholder('e.g. openai/gpt-4o')).toBeVisible();
    await expect(page.getByText('Execution Priority')).toBeVisible();
    await expect(page.getByRole('slider')).toBeVisible();
  });

  test('create modal has default rule toggle', async ({ page }) => {
    await page.goto('/rules');
    await page.getByRole('button', { name: /create rule/i }).click();
    await expect(page.getByText('Default rule (fallback)')).toBeVisible();
  });

  test('create modal Save & Deploy button disabled without required fields', async ({ page }) => {
    await page.goto('/rules');
    await page.getByRole('button', { name: /create rule/i }).click();
    const saveBtn = page.getByRole('button', { name: /save & deploy/i });
    await expect(saveBtn).toBeDisabled();
  });

  test('create modal close button works', async ({ page }) => {
    await page.goto('/rules');
    await page.getByRole('button', { name: /create rule/i }).click();
    await expect(page.getByRole('heading', { name: /create routing rule/i })).toBeVisible();
    // Click close (X) button
    await page.locator('button:has(span:text("close"))').first().click();
    await expect(page.getByRole('heading', { name: /create routing rule/i })).not.toBeVisible();
  });

  test('empty state shows when no rules exist', async ({ page }) => {
    await mockGet(page, '/rules', []);
    await page.goto('/rules');
    await expect(page.getByText('No routing rules yet')).toBeVisible();
    await expect(page.getByText('Create First Rule')).toBeVisible();
  });
});
