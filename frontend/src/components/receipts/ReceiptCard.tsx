import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  AlertTriangle,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Trash2,
  Building2,
  Tag,
  HelpCircle
} from 'lucide-react';
import { Receipt } from '../../types';

interface ReceiptCardProps {
  receipt: Receipt;
  onDelete?: (id: number) => void;
}

export const ReceiptCard: React.FC<ReceiptCardProps> = ({ receipt, onDelete }) => {
  const navigate = useNavigate();

  const getCurrencySymbol = (code?: string) => {
    switch (code) {
      case 'USD': return '$';
      case 'EUR': return '€';
      case 'GBP': return '£';
      default: return '₹';
    }
  };

  const getStatusBadge = () => {
    switch (receipt.processing_status) {
      case 'COMPLETED':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-semibold">
            <CheckCircle2 className="w-3 h-3" />
            Ready
          </span>
        );
      case 'NEEDS_REVIEW':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-semibold">
            <HelpCircle className="w-3 h-3" />
            Needs Review
          </span>
        );
      case 'PROCESSING':
      case 'OCR_PROCESSING':
      case 'EXTRACTING':
      case 'VALIDATING':
      case 'INDEXING':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[11px] font-semibold animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" />
            Processing
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[11px] font-semibold">
            <XCircle className="w-3 h-3" />
            Failed
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 border border-slate-700 text-slate-400 text-[11px] font-semibold">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        );
    }
  };

  const symbol = getCurrencySymbol(receipt.currency);

  return (
    <div
      onClick={() => navigate(`/receipts/${receipt.id}`)}
      className="group bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 hover:shadow-xl hover:shadow-cyan-500/5 transition-all cursor-pointer flex flex-col justify-between relative overflow-hidden"
    >
      {/* Top Banner: Duplicate Alert / Status */}
      <div className="flex items-center justify-between gap-2 mb-4">
        {receipt.is_duplicate ? (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-bold uppercase tracking-wider">
            <AlertTriangle className="w-3 h-3" />
            Possible Duplicate
          </span>
        ) : (
          <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-400 text-[11px] font-medium flex items-center gap-1">
            <Tag className="w-3 h-3 text-cyan-400" />
            {receipt.category || 'Other'}
          </span>
        )}
        {getStatusBadge()}
      </div>

      {/* Main Content */}
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="overflow-hidden">
            <h3 className="font-bold text-base text-slate-100 group-hover:text-cyan-400 transition-colors truncate flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
              {receipt.merchant_name || 'Receipt Record'}
            </h3>
            <p className="text-xs text-slate-500 truncate mt-0.5">{receipt.original_filename}</p>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-800/80 pt-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span>{receipt.receipt_date || 'Date N/A'}</span>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-500 block">Total</span>
            <span className="font-extrabold text-base text-white tracking-tight">
              {symbol}{(receipt.total || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Footer Actions */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
        <span className="text-cyan-400 font-semibold group-hover:underline">
          View Receipt Details &rarr;
        </span>
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(receipt.id);
            }}
            className="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all"
            title="Delete Receipt"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
