import React from 'react';

export interface RankedRow {
  label: string;
  amount: number;
  meta?: string;
}

interface RankedTableProps {
  title: string;
  icon?: React.ReactNode;
  rows: RankedRow[];
  emptyText?: string;
  badge?: string;
}

/** A small ranked list/table (category, store, or item breakdown) shared by
 * the Monthly and Yearly Review pages — avoids re-implementing the same
 * table markup four times across the two views. */
export const RankedTable: React.FC<RankedTableProps> = ({ title, icon, rows, emptyText = 'No data for this period.', badge }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          {icon}
          {title}
        </h3>
        {badge && (
          <span className="text-[11px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg">
            {badge}
          </span>
        )}
      </div>

      {rows.length === 0 ? (
        <p className="text-xs text-slate-500 italic py-3 text-center">{emptyText}</p>
      ) : (
        <div className="space-y-1">
          {rows.map((row, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b border-slate-800/60 last:border-0">
              <div className="min-w-0 flex-1 pr-3">
                <p className="text-xs font-semibold text-slate-200 truncate">{row.label}</p>
                {row.meta && <p className="text-[11px] text-slate-500">{row.meta}</p>}
              </div>
              <p className="text-xs font-extrabold text-cyan-400 shrink-0">
                ₹{row.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
