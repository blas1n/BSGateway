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
  openai: 'bg-green-500/15 text-green-400',
  anthropic: 'bg-violet-500/15 text-violet-400',
  google: 'bg-blue-500/15 text-blue-400',
  azure: 'bg-sky-500/15 text-sky-400',
  ollama: 'bg-orange-500/15 text-orange-400',
  cohere: 'bg-pink-500/15 text-pink-400',
};

function getProviderBadgeClass(litellmModel: string): string {
  const provider = litellmModel.split('/')[0].toLowerCase();
  return PROVIDER_COLORS[provider] || 'bg-secondary-container text-on-secondary-container';
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
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h2 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">Model Registry</h2>
          <p className="text-on-surface-variant max-w-2xl">
            Manage and monitor deployment-ready LLMs across your distributed infrastructure.
            {models && models.length > 0 && ` ${models.length} model${models.length !== 1 ? 's' : ''} registered.`}
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className={`px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all active:scale-95 ${
            showForm
              ? 'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest'
              : 'bg-primary-container text-on-primary hover:brightness-110'
          }`}
        >
          <span className="material-symbols-outlined text-sm">{showForm ? 'close' : 'add_circle'}</span>
          {showForm ? 'Cancel' : 'Register Model'}
        </button>
      </div>

      {createError && <ErrorBanner message={createError} onRetry={() => setCreateError(null)} />}

      {/* Create Form */}
      {showForm && (
        <div className="bg-surface-container-low rounded-2xl border border-primary/20 p-8 space-y-6">
          <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Register New Model</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Alias</label>
              <input
                type="text"
                value={formData.model_name}
                onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                placeholder="gpt-4o"
                className="w-full bg-surface-container-highest border-none rounded-xl py-3 px-4 text-sm focus:ring-1 focus:ring-primary/40 placeholder:text-on-surface-variant/20"
              />
              <p className="text-[10px] text-on-surface-variant/60">Internal alias for routing</p>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">LiteLLM Model ID</label>
              <input
                type="text"
                value={formData.litellm_model}
                onChange={(e) => setFormData({ ...formData, litellm_model: e.target.value })}
                placeholder="openai/gpt-4o"
                className="w-full bg-surface-container-highest border-none rounded-xl py-3 px-4 text-sm font-mono focus:ring-1 focus:ring-primary/40 placeholder:text-on-surface-variant/20"
              />
              <p className="text-[10px] text-on-surface-variant/60">provider/model format</p>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                API Base <span className="text-on-surface-variant/40 font-normal normal-case">(optional)</span>
              </label>
              <input
                type="text"
                value={formData.api_base || ''}
                onChange={(e) => setFormData({ ...formData, api_base: e.target.value || undefined })}
                placeholder="http://localhost:11434"
                className="w-full bg-surface-container-highest border-none rounded-xl py-3 px-4 text-sm font-mono focus:ring-1 focus:ring-primary/40 placeholder:text-on-surface-variant/20"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                API Key <span className="text-on-surface-variant/40 font-normal normal-case">(optional)</span>
              </label>
              <input
                type="password"
                value={formData.api_key || ''}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value || undefined })}
                placeholder="sk-..."
                className="w-full bg-surface-container-highest border-none rounded-xl py-3 px-4 text-sm focus:ring-1 focus:ring-primary/40 placeholder:text-on-surface-variant/20"
              />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={submitting || !formData.model_name.trim() || !formData.litellm_model.trim()}
            className="bg-primary-container text-on-primary px-6 py-3 rounded-xl font-bold hover:brightness-110 active:scale-95 transition-all disabled:opacity-50"
          >
            {submitting ? 'Registering...' : 'Register Model'}
          </button>
        </div>
      )}

      {deleteError && <ErrorBanner message={deleteError} onRetry={() => setDeleteError(null)} />}

      {/* Models Grid */}
      {models && models.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {models.map((model) => {
            const provider = model.litellm_model.split('/')[0];
            const modelId = model.litellm_model.split('/').slice(1).join('/');
            return (
              <div
                key={model.id}
                className={`bg-surface-container rounded-xl p-6 hover:bg-surface-container-high transition-colors group cursor-pointer border border-outline-variant/10 ${
                  !model.is_active ? 'opacity-60' : ''
                }`}
              >
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold">{model.model_name}</h3>
                      <div className={`w-2 h-2 rounded-full ${model.is_active ? 'bg-green-500' : 'bg-slate-600'}`} />
                    </div>
                    <div className="flex gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${getProviderBadgeClass(model.litellm_model)}`}>
                        {provider}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => onDelete(model.id, () => tenantsApi.deleteModel(tid, model.id), refetch)}
                    className={`transition-colors ${
                      deleting === model.id
                        ? 'text-error'
                        : 'text-slate-500 group-hover:text-amber-500 opacity-0 group-hover:opacity-100'
                    }`}
                  >
                    <span className="material-symbols-outlined">
                      {deleting === model.id ? 'check_circle' : 'more_vert'}
                    </span>
                  </button>
                </div>
                <div className="mb-6">
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Model ID</p>
                  <p className="text-on-surface font-mono text-sm">{modelId || model.litellm_model}</p>
                </div>
                {model.api_base && (
                  <p className="text-[10px] text-on-surface-variant font-mono truncate" title={model.api_base}>
                    {model.api_base}
                  </p>
                )}
                {/* Sparkline placeholder */}
                <div className="h-16 w-full flex items-end gap-1 mt-4">
                  {[40, 55, 50, 70, 65, 80, 75].map((h, i) => (
                    <div
                      key={i}
                      className={`flex-1 rounded-t transition-colors ${
                        model.is_active
                          ? i >= 5 ? 'bg-amber-500' : i >= 4 ? 'bg-amber-500/40' : 'bg-amber-500/20'
                          : i >= 5 ? 'bg-slate-500' : i >= 4 ? 'bg-slate-500/40' : 'bg-slate-500/20'
                      }`}
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-surface-container-low rounded-2xl border border-outline-variant/5 flex flex-col items-center justify-center py-16">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant/30 mb-4">category</span>
          <p className="text-sm text-on-surface-variant font-medium">No models registered</p>
          <p className="text-xs text-on-surface-variant/60 mt-1">Add a model to start routing</p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-4 bg-primary-container text-on-primary px-6 py-3 rounded-xl font-bold hover:brightness-110 transition-all"
          >
            Register First Model
          </button>
        </div>
      )}
    </div>
  );
}
