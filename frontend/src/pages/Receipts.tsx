import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, Filter, Upload, Receipt as ReceiptIcon, Loader2, RefreshCw, Edit3 } from 'lucide-react';
import { Receipt } from '../types';
import { ReceiptCard } from '../components/receipts/ReceiptCard';
import { ManualReceiptModal } from '../components/receipts/ManualReceiptModal';
import { apiClient } from '../services/api';
import { useDataRefresh } from '../context/DataRefreshContext';
import { useProcessingPoll } from '../hooks/useProcessingPoll';

interface ReceiptsProps {
  onOpenUploadModal: () => void;
}

export const Receipts: React.FC<ReceiptsProps> = ({ onOpenUploadModal }) => {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [searchParams] = useSearchParams();
  const { refreshToken, notifyDataChanged } = useDataRefresh();

  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);

  const categories = [
    "Groceries",
    "Food",
    "Electronics",
    "Clothing",
    "Travel",
    "Healthcare",
    "Entertainment",
    "Utilities",
    "Shopping",
    "Fuel",
    "Other"
  ];

  const fetchReceipts = async () => {
    setIsLoading((prev) => (receipts.length === 0 ? true : prev));
    try {
      let url = '/receipts';
      if (selectedCategory) {
        url += `?category=${encodeURIComponent(selectedCategory)}`;
      }
      const res = await apiClient.get<Receipt[]>(url);
      setReceipts(res.data);
    } catch (err) {
      console.error('Error fetching receipts:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReceipts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory, refreshToken]);

  // Once a receipt appears, keep polling quietly until OCR/extraction/indexing
  // finishes, so the card's status and data update without a manual refresh.
  useProcessingPoll(receipts, fetchReceipts);

  const handleDeleteReceipt = async (id: number) => {
    if (!window.confirm(`Are you sure you want to delete receipt #${id}?`)) return;
    try {
      await apiClient.delete(`/receipts/${id}`);
      setReceipts((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      alert('Failed to delete receipt.');
    }
  };

  // Client-side filtering
  const filteredReceipts = receipts.filter((r) => {
    if (selectedStatus && r.processing_status !== selectedStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const m = (r.merchant_name || '').toLowerCase();
      const c = (r.category || '').toLowerCase();
      const fn = (r.original_filename || '').toLowerCase();
      const t = (r.total || 0).toString();
      return m.includes(q) || c.includes(q) || fn.includes(q) || t.includes(q);
    }
    return true;
  });

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Receipts Library</h1>
          <p className="text-xs text-slate-400 mt-1">Manage, edit, and reprocess uploaded receipts and invoices</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsManualModalOpen(true)}
            className="flex items-center gap-2 bg-slate-900 border border-slate-800 hover:border-cyan-500/40 text-slate-200 font-semibold text-xs py-2.5 px-4 rounded-xl transition-all"
          >
            <Edit3 className="w-4 h-4 text-cyan-400" /> Enter Receipt Manually
          </button>
          <button
            onClick={onOpenUploadModal}
            className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 text-white font-semibold text-xs py-2.5 px-4 rounded-xl shadow-lg shadow-cyan-500/25 transition-all"
          >
            <Upload className="w-4 h-4" /> Upload Receipt
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by store, file name, or total amount..."
            className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none transition-all"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-500 shrink-0" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-xl px-3 py-2.5 focus:outline-none focus:border-cyan-500 w-full md:w-auto"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-xl px-3 py-2.5 focus:outline-none focus:border-cyan-500 w-full md:w-auto"
          >
            <option value="">All Statuses</option>
            <option value="COMPLETED">Ready</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="PROCESSING">Processing</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
          </select>

          <button
            onClick={fetchReceipts}
            className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/30 transition-all shrink-0"
            title="Refresh list"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Receipt Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-slate-500 text-xs gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
          Loading receipts...
        </div>
      ) : filteredReceipts.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-12 text-center space-y-3">
          <ReceiptIcon className="w-10 h-10 text-slate-600 mx-auto" />
          <p className="text-sm font-semibold text-slate-300">No receipts found</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Upload a receipt image/PDF or create a receipt manually to start building your library.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredReceipts.map((receipt) => (
            <ReceiptCard key={receipt.id} receipt={receipt} onDelete={handleDeleteReceipt} />
          ))}
        </div>
      )}

      <ManualReceiptModal
        isOpen={isManualModalOpen}
        onClose={() => setIsManualModalOpen(false)}
        onSuccess={() => {
          notifyDataChanged();
          fetchReceipts();
        }}
      />
    </div>
  );
};
