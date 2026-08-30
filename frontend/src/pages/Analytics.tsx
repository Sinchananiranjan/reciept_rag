import React, { useState, useEffect, useMemo } from 'react';
import {
  Sparkles, TrendingUp, AlertCircle, ShoppingBag, Loader2, Building2, Tag,
  DollarSign, Receipt as ReceiptIcon, Award, Percent, ChevronDown
} from 'lucide-react';
import { MonthlyReview, YearlyReview, AvailablePeriods, AIInsightItem } from '../types';
import { CategoryPieChart, DailySpendChart, MonthlySpendChart } from '../components/analytics/AnalyticsCharts';
import { RankedTable, RankedRow } from '../components/analytics/RankedTable';
import { KpiCard, ComparisonBadge } from '../components/analytics/KpiCard';
import { apiClient } from '../services/api';

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const InsightsList: React.FC<{ insights: AIInsightItem[] }> = ({ insights }) => {
  if (insights.length === 0) return null;
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-bold text-slate-200 flex items-center gap-1.5">
        <Sparkles className="w-4 h-4 text-cyan-400" />
        Insights
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {insights.map((insight, idx) => (
          <div key={idx} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2 hover:border-cyan-500/30 transition-all">
            <div className="flex items-center gap-2">
              {insight.type === 'warning' ? (
                <AlertCircle className="w-4 h-4 text-amber-400" />
              ) : insight.type === 'trend' ? (
                <TrendingUp className="w-4 h-4 text-cyan-400" />
              ) : (
                <ShoppingBag className="w-4 h-4 text-emerald-400" />
              )}
              <h3 className="font-bold text-xs text-white">{insight.title}</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{insight.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export const Analytics: React.FC = () => {
  const [viewMode, setViewMode] = useState<'monthly' | 'yearly'>('monthly');
  const [periods, setPeriods] = useState<AvailablePeriods | null>(null);
  const today = useMemo(() => new Date(), []);
  const [selectedYear, setSelectedYear] = useState(today.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(today.getMonth() + 1);

  const [monthly, setMonthly] = useState<MonthlyReview | null>(null);
  const [yearly, setYearly] = useState<YearlyReview | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiClient.get<AvailablePeriods>('/analytics/available-periods').then((res) => {
      setPeriods(res.data);
      if (res.data.years.length > 0 && !res.data.years.includes(today.getFullYear())) {
        setSelectedYear(res.data.years[0]);
        const months = res.data.months_by_year[res.data.years[0]];
        if (months && months.length > 0) setSelectedMonth(months[0]);
      }
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setIsLoading(true);
    const req = viewMode === 'monthly'
      ? apiClient.get<MonthlyReview>('/analytics/monthly', { params: { year: selectedYear, month: selectedMonth } }).then((r) => setMonthly(r.data))
      : apiClient.get<YearlyReview>('/analytics/yearly', { params: { year: selectedYear } }).then((r) => setYearly(r.data));
    req.catch((err) => console.error('Failed to load analytics:', err)).finally(() => setIsLoading(false));
  }, [viewMode, selectedYear, selectedMonth]);

  const availableYears = useMemo(() => {
    const dataYears = periods?.years || [];
    const minYear = Math.min(today.getFullYear() - 5, ...(dataYears.length ? dataYears : [today.getFullYear()]));
    const maxYear = Math.max(today.getFullYear() + 1, ...(dataYears.length ? dataYears : [today.getFullYear()]));
    const years: number[] = [];
    for (let y = maxYear; y >= minYear; y--) years.push(y);
    return years;
  }, [periods, today]);

  // The user can pick ANY month of ANY year — data availability only adds a
  // small "•" hint next to periods that actually have receipts.
  const ALL_MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);
  const monthsWithData = new Set(periods?.months_by_year[selectedYear] || []);
  const yearsWithData = new Set(periods?.years || []);

  const fmtMoney = (n: number) => `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Spending Analytics</h1>
          <p className="text-xs text-slate-400 mt-1">Monthly and yearly reviews calculated directly from your receipt database</p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Period Pickers */}
          {viewMode === 'monthly' && (
            <div className="relative">
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                className="appearance-none bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-200 rounded-xl pl-3 pr-8 py-2.5 focus:outline-none focus:border-cyan-500"
              >
                {ALL_MONTHS.map((m) => (
                  <option key={m} value={m}>{MONTH_NAMES[m - 1]}{monthsWithData.has(m) ? ' •' : ''}</option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          )}
          <div className="relative">
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="appearance-none bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-200 rounded-xl pl-3 pr-8 py-2.5 focus:outline-none focus:border-cyan-500"
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>{y}{yearsWithData.has(y) ? ' •' : ''}</option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Timeframe Toggle */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs font-semibold">
            <button
              onClick={() => setViewMode('monthly')}
              className={`px-4 py-2 rounded-lg transition-all ${viewMode === 'monthly' ? 'bg-cyan-500 text-slate-950 font-bold shadow-md' : 'text-slate-400 hover:text-white'}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setViewMode('yearly')}
              className={`px-4 py-2 rounded-lg transition-all ${viewMode === 'yearly' ? 'bg-cyan-500 text-slate-950 font-bold shadow-md' : 'text-slate-400 hover:text-white'}`}
            >
              Yearly
            </button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-slate-500 text-xs gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
          Calculating spending metrics...
        </div>
      ) : viewMode === 'monthly' && monthly ? (
        !monthly.has_data ? (
          <EmptyPeriod label={monthly.month_name} />
        ) : (
          <div className="space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <KpiCard label="Total Spending" value={fmtMoney(monthly.total_spending)} icon={<DollarSign className="w-4 h-4" />} iconBg="bg-cyan-500/10" iconColor="text-cyan-400"
                sublabel={monthly.spending_comparison ? undefined : monthly.month_name} />
              <KpiCard label="Receipts" value={String(monthly.total_receipts)} icon={<ReceiptIcon className="w-4 h-4" />} iconBg="bg-blue-500/10" iconColor="text-blue-400" sublabel={monthly.month_name} />
              <KpiCard label="Average Purchase" value={fmtMoney(monthly.avg_purchase)} icon={<TrendingUp className="w-4 h-4" />} iconBg="bg-purple-500/10" iconColor="text-purple-400" />
              <KpiCard label="Highest Purchase" value={fmtMoney(monthly.highest_purchase)} icon={<Award className="w-4 h-4" />} iconBg="bg-amber-500/10" iconColor="text-amber-400"
                sublabel={monthly.highest_purchase_merchant || undefined} />
            </div>

            {(monthly.spending_comparison || monthly.receipts_comparison) && (
              <div className="flex flex-wrap items-center gap-3">
                {monthly.spending_comparison && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    Spending vs {monthly.spending_comparison.label}: <ComparisonBadge changePct={monthly.spending_comparison.change_pct} suffix={`(₹${monthly.spending_comparison.previous.toLocaleString('en-IN')})`} />
                  </div>
                )}
                {monthly.receipts_comparison && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    Receipts vs {monthly.receipts_comparison.label}: <ComparisonBadge changePct={monthly.receipts_comparison.change_pct} suffix={`(${monthly.receipts_comparison.previous})`} />
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
                <h3 className="text-sm font-bold text-slate-200">Daily Spending — {monthly.month_name}</h3>
                <DailySpendChart points={monthly.daily_trend} />
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
                <h3 className="text-sm font-bold text-slate-200">Category Distribution</h3>
                <CategoryPieChart categories={monthly.categories} />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <RankedTable
                title="By Category" icon={<Tag className="w-4 h-4 text-cyan-400" />}
                rows={monthly.categories.map((c): RankedRow => ({ label: c.category, amount: c.amount, meta: `${c.count} receipt(s) · ${c.percentage}%` }))}
              />
              <RankedTable
                title="By Store" icon={<Building2 className="w-4 h-4 text-cyan-400" />}
                rows={monthly.stores.map((s): RankedRow => ({ label: s.merchant, amount: s.amount, meta: `${s.count} receipt(s)` }))}
              />
              <RankedTable
                title="Top Items" icon={<ShoppingBag className="w-4 h-4 text-cyan-400" />}
                rows={monthly.top_items.map((it): RankedRow => ({ label: it.product_name, amount: it.total_amount, meta: `${it.purchase_count}x · ${it.total_quantity} unit(s) · avg ₹${it.avg_price}` }))}
                emptyText="No line items recorded this month."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center"><Percent className="w-4 h-4" /></div>
                  <span className="text-xs font-semibold text-slate-400">Total Tax Paid</span>
                </div>
                <span className="text-lg font-extrabold text-white">{fmtMoney(monthly.total_tax)}</span>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center"><Percent className="w-4 h-4" /></div>
                  <span className="text-xs font-semibold text-slate-400">Total Discount Received</span>
                </div>
                <span className="text-lg font-extrabold text-white">{fmtMoney(monthly.total_discount)}</span>
              </div>
            </div>

            <InsightsList insights={monthly.insights} />
          </div>
        )
      ) : viewMode === 'yearly' && yearly ? (
        !yearly.has_data ? (
          <EmptyPeriod label={String(yearly.year)} />
        ) : (
          <div className="space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              <KpiCard label="Total Spending" value={fmtMoney(yearly.total_spending)} icon={<DollarSign className="w-4 h-4" />} iconBg="bg-cyan-500/10" iconColor="text-cyan-400" sublabel={String(yearly.year)} />
              <KpiCard label="Receipts" value={String(yearly.total_receipts)} icon={<ReceiptIcon className="w-4 h-4" />} iconBg="bg-blue-500/10" iconColor="text-blue-400" />
              <KpiCard label="Average Purchase" value={fmtMoney(yearly.avg_purchase)} icon={<TrendingUp className="w-4 h-4" />} iconBg="bg-purple-500/10" iconColor="text-purple-400" />
              <KpiCard label="Highest Purchase" value={fmtMoney(yearly.highest_purchase)} icon={<Award className="w-4 h-4" />} iconBg="bg-amber-500/10" iconColor="text-amber-400" />
            </div>

            <div className="flex flex-wrap items-center gap-4">
              {yearly.spending_comparison && (
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  Spending vs {yearly.spending_comparison.label}: <ComparisonBadge changePct={yearly.spending_comparison.change_pct} suffix={`(₹${yearly.spending_comparison.previous.toLocaleString('en-IN')})`} />
                </div>
              )}
              {yearly.highest_spending_month && (
                <span className="text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg">
                  Peak: {yearly.highest_spending_month}
                </span>
              )}
              {yearly.lowest_spending_month && (
                <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg">
                  Lowest: {yearly.lowest_spending_month}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
                <h3 className="text-sm font-bold text-slate-200">Monthly Trend — {yearly.year}</h3>
                <MonthlySpendChart points={yearly.monthly_trend} />
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
                <h3 className="text-sm font-bold text-slate-200">Category Distribution</h3>
                <CategoryPieChart categories={yearly.categories} />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <RankedTable
                title="By Category" icon={<Tag className="w-4 h-4 text-cyan-400" />}
                rows={yearly.categories.map((c): RankedRow => ({ label: c.category, amount: c.amount, meta: `${c.count} receipt(s) · ${c.percentage}%` }))}
              />
              <RankedTable
                title="By Store" icon={<Building2 className="w-4 h-4 text-cyan-400" />}
                rows={yearly.stores.map((s): RankedRow => ({ label: s.merchant, amount: s.amount, meta: `${s.count} receipt(s)` }))}
              />
              <RankedTable
                title="Top Items" icon={<ShoppingBag className="w-4 h-4 text-cyan-400" />}
                rows={yearly.top_items.map((it): RankedRow => ({ label: it.product_name, amount: it.total_amount, meta: `${it.purchase_count}x · avg ₹${it.avg_price}` }))}
                emptyText="No line items recorded this year."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center"><Percent className="w-4 h-4" /></div>
                  <span className="text-xs font-semibold text-slate-400">Total Tax Paid</span>
                </div>
                <span className="text-lg font-extrabold text-white">{fmtMoney(yearly.total_tax)}</span>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center"><Percent className="w-4 h-4" /></div>
                  <span className="text-xs font-semibold text-slate-400">Total Discount Received</span>
                </div>
                <span className="text-lg font-extrabold text-white">{fmtMoney(yearly.total_discount)}</span>
              </div>
            </div>

            <InsightsList insights={yearly.insights} />
          </div>
        )
      ) : null}
    </div>
  );
};

const EmptyPeriod: React.FC<{ label: string }> = ({ label }) => (
  <div className="bg-slate-900/60 border border-dashed border-slate-800 rounded-3xl p-14 text-center space-y-2">
    <ReceiptIcon className="w-10 h-10 text-slate-600 mx-auto" />
    <p className="text-sm font-semibold text-slate-300">No purchases for {label}</p>
    <p className="text-xs text-slate-500 max-w-xs mx-auto">
      Nothing to show yet — pick a different month or year above, or upload a receipt dated within this period.
    </p>
  </div>
);
