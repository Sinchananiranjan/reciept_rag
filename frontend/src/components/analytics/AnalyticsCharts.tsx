import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  CartesianGrid
} from 'recharts';
import { AnalyticsOverview, CategoryBreakdownItem, DailyTrendPoint, MonthTrendPoint } from '../../types';

interface AnalyticsChartsProps {
  analytics: AnalyticsOverview;
}

export const COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#64748b'];

const tooltipStyle = { backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', fontSize: '12px' };

/** Reusable category pie chart — used by both the Monthly and Yearly Review pages. */
export const CategoryPieChart: React.FC<{ categories: CategoryBreakdownItem[]; height?: number }> = ({ categories, height = 260 }) => {
  if (categories.length === 0) {
    return <div style={{ height }} className="flex items-center justify-center text-xs text-slate-500">No category data for this period.</div>;
  }
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={categories}
            dataKey="amount"
            nameKey="category"
            cx="50%"
            cy="50%"
            outerRadius={80}
            innerRadius={45}
            paddingAngle={4}
            label={({ name, percent }: any) => `${name} (${(percent * 100).toFixed(0)}%)`}
            labelLine={false}
          >
            {categories.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} formatter={(val: any) => [`₹${Number(val).toFixed(2)}`, 'Total']} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

/** Day-by-day spending line chart within a single month (Monthly Review). */
export const DailySpendChart: React.FC<{ points: DailyTrendPoint[]; height?: number }> = ({ points, height = 260 }) => {
  const hasSpend = points.some((p) => p.amount > 0);
  if (!hasSpend) {
    return <div style={{ height }} className="flex items-center justify-center text-xs text-slate-500">No daily spending recorded.</div>;
  }
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis dataKey="day" stroke="#64748b" fontSize={11} tickLine={false} />
          <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `₹${v}`} tickLine={false} />
          <Tooltip
            contentStyle={tooltipStyle}
            labelFormatter={(d) => `Day ${d}`}
            formatter={(val: any) => [`₹${Number(val).toFixed(2)}`, 'Spent']}
          />
          <Line type="monotone" dataKey="amount" stroke="#06b6d4" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

/** Month-by-month spending bar chart across a year (Yearly Review). */
export const MonthlySpendChart: React.FC<{ points: MonthTrendPoint[]; height?: number }> = ({ points, height = 260 }) => {
  const hasSpend = points.some((p) => p.amount > 0);
  if (!hasSpend) {
    return <div style={{ height }} className="flex items-center justify-center text-xs text-slate-500">No spending recorded this year.</div>;
  }
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points}>
          <XAxis dataKey="month_name" stroke="#64748b" fontSize={11} tickLine={false} />
          <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `₹${v}`} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle} formatter={(val: any) => [`₹${Number(val).toFixed(2)}`, 'Spent']} />
          <Bar dataKey="amount" fill="#06b6d4" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ analytics }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 1. Monthly Spending Trend Bar Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-200">Monthly Spending Trends</h3>
        <div className="h-64 w-full">
          {analytics.monthly_analytics.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.monthly_analytics}>
                <XAxis dataKey="month_name" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `₹${v}`} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(val: any) => [`₹${Number(val).toFixed(2)}`, 'Spent']}
                />
                <Bar dataKey="amount" fill="#06b6d4" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500">No monthly data available yet.</div>
          )}
        </div>
      </div>

      {/* 2. Category Distribution Pie Chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-200">Category Expense Distribution</h3>
        <CategoryPieChart categories={analytics.categories} height={256} />
      </div>
    </div>
  );
};
