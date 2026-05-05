/**
 * BSGateway demo smoke tests.
 *
 * The actual test bodies live in `@bsvibe/demo/testing` so all four
 * products run identical assertions. Localhost defaults match
 * `_infra/scripts/demo-up-local.sh BSGateway`.
 *
 * Run locally:
 *   ~/Works/_infra/scripts/demo-up-local.sh BSGateway
 *   DEMO_E2E_BASE_URL=http://localhost:14500 \
 *   DEMO_E2E_API_URL=http://localhost:14500 \
 *     pnpm test:e2e --grep @demo
 *
 * Run in CI: see .github/workflows/demo-smoke.yml.
 */

import { runDemoSmokeSuite } from '@bsvibe/demo/testing';

runDemoSmokeSuite({
  product: 'BSGateway',
  baseUrl: process.env.DEMO_E2E_BASE_URL ?? 'http://localhost:14500',
  apiUrl: process.env.DEMO_E2E_API_URL ?? 'http://localhost:14500',
});
