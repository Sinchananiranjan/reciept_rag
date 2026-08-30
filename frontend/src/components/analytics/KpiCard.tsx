import React from 'react';

interface KpiCardProps {
  label: string;
  value: string;
  sublabel?: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
}

/** A single stat card — total spending, receipt count, average, highest, etc.
 * Shared by the Monthly and Yearly Review pages (and could back the Dashboard
 * KPIs too) so the four-card grid isn't reimplemented per page. */
export const KpiCard: React.FC<KpiCardProps> = ({ label, value, sublabel, icon, iconBg, iconColor }) => (
  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
    <div className="flex items-center justify-between">
      <span className="text-xs font-semibold text-slate-400">{label}</span>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconBg} ${iconColor}`}>
        {icon}
      </div>
    </div>
    <p className="text-2xl font-extrabold text-white tracking-tight">{value}</p>
    {sublabel && <p className="text-[11px] text-slate-500">{sublabel}</p>}
  </div>
);

interface ComparisonBadgeProps {
  changePct?: number | null;
  suffix?: string;
}

/** "+12.4% vs July 2026" style badge, colored green when spending went down
 * (good) and amber when it went up — used next to comparison stats. */
export const ComparisonBadge: React.FC<ComparisonBadgeProps> = ({ changePct, suffix }) => {
  if (changePct === null || changePct === undefined) return null;
  const isUp = changePct >= 0;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-lg border ${
        isUp ? 'text-amber-400 bg-amber-500/10 border-amber-500/20' : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      }`}
    >
      {isUp ? '▲' : '▼'} {Math.abs(changePct)}% {suffix}
    </span>
  );
};
