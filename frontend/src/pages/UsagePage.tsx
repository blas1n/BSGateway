import { useEffect, useState } from 'react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import { api } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBanner } from '../components/common/ErrorBanner';
import type { UsageResponse } from '../types/api';

const COLORS = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#ec4899'];

const PERIOD_LABELS = {
  day: 'Today',
  week: 'Last 7 days',
  month: 'Last 30 days',
};

export function UsagePage() {
  const { tenantId } = useAuth();
  const tid = tenantId || '';
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('week');
  const [data, setData] = useState<UsageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUsage();
  }, [period]);

  const loadUsage = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<UsageResponse>(
        `/tenants/${tid}/usage?period=${period}`
      );
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load usage data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  const dailyData = data?.daily_breakdown
    ? data.daily_breakdown.map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      requests: d.requests,
    }))
    : [];

  const modelData = data?.by_model
    ? Object.entries(data.by_model).map(([model, usage]) => ({
      name: model,
      value: usage.requests,
    }))
    : [];

  const ruleData = data?.by_rule
    ? Object.entries(data.by_rule).map(([rule, requests]) => ({
      name: rule,
      requests,
    }))
    : [];

  const totalRequests = data?.total_requests ?? 0;
  const totalTokens = data?.total_tokens ?? 0;
  const modelCount = data ? Object.keys(data.by_model).length : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-50">Usage Analytics</h2>
          <p className="text-gray-500 text-sm mt-0.5">Routing traffic and token consumption</p>
        </div>
        <div className="flex items-center gap-1 bg-gray-900 border border-gray-700 rounded-lg p-1">
          {(['day', 'week', 'month'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                period === p
                  ? 'bg-accent-500 text-gray-950'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={loadUsage} />}

      {/* Summary Stats */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              label: 'Total Requests',
              value: totalRequests.toLocaleString(),
              icon: (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 12L5 8L7.5 10L10.5 5L14 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              ),
              accent: true,
            },
            {
              label: 'Total Tokens',
              value: totalTokens > 1_000_000
                ? `${(totalTokens / 1_000_000).toFixed(2)}M`
                : totalTokens > 1_000
                ? `${(totalTokens / 1_000).toFixed(1)}K`
                : totalTokens.toLocaleString(),
              icon: (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M8 5.5V8L9.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              ),
            },
            {
              label: 'Active Models',
              value: modelCount,
              icon: (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 2L14 5.5V10.5L8 14L2 10.5V5.5L8 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  <circle cx="8" cy="8" r="2" fill="currentColor" opacity="0.8"/>
                </svg>
              ),
            },
          ].map((stat) => (
            <div key={stat.label} className="bg-gray-900 rounded-xl border border-gray-700 p-5">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 ${
                stat.accent ? 'bg-accent-500/15 text-accent-500' : 'bg-gray-800 text-gray-400'
              }`}>
                {stat.icon}
              </div>
              <p className="text-2xl font-bold text-gray-50 tabular-nums">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Daily Trend */}
      {dailyData.length > 0 && (
        <div className="bg-gray-900 rounded-xl border border-gray-700 p-6">
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-gray-50">Daily Requests</h3>
            <p className="text-xs text-gray-500 mt-0.5">{PERIOD_LABELS[period]}</p>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={dailyData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
              <defs>
                <linearGradient id="usageGradient" x1="0" y1="0" x2="0" y2="1">
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
                fill="url(#usageGradient)"
                dot={{ fill: '#f59e0b', r: 3, strokeWidth: 0 }}
                activeDot={{ fill: '#f59e0b', r: 5, strokeWidth: 0 }}
                name="Requests"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* By Model & By Rule */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {modelData.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-700 p-6">
            <h3 className="text-sm font-semibold text-gray-50 mb-1">Traffic by Model</h3>
            <p className="text-xs text-gray-500 mb-5">Request distribution</p>
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={160}>
                <PieChart>
                  <Pie
                    data={modelData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    dataKey="value"
                    strokeWidth={0}
                  >
                    {modelData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111218', border: '1px solid #2a2d42', borderRadius: '8px', color: '#f2f3f7', fontSize: '11px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {modelData.slice(0, 5).map((item, index) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="text-gray-400 truncate flex-1">{item.name}</span>
                    <span className="text-gray-500 tabular-nums shrink-0">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {ruleData.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-700 p-6">
            <h3 className="text-sm font-semibold text-gray-50 mb-1">Traffic by Rule</h3>
            <p className="text-xs text-gray-500 mb-5">Routing rule hits</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={ruleData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2033" vertical={false} />
                <XAxis dataKey="name" stroke="#2a2d42" tick={{ fill: '#5a5f7d', fontSize: 11 }} tickLine={false} />
                <YAxis stroke="#2a2d42" tick={{ fill: '#5a5f7d', fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111218', border: '1px solid #2a2d42', borderRadius: '8px', color: '#f2f3f7', fontSize: '12px' }}
                  cursor={{ fill: '#1e2033' }}
                />
                <Bar dataKey="requests" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Requests" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {!data && !loading && (
        <div className="bg-gray-900 rounded-xl border border-gray-700 flex flex-col items-center justify-center py-16">
          <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center mb-4">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-gray-600">
              <path d="M2 16L6 10L9 13L13 7L18 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <p className="text-sm text-gray-500 font-medium">No usage data available</p>
          <p className="text-xs text-gray-600 mt-1">Start routing requests to see analytics</p>
        </div>
      )}
    </div>
  );
}
