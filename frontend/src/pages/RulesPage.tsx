import { useState } from 'react';
import { rulesApi } from '../api/rules';
import { useAuth } from '../hooks/useAuth';
import { useApi } from '../hooks/useApi';
import { useDeleteConfirm } from '../hooks/useDeleteConfirm';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import type { Rule, RuleCreate } from '../types/api';

const INITIAL_RULE: RuleCreate = { name: '', priority: 0, target_model: '', is_default: false };

function CreateModal({
  onClose,
  onCreated,
  tenantId,
}: {
  onClose: () => void;
  onCreated: () => void;
  tenantId: string;
}) {
  const [formData, setFormData] = useState<RuleCreate>(INITIAL_RULE);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!formData.name.trim() || !formData.target_model.trim()) {
      setError('Name and target model are required');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await rulesApi.create(tenantId, formData);
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create rule');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-gray-950/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-gray-900 rounded-xl border border-gray-700 w-full max-w-md shadow-2xl">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-1 h-4 rounded-full bg-accent-500" />
            <h3 className="text-sm font-semibold text-gray-50">New Routing Rule</h3>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-gray-500 hover:text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Modal Body */}
        <div className="px-6 py-5 space-y-4">
          {error && (
            <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Rule Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. high-priority-route"
              className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm bg-gray-800 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-accent-500/60 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Target Model</label>
            <input
              type="text"
              value={formData.target_model}
              onChange={(e) => setFormData({ ...formData, target_model: e.target.value })}
              placeholder="e.g. gpt-4o"
              className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm bg-gray-800 text-gray-100 placeholder-gray-600 font-mono focus:outline-none focus:border-accent-500/60 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Priority</label>
            <input
              type="number"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
              className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm bg-gray-800 text-gray-100 focus:outline-none focus:border-accent-500/60 transition-colors"
            />
            <p className="text-[11px] text-gray-600 mt-1">Lower number = higher priority</p>
          </div>

          <label className="flex items-center gap-2.5 cursor-pointer select-none">
            <div
              onClick={() => setFormData({ ...formData, is_default: !formData.is_default })}
              className={`w-9 h-5 rounded-full transition-colors cursor-pointer relative ${
                formData.is_default ? 'bg-accent-500' : 'bg-gray-700'
              }`}
            >
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                formData.is_default ? 'translate-x-4' : 'translate-x-0'
              }`} />
            </div>
            <span className="text-sm text-gray-300">Default rule (fallback)</span>
          </label>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={submitting || !formData.name.trim() || !formData.target_model.trim()}
            className="bg-accent-500 text-gray-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-400 disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Creating…' : 'Create Rule'}
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusToggle({ rule, tenantId, onToggled }: { rule: Rule; tenantId: string; onToggled: () => void }) {
  const [toggling, setToggling] = useState(false);

  const handleToggle = async () => {
    if (toggling) return;
    setToggling(true);
    try {
      // Cast to allow is_active which the backend PATCH accepts but RuleCreate type omits
      await (rulesApi.update as (tid: string, id: string, data: Record<string, unknown>) => Promise<Rule>)(
        tenantId,
        rule.id,
        { is_active: !rule.is_active },
      );
      onToggled();
    } finally {
      setToggling(false);
    }
  };

  return (
    <button
      onClick={handleToggle}
      disabled={toggling}
      title={rule.is_active ? 'Disable rule' : 'Enable rule'}
      className={`w-9 h-5 rounded-full transition-colors relative disabled:opacity-60 ${
        rule.is_active ? 'bg-accent-500' : 'bg-gray-700'
      }`}
    >
      <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
        rule.is_active ? 'translate-x-4' : 'translate-x-0'
      }`} />
    </button>
  );
}

export function RulesPage() {
  const { tenantId } = useAuth();
  const tid = tenantId || '';
  const { data: rules, loading, error, refetch } = useApi(
    () => rulesApi.list(tid),
    [tid],
  );

  const [showModal, setShowModal] = useState(false);
  const { deleting, deleteError, handleDelete: onDelete, setDeleteError } = useDeleteConfirm();

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onRetry={refetch} />;

  const sortedRules = rules ? [...rules].sort((a, b) => a.priority - b.priority) : [];

  return (
    <div className="space-y-6">
      {showModal && (
        <CreateModal
          tenantId={tid}
          onClose={() => setShowModal(false)}
          onCreated={refetch}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-50">Routing Rules</h2>
          <p className="text-gray-500 text-sm mt-0.5">
            {sortedRules.length} rule{sortedRules.length !== 1 ? 's' : ''} · first-match priority order
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-accent-500 text-gray-950 hover:bg-accent-400 transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          New Rule
        </button>
      </div>

      {deleteError && <ErrorBanner message={deleteError} onRetry={() => setDeleteError(null)} />}

      {/* Rules Table */}
      <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
        {sortedRules.length > 0 ? (
          <div>
            <div className="hidden sm:grid grid-cols-[48px_1fr_160px_80px_56px_80px] gap-4 px-5 py-2.5 border-b border-gray-800">
              <span className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Pri.</span>
              <span className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Name</span>
              <span className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Target</span>
              <span className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Status</span>
              <span className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider">Active</span>
              <span />
            </div>
            {sortedRules.map((rule, idx) => (
              <div
                key={rule.id}
                className={`sm:grid sm:grid-cols-[48px_1fr_160px_80px_56px_80px] flex flex-wrap gap-3 sm:gap-4 px-5 py-4 items-center hover:bg-gray-800/40 transition-colors ${
                  idx < sortedRules.length - 1 ? 'border-b border-gray-800' : ''
                }`}
              >
                <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-gray-800 text-xs font-mono font-bold text-gray-400">
                  {rule.priority}
                </span>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-100 text-sm">{rule.name}</span>
                    {rule.is_default && (
                      <span className="text-[10px] bg-accent-500/15 text-accent-500 px-1.5 py-0.5 rounded font-medium">
                        default
                      </span>
                    )}
                  </div>
                  {rule.conditions?.length > 0 && (
                    <p className="text-[11px] text-gray-600 mt-0.5">
                      {rule.conditions.length} condition{rule.conditions.length !== 1 ? 's' : ''}
                    </p>
                  )}
                </div>
                <span className="font-mono text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded-md">
                  {rule.target_model}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium w-fit ${
                  rule.is_active
                    ? 'bg-emerald-500/15 text-emerald-400'
                    : 'bg-gray-700 text-gray-500'
                }`}>
                  {rule.is_active ? 'active' : 'off'}
                </span>
                <StatusToggle rule={rule} tenantId={tid} onToggled={refetch} />
                <button
                  onClick={() => onDelete(rule.id, () => rulesApi.delete(tid, rule.id), refetch)}
                  className={`text-xs px-2.5 py-1 rounded transition-colors ${
                    deleting === rule.id
                      ? 'text-white bg-red-600'
                      : 'text-gray-600 hover:text-red-400 hover:bg-red-500/10'
                  }`}
                >
                  {deleting === rule.id ? 'Confirm?' : 'Delete'}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center mb-4">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-gray-600">
                <path d="M3 5h14M3 10h9M3 15h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <p className="text-sm text-gray-500 font-medium">No routing rules yet</p>
            <p className="text-xs text-gray-600 mt-1">Create a rule to start routing requests</p>
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 bg-accent-500 text-gray-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-accent-400 transition-colors"
            >
              Create First Rule
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
