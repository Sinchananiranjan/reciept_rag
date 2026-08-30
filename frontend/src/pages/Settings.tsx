import React from 'react';
import { User, Cpu, Database, FileText, CheckCircle2, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Settings: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-extrabold text-white tracking-tight">System Settings & Architecture</h1>
        <p className="text-xs text-slate-400 mt-1">ReceiptRAG system details and active modular service engines</p>
      </div>

      {/* Profile Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <User className="w-4 h-4 text-cyan-400" />
          User Profile Account
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-slate-400 block">Full Name</span>
            <span className="font-semibold text-slate-200">{user?.full_name || 'N/A'}</span>
          </div>
          <div>
            <span className="text-slate-400 block">Email Address</span>
            <span className="font-semibold text-slate-200">{user?.email}</span>
          </div>
          <div>
            <span className="text-slate-400 block">Account ID</span>
            <span className="font-mono text-slate-200">User #{user?.id}</span>
          </div>
          <div>
            <span className="text-slate-400 block">Data Isolation Scope</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Enforced Multi-Tenant Scope
            </span>
          </div>
        </div>
      </div>

      {/* Engine Status Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          Active Service Engine Architecture
        </h2>

        <div className="space-y-3 text-xs">
          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800/80 flex items-center justify-between">
            <div className="space-y-1">
              <span className="font-bold text-slate-200 flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-400" />
                Vector Database
              </span>
              <p className="text-slate-400">ChromaDB Persistent Embedded Store (Extensible for pgvector)</p>
            </div>
            <span className="flex items-center gap-1 text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-lg">
              <CheckCircle2 className="w-3.5 h-3.5" /> Active
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800/80 flex items-center justify-between">
            <div className="space-y-1">
              <span className="font-bold text-slate-200 flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                OCR Extraction Engine
              </span>
              <p className="text-slate-400">PyTesseract + OpenCV Preprocessing (Grayscale, Denoise, Deskew)</p>
            </div>
            <span className="flex items-center gap-1 text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-lg">
              <CheckCircle2 className="w-3.5 h-3.5" /> Active
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800/80 flex items-center justify-between">
            <div className="space-y-1">
              <span className="font-bold text-slate-200 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                Structured LLM Extraction & RAG Pipeline
              </span>
              <p className="text-slate-400">OpenAI API Compatibility + Local Heuristic Extraction Fallback</p>
            </div>
            <span className="flex items-center gap-1 text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-lg">
              <CheckCircle2 className="w-3.5 h-3.5" /> Active
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
