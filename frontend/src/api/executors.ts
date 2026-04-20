import type { ExecutorTask, Worker } from '../types/api';
import { api } from './client';

export const executorsApi = {
  submitTask: (executorType: string, prompt: string) =>
    api.post<ExecutorTask>('/execute', { executor_type: executorType, prompt }),

  getTask: (taskId: string) =>
    api.get<ExecutorTask>(`/tasks/${taskId}`),

  listTasks: (limit = 50, offset = 0) =>
    api.get<ExecutorTask[]>(`/tasks?limit=${limit}&offset=${offset}`),

  listWorkers: () =>
    api.get<Worker[]>(`/workers`),

  getInstallToken: () =>
    api.get<{ token: string | null; has_token: boolean }>(`/workers/install-token`),

  createInstallToken: () =>
    api.post<{ token: string; has_token: boolean }>(`/workers/install-token`),

  revokeInstallToken: () =>
    api.delete<void>(`/workers/install-token`),
};
