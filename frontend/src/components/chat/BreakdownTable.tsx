import React from 'react';
import { ChatBreakdownTable } from '../../types';

interface BreakdownTableProps {
  breakdown: ChatBreakdownTable;
}

/** Renders the verified numeric breakdown that backs a structured chat
 * answer (e.g. per-product or per-category totals) as an actual table,
 * rather than as a markdown blob buried in chat text. */
export const BreakdownTable: React.FC<BreakdownTableProps> = ({ breakdown }) => {
  if (!breakdown.rows.length) return null;

  return (
    <div className="pt-3 border-t border-slate-800 space-y-2">
      <p className="text-[11px] font-bold text-cyan-400">{breakdown.title}</p>
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-left text-[11px]">
          <thead>
            <tr className="bg-slate-950/80 text-slate-400 font-semibold">
              {breakdown.columns.map((col, i) => (
                <th key={i} className={`px-3 py-2 ${i === 0 ? '' : 'text-right'}`}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {breakdown.rows.map((row, ri) => (
              <tr key={ri} className="text-slate-200">
                {row.map((cell, ci) => (
                  <td key={ci} className={`px-3 py-2 ${ci === 0 ? 'font-medium text-slate-100' : 'text-right tabular-nums'}`}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
