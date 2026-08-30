import React, { useState, useRef } from 'react';
import { Upload, X, FileText, Image as ImageIcon, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { apiClient } from '../../services/api';

interface ReceiptUploaderProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

export const ReceiptUploader: React.FC<ReceiptUploaderProps> = ({ isOpen, onClose, onUploadSuccess }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      validateAndSetFiles(filesArray);
    }
  };

  const validateAndSetFiles = (files: File[]) => {
    setErrorMsg(null);
    const valid: File[] = [];
    const allowed = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];

    for (const f of files) {
      if (!allowed.includes(f.type) && !f.name.match(/\.(jpg|jpeg|png|pdf)$/i)) {
        setErrorMsg(`Unsupported file type '${f.name}'. Allowed: JPG, PNG, PDF.`);
        return;
      }
      if (f.size > 15 * 1024 * 1024) {
        setErrorMsg(`File '${f.name}' exceeds 15MB limit.`);
        return;
      }
      valid.push(f);
    }
    setSelectedFiles((prev) => [...prev, ...valid]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      validateAndSetFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadSubmit = async () => {
    if (selectedFiles.length === 0) return;
    setIsUploading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append('files', file);
    });

    try {
      await apiClient.post('/receipts/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSuccessMsg(`Successfully uploaded ${selectedFiles.length} receipt(s)! Background OCR and indexing active.`);
      setSelectedFiles([]);
      setTimeout(() => {
        onUploadSuccess();
        onClose();
        setSuccessMsg(null);
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to upload receipts. Please check server logs.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Upload className="w-5 h-5 text-cyan-400" />
            Upload Receipts & Invoices
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Upload images or PDFs (JPG, PNG, PDF up to 15MB). OCR and JSON extraction will execute automatically.
          </p>
        </div>

        {/* Drag & Drop Zone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-800 hover:border-cyan-500/50 bg-slate-950/50 hover:bg-slate-950 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all group"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            accept=".jpg,.jpeg,.png,.pdf"
            className="hidden"
          />
          <div className="w-12 h-12 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
            <Upload className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-slate-200">
            Click to browse or drag and drop receipts here
          </p>
          <p className="text-xs text-slate-500 mt-1">Supports JPG, PNG, PDF</p>
        </div>

        {/* Error / Success Notifications */}
        {errorMsg && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Selected File List */}
        {selectedFiles.length > 0 && (
          <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
            <p className="text-xs font-semibold text-slate-400">Selected Files ({selectedFiles.length}):</p>
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs"
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  {file.name.endsWith('.pdf') ? (
                    <FileText className="w-4 h-4 text-rose-400 shrink-0" />
                  ) : (
                    <ImageIcon className="w-4 h-4 text-cyan-400 shrink-0" />
                  )}
                  <span className="text-slate-200 font-medium truncate">{file.name}</span>
                  <span className="text-slate-500">({(file.size / 1024).toFixed(1)} KB)</span>
                </div>
                <button
                  onClick={() => handleRemoveFile(idx)}
                  className="text-slate-500 hover:text-rose-400 p-1 rounded-lg"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-slate-800 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-all"
          >
            Cancel
          </button>
          <button
            onClick={handleUploadSubmit}
            disabled={selectedFiles.length === 0 || isUploading}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs shadow-lg shadow-cyan-500/25 disabled:opacity-50 transition-all"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing Upload...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Start Processing ({selectedFiles.length})
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
