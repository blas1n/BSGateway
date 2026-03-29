import { useEffect, useState } from 'react';
import { tenantsApi } from '../api/tenants';
import { useAuth } from '../hooks/useAuth';
import { rulesApi } from '../api/rules';
import type { TenantModel } from '../types/api';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';

interface TestMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface MatchedRule {
  id: string;
  name: string;
  priority: number;
}

interface TestResult {
  matched_rule: MatchedRule | null;
  target_model: string | null;
  evaluation_trace: Record<string, unknown>[];
  context: Record<string, unknown>;
}

const ROLE_COLORS = {
  user: 'bg-blue-500/15 text-blue-400',
  assistant: 'bg-emerald-500/15 text-emerald-400',
  system: 'bg-violet-500/15 text-violet-400',
};

export function RoutingTestPage() {
  const { tenantId } = useAuth();
  const tid = tenantId || '';
  const [models, setModels] = useState<TenantModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [selectedModel, setSelectedModel] = useState('');
  const [messages, setMessages] = useState<TestMessage[]>([{ role: 'user', content: '' }]);
  const [result, setResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadModelsAndRules();
  }, []);

  const loadModelsAndRules = async () => {
    try {
      const m = await tenantsApi.listModels(tid);
      setModels(m || []);
      if (m && m.length > 0) {
        setSelectedModel(m[0].model_name);
      }
    } catch {
      setError('Failed to load models');
    } finally {
      setLoadingModels(false);
    }
  };

  const handleTest = async () => {
    if (!selectedModel || !messages[0]?.content) {
      setError('Model and at least one message required');
      return;
    }

    setTesting(true);
    setError(null);
    try {
      const data = await rulesApi.test(tid, {
        model: selectedModel,
        messages: messages.filter(m => m.content.trim()),
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test failed');
    } finally {
      setTesting(false);
    }
  };

  if (loadingModels) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-50">Routing Simulator</h2>
        <p className="text-gray-500 text-sm mt-0.5">Test routing logic before deployment</p>
      </div>

      {error && <ErrorBanner message={error} onRetry={() => setError(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        <div className="space-y-4">
          <div className="bg-gray-900 rounded-xl border border-gray-700 p-5 space-y-4">
            <h3 className="text-sm font-semibold text-gray-50 flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-gray-400">
                <rect x="1" y="2" width="12" height="10" rx="2" stroke="currentColor" strokeWidth="1.25"/>
                <path d="M4 6h6M4 8.5h4" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"/>
              </svg>
              Request Configuration
            </h3>

            {/* Model selector */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Model</label>
              {models.length > 0 ? (
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full border border-gray-700 rounded-lg px-3 py-2 text-sm bg-gray-900"
                >
                  {models.map((m) => (
                    <option key={m.id} value={m.model_name}>
                      {m.model_name} ({m.provider})
                    </option>
                  ))}
                </select>
              ) : (
                <div className="border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-600 bg-gray-900/50">
                  No models registered
                </div>
              )}
            </div>

            {/* Messages */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2">Messages</label>
              <div className="space-y-3">
                {messages.map((msg, i) => (
                  <div key={i} className="rounded-lg border border-gray-700 bg-gray-900/60 overflow-hidden">
                    <div className="flex items-center justify-between px-3 py-2 bg-gray-800/50 border-b border-gray-700">
                      <select
                        value={msg.role}
                        onChange={(e) => {
                          const newMsgs = [...messages];
                          newMsgs[i].role = e.target.value as 'user' | 'assistant' | 'system';
                          setMessages(newMsgs);
                        }}
                        className="text-xs bg-transparent border-0 p-0 font-medium text-gray-300 cursor-pointer"
                      >
                        <option value="user">user</option>
                        <option value="assistant">assistant</option>
                        <option value="system">system</option>
                      </select>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${ROLE_COLORS[msg.role]}`}>
                        {msg.role}
                      </span>
                      {messages.length > 1 && (
                        <button
                          onClick={() => setMessages(messages.filter((_, j) => j !== i))}
                          className="text-gray-600 hover:text-red-400 transition-colors ml-2"
                        >
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                            <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                          </svg>
                        </button>
                      )}
                    </div>
                    <textarea
                      value={msg.content}
                      onChange={(e) => {
                        const newMsgs = [...messages];
                        newMsgs[i].content = e.target.value;
                        setMessages(newMsgs);
                      }}
                      placeholder="Message content..."
                      className="w-full px-3 py-2 text-sm bg-transparent border-0 resize-none text-gray-200 placeholder-gray-600"
                      rows={2}
                    />
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setMessages([...messages, { role: 'user', content: '' }])}
                className="mt-2 text-xs text-accent-500 hover:text-accent-400 flex items-center gap-1 transition-colors"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M6 2v8M2 6h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                Add Message
              </button>
            </div>

            <button
              onClick={handleTest}
              disabled={testing || !selectedModel || !messages[0]?.content}
              className="w-full bg-accent-500 text-gray-950 py-2.5 rounded-lg text-sm font-semibold hover:bg-accent-400 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {testing ? (
                <>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="animate-spin">
                    <path d="M7 1.5A5.5 5.5 0 0112.5 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                  Testing...
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M3 13L7 9M7 9L5 4L12 3L11 10L7 9Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
                  </svg>
                  Run Routing Test
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Panel */}
        <div>
          {result ? (
            <div className="bg-gray-900 rounded-xl border border-gray-700 p-5 space-y-5">
              <h3 className="text-sm font-semibold text-gray-50 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Test Result
              </h3>

              {/* Primary result */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-800 rounded-lg p-4">
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">Target Model</p>
                  <p className="font-mono text-sm font-semibold text-gray-50 break-all">
                    {result.target_model || <span className="text-gray-600">none</span>}
                  </p>
                </div>
                <div className="bg-gray-800 rounded-lg p-4">
                  <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1.5">Matched Rule</p>
                  {result.matched_rule ? (
                    <div>
                      <p className="text-sm font-semibold text-gray-50">{result.matched_rule.name}</p>
                      <p className="text-[11px] text-gray-600 mt-0.5">priority {result.matched_rule.priority}</p>
                    </div>
                  ) : (
                    <p className="font-mono text-sm text-gray-600">none</p>
                  )}
                </div>
              </div>

              {/* Context */}
              {result.context && Object.keys(result.context).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-400 mb-2 flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.25"/>
                      <path d="M6 5.5V8" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"/>
                      <circle cx="6" cy="4" r="0.5" fill="currentColor"/>
                    </svg>
                    Request Context
                  </p>
                  <div className="bg-gray-800 rounded-lg p-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {Object.entries(result.context).map(([key, value]) =>
                      value !== null && value !== undefined ? (
                        <div key={key} className="flex items-center gap-1.5 text-xs min-w-0">
                          <span className="text-gray-600 shrink-0">{key}:</span>
                          <span className="font-mono text-gray-300 truncate">{String(value)}</span>
                        </div>
                      ) : null
                    )}
                  </div>
                </div>
              )}

              {/* Evaluation trace */}
              {result.evaluation_trace && result.evaluation_trace.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-400 mb-2 flex items-center gap-1">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <rect x="1" y="1" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.25"/>
                      <path d="M3.5 5h5M3.5 7.5h3" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"/>
                    </svg>
                    Evaluation Trace
                  </p>
                  <div className="space-y-1.5">
                    {result.evaluation_trace.map((entry, i) => {
                      const safeEntry: Record<string, unknown> = {};
                      for (const [k, v] of Object.entries(entry)) {
                        safeEntry[k] = typeof v === 'string' ? v : JSON.stringify(v);
                      }
                      return (
                        <div key={i} className="text-[11px] font-mono bg-gray-800 rounded-lg px-3 py-2 whitespace-pre-wrap break-all text-gray-400 leading-relaxed">
                          {JSON.stringify(safeEntry)}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-900 rounded-xl border border-gray-700 flex flex-col items-center justify-center h-full min-h-[280px]">
              <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center mb-4">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-gray-600">
                  <path d="M4 18L9 12M9 12L6 5L16 4L15 13L9 12Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round"/>
                </svg>
              </div>
              <p className="text-sm text-gray-500 font-medium">No test run yet</p>
              <p className="text-xs text-gray-600 mt-1">Configure a request and run the test</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
