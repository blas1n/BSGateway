import { test, expect } from '@playwright/test';
import { injectAuth, mockTenantInfo, mockGet, mockPost, MOCK_MODELS, MOCK_RULES, MOCK_TEST_RESULT } from './helpers';

test.describe('Routing Simulator Page', () => {
  test.beforeEach(async ({ page }) => {
    await injectAuth(page);
    await mockTenantInfo(page);
    await mockGet(page, '/models', MOCK_MODELS);
    await mockGet(page, '/rules', MOCK_RULES);
  });

  test('displays page heading', async ({ page }) => {
    await page.goto('/test');
    await expect(page.getByRole('heading', { name: /routing simulator/i })).toBeVisible();
    await expect(page.getByText('Test routing logic before deployment')).toBeVisible();
  });

  test('shows split panel layout with Test Input and empty result', async ({ page }) => {
    await page.goto('/test');
    await expect(page.getByText('Test Input')).toBeVisible();
    await expect(page.getByText('No test run yet')).toBeVisible();
    await expect(page.getByText('Configure a request and run the simulation')).toBeVisible();
  });

  test('model selector populated with registered models', async ({ page }) => {
    await page.goto('/test');
    const select = page.locator('select').first();
    await expect(select).toBeVisible();
    // Check options contain model names
    await expect(select.locator('option')).toHaveCount(3);
  });

  test('prompt textarea is visible with placeholder', async ({ page }) => {
    await page.goto('/test');
    await expect(page.getByPlaceholder(/paste your llm prompt here/i)).toBeVisible();
  });

  test('Run Simulation button disabled without prompt', async ({ page }) => {
    await page.goto('/test');
    const btn = page.getByRole('button', { name: /run simulation/i });
    await expect(btn).toBeDisabled();
  });

  test('Add Message button adds another message input', async ({ page }) => {
    await page.goto('/test');
    const addBtn = page.getByText('Add Message');
    await addBtn.click();
    // Should now have 2 textareas
    const textareas = page.locator('textarea');
    await expect(textareas).toHaveCount(2);
  });

  test('shows simulation result after test run', async ({ page }) => {
    await mockPost(page, '/rules/test', MOCK_TEST_RESULT);
    await page.goto('/test');

    // Type a prompt
    await page.getByPlaceholder(/paste your llm prompt here/i).fill('Explain quantum computing in detail');

    // Run simulation
    await page.getByRole('button', { name: /run simulation/i }).click();

    // Result panel
    await expect(page.getByText('Simulation Result')).toBeVisible();
    await expect(page.getByText('openai/gpt-4o').first()).toBeVisible();
    await expect(page.getByText('MATCHED', { exact: true })).toBeVisible();
  });

  test('result shows routing path visualization', async ({ page }) => {
    await mockPost(page, '/rules/test', MOCK_TEST_RESULT);
    await page.goto('/test');
    await page.getByPlaceholder(/paste your llm prompt here/i).fill('Test prompt');
    await page.getByRole('button', { name: /run simulation/i }).click();

    // Routing path nodes (scoped to main content area, not sidebar)
    const main = page.getByRole('main');
    await expect(main.getByText('Input', { exact: true })).toBeVisible();
    await expect(main.getByText('Classifier')).toBeVisible();
    await expect(main.getByText('Routing Path')).toBeVisible();
  });

  test('result shows matched rule info', async ({ page }) => {
    await mockPost(page, '/rules/test', MOCK_TEST_RESULT);
    await page.goto('/test');
    await page.getByPlaceholder(/paste your llm prompt here/i).fill('Test prompt');
    await page.getByRole('button', { name: /run simulation/i }).click();

    await expect(page.getByText(/Rule: High Priority Router/)).toBeVisible();
  });

  test('result shows evaluation trace', async ({ page }) => {
    await mockPost(page, '/rules/test', MOCK_TEST_RESULT);
    await page.goto('/test');
    await page.getByPlaceholder(/paste your llm prompt here/i).fill('Test prompt');
    await page.getByRole('button', { name: /run simulation/i }).click();

    await expect(page.getByText('Evaluation Trace')).toBeVisible();
  });

  test('result shows request context', async ({ page }) => {
    await mockPost(page, '/rules/test', MOCK_TEST_RESULT);
    await page.goto('/test');
    await page.getByPlaceholder(/paste your llm prompt here/i).fill('Test prompt');
    await page.getByRole('button', { name: /run simulation/i }).click();

    await expect(page.getByText('Request Context')).toBeVisible();
    await expect(page.getByText('complexity_score:')).toBeVisible();
  });
});
