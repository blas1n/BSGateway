import { useCallback, useEffect, useState } from 'react';
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

  const loadModelsAndRules = useCallback(async () => {
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
  }, [tid]);

  useEffect(() => {
    loadModelsAndRules();
  }, [loadModelsAndRules]);

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
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">Routing Simulator</h2>
        <p className="text-on-surface-variant">Test routing logic before deployment</p>
      </div>

      {error && <ErrorBanner message={error} onRetry={() => setError(null)} />}

      <div className="grid grid-cols-12 gap-8">
        {/* Left Panel: Input */}
        <section className="col-span-12 lg:col-span-5 flex flex-col gap-4">
          <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/15 flex flex-col h-full">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-amber-500">input</span>
                Test Input
              </h3>
              <span className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">Request Context</span>
            </div>

            <div className="space-y-6 flex-1 flex flex-col">
              {/* Model selector */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Model</label>
                {models.length > 0 ? (
                  <div className="relative">
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="w-full bg-surface-container-low border-none rounded-lg py-2 px-3 text-sm appearance-none focus:ring-1 focus:ring-amber-500 border border-outline-variant/15"
                    >
                      {models.map((m) => (
                        <option key={m.id} value={m.model_name}>
                          {m.model_name} ({m.provider})
                        </option>
                      ))}
                    </select>
                    <span className="material-symbols-outlined absolute right-2 top-2 text-slate-500 pointer-events-none">expand_more</span>
                  </div>
                ) : (
                  <div className="border border-outline-variant/15 rounded-lg px-3 py-2 text-sm text-on-surface-variant bg-surface-container-low">
                    No models registered
                  </div>
                )}
              </div>

              {/* Messages */}
              <div className="space-y-2 flex-1 flex flex-col">
                <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Prompt Content</label>
                {messages.map((msg, i) => (
                  <div key={i} className="flex-1 flex flex-col">
                    <div className="flex items-center gap-2 mb-2">
                      <select
                        value={msg.role}
                        onChange={(e) => {
                          const newMsgs = [...messages];
                          newMsgs[i].role = e.target.value as 'user' | 'assistant' | 'system';
                          setMessages(newMsgs);
                        }}
                        className="text-xs bg-surface-container-low border border-outline-variant/15 rounded px-2 py-1 font-medium text-on-surface"
                      >
                        <option value="user">user</option>
                        <option value="assistant">assistant</option>
                        <option value="system">system</option>
                      </select>
                      {messages.length > 1 && (
                        <button
                          onClick={() => setMessages(messages.filter((_, j) => j !== i))}
                          className="text-on-surface-variant hover:text-error transition-colors"
                        >
                          <span className="material-symbols-outlined text-sm">close</span>
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
                      placeholder="Paste your LLM prompt here for routing analysis..."
                      className="flex-1 w-full bg-surface-container-low border-none rounded-lg p-4 text-sm font-mono text-amber-200/80 focus:ring-1 focus:ring-amber-500 min-h-[200px] border border-outline-variant/15"
                    />
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setMessages([...messages, { role: 'user', content: '' }])}
                  className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">add</span>
                  Add Message
                </button>
              </div>

              <button
                onClick={handleTest}
                disabled={testing || !selectedModel || !messages[0]?.content}
                className="w-full bg-gradient-to-r from-primary to-primary-container text-on-primary py-4 rounded-lg font-bold text-sm flex items-center justify-center gap-2 active:scale-95 transition-transform shadow-lg shadow-amber-900/20 disabled:opacity-50"
              >
                {testing ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-sm">progress_activity</span>
                    Testing...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
                    Run Simulation
                  </>
                )}
              </button>
            </div>
          </div>
        </section>

        {/* Right Panel: Result */}
        <section className="col-span-12 lg:col-span-7 flex flex-col gap-6">
          {result ? (
            <div className="bg-surface-container-high p-6 rounded-xl border border-outline-variant/15 relative overflow-hidden">
              <div className="absolute -right-20 -top-20 w-64 h-64 bg-amber-500/5 blur-[100px]" />
              <div className="flex items-center justify-between mb-8 relative z-10">
                <h3 className="text-lg font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-amber-500">analytics</span>
                  Simulation Result
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-10 relative z-10">
                {/* Model Selection */}
                <div className="space-y-6">
                  <div className="bg-surface-container-lowest p-5 rounded-lg border border-outline-variant/15">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs text-slate-500">Routed Model</span>
                      {result.matched_rule && (
                        <span className="bg-amber-500/10 text-amber-500 text-[10px] px-2 py-0.5 rounded font-bold border border-amber-500/20">
                          MATCHED
                        </span>
                      )}
                    </div>
                    <div className="text-2xl font-bold text-on-surface tracking-tight">
                      {result.target_model || 'none'}
                    </div>
                    {result.matched_rule && (
                      <div className="mt-4 flex items-center gap-2 text-slate-400 text-xs">
                        <span className="material-symbols-outlined text-sm">gavel</span>
                        <span>Rule: {result.matched_rule.name} (P{result.matched_rule.priority})</span>
                      </div>
                    )}
                  </div>

                  {/* Context */}
                  {result.context && Object.keys(result.context).length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Request Context</h4>
                      <div className="bg-surface-container-lowest p-4 rounded-lg border border-outline-variant/15 space-y-2">
                        {Object.entries(result.context).map(([key, value]) =>
                          value !== null && value !== undefined ? (
                            <div key={key} className="flex items-center gap-2 text-xs">
                              <span className="text-on-surface-variant">{key}:</span>
                              <span className="font-mono text-on-surface truncate">{String(value)}</span>
                            </div>
                          ) : null
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Routing Flow & Triggered Rules */}
                <div className="space-y-6">
                  {/* Routing Path */}
                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Routing Path</h4>
                    <div className="flex items-center justify-between px-2">
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-8 h-8 rounded-full bg-surface-container-lowest flex items-center justify-center border border-slate-700">
                          <span className="material-symbols-outlined text-xs">input</span>
                        </div>
                        <span className="text-[9px] text-slate-500">Input</span>
                      </div>
                      <div className="h-px flex-1 bg-gradient-to-r from-slate-700 to-amber-500/50 mx-1" />
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center border border-amber-500/30">
                          <span className="material-symbols-outlined text-xs text-amber-500">psychology</span>
                        </div>
                        <span className="text-[9px] text-amber-500">Classifier</span>
                      </div>
                      <div className="h-px flex-1 bg-gradient-to-r from-amber-500/50 to-amber-500/50 mx-1" />
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center border border-amber-500/30">
                          <span className="material-symbols-outlined text-xs text-amber-500">gavel</span>
                        </div>
                        <span className="text-[9px] text-amber-500">Rules</span>
                      </div>
                      <div className="h-px flex-1 bg-gradient-to-r from-amber-500/50 to-slate-700 mx-1" />
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-8 h-8 rounded-full bg-surface-container-lowest flex items-center justify-center border border-slate-700">
                          <span className="material-symbols-outlined text-xs">memory</span>
                        </div>
                        <span className="text-[9px] text-slate-500 truncate max-w-[60px]">{result.target_model || 'None'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Evaluation trace */}
                  {result.evaluation_trace && result.evaluation_trace.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Evaluation Trace</h4>
                      <div className="space-y-2">
                        {result.evaluation_trace.map((entry, i) => {
                          const matched = entry.matched === true || entry.result === true;
                          return (
                            <div key={i} className={`flex items-center gap-3 p-2 bg-surface-container-lowest rounded border border-outline-variant/15 ${!matched ? 'opacity-50' : ''}`}>
                              <span className={`material-symbols-outlined text-sm ${matched ? 'text-amber-500' : 'text-slate-500'}`}>
                                {matched ? 'check_circle' : 'circle'}
                              </span>
                              <span className="text-xs font-medium text-on-surface font-mono truncate">
                                {JSON.stringify(entry)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-surface-container-high rounded-xl border border-outline-variant/15 flex flex-col items-center justify-center h-full min-h-[400px]">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant/20 mb-4">terminal</span>
              <p className="text-sm text-on-surface-variant font-medium">No test run yet</p>
              <p className="text-xs text-on-surface-variant/60 mt-1">Configure a request and run the simulation</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
