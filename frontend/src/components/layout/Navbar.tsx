import React from 'react';
import { Search, Upload, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface NavbarProps {
  onOpenUploadModal: () => void;
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenUploadModal,
  searchQuery = '',
  onSearchChange,
}) => {
  const navigate = useNavigate();

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/receipts?search=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Global Search Bar */}
      <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange?.(e.target.value)}
            placeholder="Search receipts by store, amount (e.g. ₹500), category, or item..."
            className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-all"
          />
        </div>
      </form>

      {/* Action Buttons & Status Badge */}
      <div className="flex items-center gap-4">
        <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          RAG Engine Ready
        </div>

        <button
          onClick={onOpenUploadModal}
          className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs py-2 px-4 rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <Upload className="w-4 h-4" />
          Upload Receipts
        </button>
      </div>
    </header>
  );
};
