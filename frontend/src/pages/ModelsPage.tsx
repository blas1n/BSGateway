import { tenantsApi } from '../api/tenants';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { useForm } from '../hooks/useForm';
import { useDeleteConfirm } from '../hooks/useDeleteConfirm';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import type { TenantModelCreate } from '../types/api';

const INITIAL_MODEL: TenantModelCreate = { model_name: '', litellm_model: '' };

const PROVIDER_COLORS: Record<string, string> = {
  openai: 'bg-emerald-500/15 text-emerald-400',
  anthropic: 'bg-violet-500/15 text-violet-400',
  google: 'bg-blue-500/15 text-blue-400',
  azure: 'bg-sky-500/15 text-sky-400',
  ollama: 'bg-orange-500/15 text-orange-400',
  cohere: 'bg-pink-500/15 text-pink-400',
};

function getProviderBadgeClass(litellmModel: string): string {
  const provider = litellmModel.split('/')[0].toLowerCase();
  return PROVIDER_COLORS[provider] || 'bg-gray-700 text-gray-400';
}

export function ModelsPage() {
  const { tenantId } = useAuth();
  const tid = tenantId || '';
  const { data: models, loading, error, refetch } = useApi(
    () => tenantsApi.listModels(tid),
    [tid],
  );

  const {
    formData, setFormData, showForm, setShowForm,
    submitting, createError, setCreateError, handleCreate,
  } = useForm<TenantModelCreate>({
    initialValues: INITIAL_MODEL,
    validate: (v) => (!v.model_name.trim() || !v.litellm_model.trim()) ? 'Alias and model name are required' : null,
    onSubmit: async (v) => { await tenantsApi.createModel(tid, v); refetch(); },
  });

  const { deleting, deleteError, handleDelete: onDelete, setDeleteError } = useDeleteConfirm();

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onRetry={refetch} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-50">Models Registry</h2>
          <p className="text-gray-500 text-sm mt-0.5">
            {models?.length ?? 0} model{models?.length !== 1 ? 's' : ''} registered
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            showForm
              ? 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              : 'bg-accent-500 text-gray-950 hover:bg-accent-400'
          }`}
        >
          {showForm ? (
            <>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              Cancel
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              Register Model
            </>
          )}
        </button>
      </div>

      {createError && <ErrorBanner message={createError} onRetry={() => setCreateError(null)} />}

      {/* Create Form */}
      {showForm && (
        <div className="bg-gray-900 rounded-xl border border-accent-500/30 p-6 space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1 h-4 rounded-full bg-accent-500" />
            <h3 className="text-sm font-semibold text-gray-50">Register New Model</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Alias</label>
              <input
                type="text"
                value={formData.model_name}
                onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                placeholder="gpt-4o"
                className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm bg-gray-900"
              />
              <p className="text-[11px] text-gray-600 mt-1">Internal alias for routing</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">LiteLLM Model ID</label>
              <input
                type="text"
                value={formData.litellm_model}
                onChange={(e) => setFormData({ ...formData, litellm_model: e.target.value })}
                placeholder="openai/gpt-4o"
                className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono bg-gray-900"
              />
              <p className="text-[11px] text-gray-600 mt-1">provider/model format</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                API Base <span className="text-gray-600 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={formData.api_base || ''}
                onChange={(e) => setFormData({ ...formData, api_base: e.target.value || undefined })}
                placeholder="http://localhost:11434"
                className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm font-mono bg-gray-900"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                API Key <span className="text-gray-600 font-normal">(optional)</span>
              </label>
              <input
                type="password"
                value={formData.api_key || ''}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value || undefined })}
                placeholder="sk-..."
                className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm bg-gray-900"
              />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={submitting || !formData.model_name.trim() || !formData.litellm_model.trim()}
            className="bg-accent-500 text-gray-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-400 disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Registering...' : 'Register Model'}
          </button>
        </div>
      )}

      {deleteError && <ErrorBanner message={deleteError} onRetry={() => setDeleteError(null)} />}

      {/* Models Grid */}
      {models && models.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((model) => {
            const provider = model.litellm_model.split('/')[0];
            const modelId = model.litellm_model.split('/').slice(1).join('/');
            return (
              <div
                key={model.id}
                className="bg-gray-900 rounded-xl border border-gray-700 p-5 hover:border-gray-600 transition-colors group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center shrink-0">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-gray-400">
                        <path d="M7 1L13 4.5V9.5L7 13L1 9.5V4.5L7 1Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round"/>
                        <circle cx="7" cy="7" r="2" fill="currentColor" opacity="0.7"/>
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-50 text-sm truncate">{model.model_name}</p>
                      {!model.is_active && (
                        <span className="text-[10px] text-red-400">inactive</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => onDelete(model.id, () => tenantsApi.deleteModel(tid, model.id), refetch)}
                    className={`text-xs px-2 py-0.5 rounded shrink-0 ml-2 transition-colors ${
                      deleting === model.id
                        ? 'text-white bg-red-600'
                        : 'text-gray-700 hover:text-red-400 opacity-0 group-hover:opacity-100'
                    }`}
                  >
                    {deleting === model.id ? 'Confirm?' : 'Delete'}
                  </button>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide ${getProviderBadgeClass(model.litellm_model)}`}>
                      {provider}
                    </span>
                    {modelId && (
                      <span className="font-mono text-xs text-gray-500 truncate">{modelId}</span>
                    )}
                  </div>
                  {model.api_base && (
                    <p className="text-[11px] text-gray-600 font-mono truncate" title={model.api_base}>
                      {model.api_base}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-700 flex flex-col items-center justify-center py-16">
          <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center mb-4">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-gray-600">
              <path d="M10 2L18 6.5V13.5L10 18L2 13.5V6.5L10 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              <circle cx="10" cy="10" r="3" fill="currentColor" opacity="0.5"/>
            </svg>
          </div>
          <p className="text-sm text-gray-500 font-medium">No models registered</p>
          <p className="text-xs text-gray-600 mt-1">Add a model to start routing</p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-4 bg-accent-500 text-gray-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-400 transition-colors"
          >
            Register First Model
          </button>
        </div>
      )}
    </div>
  );
}
