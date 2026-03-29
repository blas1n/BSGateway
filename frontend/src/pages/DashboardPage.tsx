import { useEffect, useState } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { rulesApi } from '../api/rules';
import { tenantsApi } from '../api/tenants';
import { usageApi } from '../api/usage';
import { useAuth } from '../hooks/useAuth';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';

interface Stat {
  label: string;
  value: string | number;
  subtext?: string;
  icon: React.ReactNode;
  accent?: boolean;
}

interface UsageData {
  date: string;
  requests: number;
}

const StatCard = ({ stat }: { stat: Stat }) => (
  <div className="bg-gray-900 rounded-xl p-5 border border-gray-700 hover:border-gray-600 transition-colors group">
    <div className="flex items-start justify-between mb-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
        stat.accent ? 'bg-accent-500/15 text-accent-500' : 'bg-gray-800 text-gray-400'
      }`}>
        {stat.icon}
      </div>
    </div>
    <p className="text-2xl font-bold text-gray-50 tabular-nums">{stat.value}</p>
    <p className="text-xs font-medium text-gray-400 mt-1">{stat.label}</p>
    {stat.subtext && <p className="text-[11px] text-gray-600 mt-0.5">{stat.subtext}</p>}
  </div>
);

export function DashboardPage() {
  const { tenantId, tenantName } = useAuth();
  const tid = tenantId || '';
  const [stats, setStats] = useState<Stat[]>([]);
  const [usageData, setUsageData] = useState<UsageData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [rules, models, usage] = await Promise.all([
        rulesApi.list(tid).catch(() => []),
        tenantsApi.listModels(tid).catch(() => []),
        usageApi.get(tid, 'week').catch(() => null),
      ]);

      const ruleCount = Array.isArray(rules) ? rules.length : 0;
      const modelCount = Array.isArray(models) ? models.length : 0;
      const totalRequests = usage?.total_requests || 0;
      const totalTokens = usage?.total_tokens || 0;

      setStats([
        {
          label: 'Active Rules',
          value: ruleCount,
          subtext: 'routing policies',
          accent: true,
          icon: (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 4h12M2 8h8M2 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="13" cy="8" r="2" fill="currentColor" opacity="0.8"/>
            </svg>
          ),
        },
        {
          label: 'Registered Models',
          value: modelCount,
          subtext: 'LLM endpoints',
          icon: (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 2L14 5.5V10.5L8 14L2 10.5V5.5L8 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              <circle cx="8" cy="8" r="2" fill="currentColor" opacity="0.8"/>
            </svg>
          ),
        },
        {
          label: 'Weekly Requests',
          value: totalRequests.toLocaleString(),
          subtext: 'last 7 days',
          accent: true,
          icon: (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 12L5 8L7.5 10L10.5 5L14 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          ),
        },
        {
          label: 'Total Tokens',
          value: totalTokens > 1_000_000
            ? `${(totalTokens / 1_000_000).toFixed(1)}M`
            : totalTokens > 1_000
            ? `${(totalTokens / 1_000).toFixed(1)}K`
            : totalTokens.toString(),
          subtext: 'processed this week',
          icon: (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M8 5.5V8L9.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          ),
        },
      ]);

      if (usage?.daily_breakdown) {
        const chartData = usage.daily_breakdown.map((d) => ({
          date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          requests: d.requests,
        }));
        setUsageData(chartData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-50">
            {tenantName ? `${tenantName} Overview` : 'Dashboard'}
          </h2>
          <p className="text-gray-500 text-sm mt-0.5">Routing overview and metrics</p>
        </div>
        <button
          onClick={loadDashboard}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-colors"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M10 6A4 4 0 112 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M10 2v4H6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Refresh
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadDashboard} />}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </div>

      {/* Usage Trend */}
      {usageData.length > 0 ? (
        <div className="bg-gray-900 rounded-xl border border-gray-700 p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-sm font-semibold text-gray-50">Request Trend</h3>
              <p className="text-xs text-gray-500 mt-0.5">Last 7 days</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={usageData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
              <defs>
                <linearGradient id="requestGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2033" vertical={false} />
              <XAxis dataKey="date" stroke="#2a2d42" tick={{ fill: '#5a5f7d', fontSize: 11 }} tickLine={false} />
              <YAxis stroke="#2a2d42" tick={{ fill: '#5a5f7d', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#111218', border: '1px solid #2a2d42', borderRadius: '8px', color: '#f2f3f7', fontSize: '12px' }}
                labelStyle={{ color: '#8187a8' }}
                cursor={{ stroke: '#2a2d42' }}
              />
              <Area
                type="monotone"
                dataKey="requests"
                stroke="#f59e0b"
                strokeWidth={2}
                fill="url(#requestGradient)"
                dot={{ fill: '#f59e0b', r: 3, strokeWidth: 0 }}
                activeDot={{ fill: '#f59e0b', r: 5, strokeWidth: 0 }}
                name="Requests"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-700 p-10 text-center">
          <div className="w-10 h-10 rounded-xl bg-gray-800 flex items-center justify-center mx-auto mb-3">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-gray-500">
              <path d="M2 14L6 9L9 11L12 6L16 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <p className="text-sm text-gray-500">No usage data yet</p>
          <p className="text-xs text-gray-600 mt-1">Start routing requests to see trends</p>
        </div>
      )}

      {/* Quick Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-lg bg-accent-500/15 flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-accent-500">
                <path d="M7 1L8.5 5H13L9.5 7.5L11 11.5L7 9L3 11.5L4.5 7.5L1 5H5.5L7 1Z" fill="currentColor"/>
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-gray-50">Getting Started</h3>
          </div>
          <ul className="space-y-2">
            {[
              'Register your LLM models in the Models tab',
              'Create routing rules to control traffic',
              'Test your rules with the Route Test tool',
              'Monitor usage metrics here',
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-400">
                <span className="text-accent-500 mt-0.5 shrink-0">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-gray-900 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-lg bg-gray-800 flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-gray-400">
                <rect x="1" y="2" width="12" height="10" rx="2" stroke="currentColor" strokeWidth="1.25"/>
                <path d="M4 6h2M4 8.5h6" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round"/>
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-gray-50">API Integration</h3>
          </div>
          <p className="text-xs text-gray-400 mb-3">
            Use the chat completions endpoint:
          </p>
          <code className="block bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-accent-400 mb-3">
            POST /api/v1/chat/completions
          </code>
          <p className="text-xs text-gray-500">
            Authenticate with your Supabase JWT as a Bearer token.
            Generate API keys in the <span className="text-accent-500">API Keys</span> section.
          </p>
        </div>
      </div>
    </div>
  );
}
