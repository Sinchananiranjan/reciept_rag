import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  DollarSign,
  Receipt as ReceiptIcon,
  TrendingUp,
  Award,
  ArrowRight,
  Loader2,
  LayoutGrid
} from 'lucide-react';
import { Receipt, AnalyticsOverview } from '../types';
import { ReceiptCard } from '../components/receipts/ReceiptCard';
import { apiClient } from '../services/api';
import { useDataRefresh } from '../context/DataRefreshContext';
import { useProcessingPoll } from '../hooks/useProcessingPoll';

export const Dashboard: React.FC = () => {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { refreshToken } = useDataRefresh();

  const navigate = useNavigate();

  const fetchDashboardData = async () => {
    setIsLoading((prev) => (receipts.length === 0 ? true : prev));
    try {
      const [rRes, aRes] = await Promise.all([
        apiClient.get<Receipt[]>('/receipts'),
        apiClient.get<AnalyticsOverview>('/analytics/overview')
      ]);
      setReceipts(rRes.data);
      setAnalytics(aRes.data);
    } catch (err) {
      console.error('Error loading dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshToken]);

  // Keep the dashboard current while a freshly uploaded receipt is still
  // being OCR'd/extracted/indexed in the background.
  useProcessingPoll(receipts, fetchDashboardData);

  const summary = analytics?.summary;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Hero Banner — informational only; Upload lives in the header, Enter Manually
          lives on the Receipts Library page, so there's exactly one home for each action. */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-cyan-950 via-slate-900 to-slate-950 border border-cyan-500/20 p-8 shadow-2xl">
        <div className="relative z-10 max-w-2xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            Universal AI Document Intelligence
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Your Receipts, Searchable with <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">AI Precision</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Every receipt you upload is OCR'd, structured, and indexed into a grounded RAG vector store —
            ask a question in plain English and get an answer backed by your real purchase data.
          </p>
          {summary && summary.total_receipts > 0 && (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-1 pt-1 text-xs text-slate-400">
              <span><span className="text-slate-100 font-bold">₹{summary.total_spending.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span> tracked</span>
              <span className="w-1 h-1 rounded-full bg-slate-700" />
              <span><span className="text-slate-100 font-bold">{summary.total_receipts}</span> receipt{summary.total_receipts === 1 ? '' : 's'}</span>
              <span className="w-1 h-1 rounded-full bg-slate-700" />
              <span>This month: <span className="text-slate-100 font-bold">₹{summary.current_month_spending.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></span>
            </div>
          )}
        </div>
      </div>

      {/* KPI Stats Cards */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-slate-500 text-xs gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
          Loading spending stats...
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Total Recorded Spending</span>
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-extrabold text-white tracking-tight">
              ₹{(summary?.total_spending || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </p>
            <p className="text-[11px] text-slate-500">Across all processed receipts</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Total Receipts</span>
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
                <ReceiptIcon className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-extrabold text-white tracking-tight">{summary?.total_receipts || 0}</p>
            <p className="text-[11px] text-slate-500">Indexed in vector store</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Average Purchase</span>
              <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-extrabold text-white tracking-tight">
              ₹{(summary?.avg_receipt_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </p>
            <p className="text-[11px] text-slate-500">Average receipt value</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Highest Purchase</span>
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
                <Award className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-extrabold text-white tracking-tight">
              ₹{(summary?.highest_purchase || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </p>
            <p className="text-[11px] text-slate-500">Single max transaction</p>
          </div>
        </div>
      )}

      {/* Recent Receipts Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white tracking-tight">Recent Receipts</h2>
          {receipts.length > 0 && (
            <button
              onClick={() => navigate('/receipts')}
              className="text-xs text-cyan-400 hover:underline font-semibold flex items-center gap-1"
            >
              View All ({receipts.length}) <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {receipts.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-12 text-center space-y-4">
            <ReceiptIcon className="w-12 h-12 text-slate-600 mx-auto" />
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-200">No receipts yet.</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Use the Upload Receipts button in the header, or head to the Receipts Library to add one manually.
              </p>
            </div>
            <button
              onClick={() => navigate('/receipts')}
              className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-xs py-2.5 px-4 rounded-xl transition-all"
            >
              <LayoutGrid className="w-4 h-4 text-cyan-400" /> Go to Receipts Library
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {receipts.slice(0, 6).map((receipt) => (
              <ReceiptCard key={receipt.id} receipt={receipt} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
