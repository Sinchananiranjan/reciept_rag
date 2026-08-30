import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, Receipt, Building2, Calendar, Tag } from 'lucide-react';
import { SourceCitation } from '../../types';

interface SourceCardProps {
  source: SourceCitation;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source }) => {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/receipts/${source.receipt_id}`)}
      className="bg-slate-900/90 border border-cyan-500/20 hover:border-cyan-500/50 rounded-xl p-3 hover:bg-slate-800 transition-all cursor-pointer group shadow-sm"
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 overflow-hidden">
          <Building2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span className="font-semibold text-xs text-slate-100 group-hover:text-cyan-400 transition-colors truncate">
            {source.merchant_name}
          </span>
        </div>
        <span className="font-bold text-xs text-emerald-400">
          ₹{source.total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
        </span>
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3 text-slate-500" />
            {source.receipt_date}
          </span>
          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
            {source.category}
          </span>
        </div>
        <span className="text-cyan-400 flex items-center gap-0.5 group-hover:translate-x-0.5 transition-transform">
          Open <ExternalLink className="w-3 h-3" />
        </span>
      </div>
    </div>
  );
};
