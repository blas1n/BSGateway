import type { TenantModel } from '../types/api';

/**
 * Display label for a model dropdown option.
 *
 * LLMs show as "alias (provider)". Executor-backed models show as
 * "alias (executor-type)" — e.g. `worker-A (claude_code)` — so two
 * workers of the same type are distinguishable by their alias.
 */
export function modelDisplayLabel(m: TenantModel): string {
  if (m.provider === 'executor') {
    const execType = m.litellm_model.split('/', 2)[1];
    return execType ? `${m.model_name} (${execType})` : m.model_name;
  }
  return `${m.model_name} (${m.provider})`;
}
