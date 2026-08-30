import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  RefreshCw,
  Trash2,
  AlertTriangle,
  FileText,
  Building2,
  Plus,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import { Receipt, ReceiptItem } from '../types';
import { apiClient } from '../services/api';
import { useDataRefresh } from '../context/DataRefreshContext';

export const ReceiptDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { notifyDataChanged } = useDataRefresh();

  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Form State
  const [merchantName, setMerchantName] = useState('');
  const [receiptDate, setReceiptDate] = useState('');
  const [subtotal, setSubtotal] = useState<number | ''>('');
  const [tax, setTax] = useState<number | ''>('');
  const [discount, setDiscount] = useState<number | ''>('');
  const [total, setTotal] = useState<number | ''>('');
  const [category, setCategory] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [items, setItems] = useState<ReceiptItem[]>([]);
  const [previewFailed, setPreviewFailed] = useState(false);

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

  useEffect(() => {
    fetchReceiptDetails();
  }, [id]);

  const fetchReceiptDetails = async () => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<Receipt>(`/receipts/${id}`);
      const r = res.data;
      setReceipt(r);
      setMerchantName(r.merchant_name || '');
      setReceiptDate(r.receipt_date || '');
      setSubtotal(r.subtotal ?? '');
      setTax(r.tax ?? '');
      setDiscount(r.discount ?? '');
      setTotal(r.total ?? '');
      setCategory(r.category || 'Other');
      setPaymentMethod(r.payment_method || 'UPI');
      setItems(r.items || []);
    } catch (err) {
      console.error('Error loading receipt details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const res = await apiClient.put<Receipt>(`/receipts/${id}`, {
        merchant_name: merchantName,
        receipt_date: receiptDate,
        subtotal: subtotal === '' ? null : Number(subtotal),
        tax: tax === '' ? null : Number(tax),
        discount: discount === '' ? null : Number(discount),
        total: total === '' ? null : Number(total),
        category,
        payment_method: paymentMethod,
        items: items,
      });
      setReceipt(res.data);
      setSaveSuccess(true);
      notifyDataChanged();
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      alert('Failed to save receipt updates.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReprocess = async () => {
    setIsReprocessing(true);
    try {
      await apiClient.post(`/receipts/${id}/reprocess`);
      notifyDataChanged();
      fetchReceiptDetails();
    } catch (err) {
      alert('Reprocess request failed.');
    } finally {
      setIsReprocessing(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this receipt?')) return;
    try {
      await apiClient.delete(`/receipts/${id}`);
      notifyDataChanged();
      navigate('/receipts');
    } catch (err) {
      alert('Failed to delete receipt.');
    }
  };

  const handleAddItem = () => {
    setItems((prev) => [
      ...prev,
      { product_name: 'New Product', quantity: 1.0, unit_price: 0, total_price: 0 },
    ]);
  };

  const handleItemChange = (index: number, field: keyof ReceiptItem, val: any) => {
    setItems((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: val };
      if (field === 'quantity' || field === 'unit_price') {
        const q = Number(updated[index].quantity) || 1;
        const p = Number(updated[index].unit_price) || 0;
        updated[index].total_price = q * p;
      }
      return updated;
    });
  };

  const handleRemoveItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh] text-slate-500 text-xs gap-2">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
        Loading receipt metadata...
      </div>
    );
  }

  if (!receipt) {
    return (
      <div className="p-8 text-center text-slate-400 space-y-4">
        <p>Receipt not found.</p>
        <button onClick={() => navigate('/receipts')} className="text-cyan-400 underline text-xs">
          Back to Receipts Library
        </button>
      </div>
    );
  }

  const fileBasename = receipt.file_path.split(/[\\/]/).pop() || '';
  const backendUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace('/api', '') : '';
  const fileUrl = `${backendUrl}/uploads/${fileBasename}`;
  const isPdf = receipt.original_filename.toLowerCase().endsWith('.pdf');
  const isManualEntry = receipt.entry_type === 'MANUAL';

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Header Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/receipts')}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
              Receipt #{receipt.id}
              <span className="text-xs text-slate-400 font-normal">({receipt.original_filename})</span>
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">Uploaded {new Date(receipt.upload_date).toLocaleString()}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!isManualEntry && (
            <button
              onClick={handleReprocess}
              disabled={isReprocessing}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 font-semibold text-xs transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isReprocessing ? 'animate-spin' : ''}`} />
              Reprocess OCR
            </button>
          )}

          <button
            onClick={handleDelete}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 font-semibold text-xs hover:bg-rose-500/20 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 text-white font-bold text-xs shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50"
          >
            {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            Save Changes
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
          <CheckCircle2 className="w-4 h-4" />
          <span>Receipt updated and vector embeddings refreshed successfully!</span>
        </div>
      )}

      {/* Discrepancy Banner */}
      {receipt.validation_notes && (
        <div className="flex items-center gap-2.5 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-medium">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          <span>{receipt.validation_notes}</span>
        </div>
      )}

      {/* Split Screen View — the preview column only makes sense for uploaded
          files; manually entered receipts have no source document. */}
      <div className={`grid grid-cols-1 ${isManualEntry ? '' : 'lg:grid-cols-12'} gap-8`}>
        {!isManualEntry && (
          <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-3xl p-4 flex flex-col items-center justify-center min-h-[500px] overflow-hidden">
            <p className="text-xs font-semibold text-slate-400 mb-3 self-start flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-cyan-400" />
              Original Document Preview
            </p>
            {previewFailed ? (
              <div className="flex-1 w-full flex flex-col items-center justify-center gap-2 text-slate-500 text-xs">
                <FileText className="w-8 h-8 text-slate-700" />
                Preview unavailable for this file.
              </div>
            ) : isPdf ? (
              <iframe
                src={fileUrl}
                className="w-full h-[550px] rounded-xl border border-slate-800"
                title="PDF Preview"
                onError={() => setPreviewFailed(true)}
              />
            ) : (
              <img
                src={fileUrl}
                alt="Receipt Preview"
                className="max-h-[550px] w-auto object-contain rounded-xl border border-slate-800 shadow-md"
                onError={() => setPreviewFailed(true)}
              />
            )}
          </div>
        )}

        {/* Structured Fields & Editor */}
        <div className={isManualEntry ? 'space-y-6' : 'lg:col-span-7 space-y-6'}>
          {/* Metadata Form */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Building2 className="w-4 h-4 text-cyan-400" />
              Extracted Structured Metadata
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">Merchant Store Name</label>
                <input
                  type="text"
                  value={merchantName}
                  onChange={(e) => setMerchantName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">Receipt Date</label>
                <input
                  type="text"
                  value={receiptDate}
                  onChange={(e) => setReceiptDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-white"
                >
                  {categories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">Payment Method</label>
                <input
                  type="text"
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">Subtotal (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={subtotal}
                  onChange={(e) => setSubtotal(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">Tax Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={tax}
                  onChange={(e) => setTax(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 mb-1">Discount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-cyan-400 mb-1">Total Stated Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={total}
                  onChange={(e) => setTotal(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-950 border border-cyan-500/50 focus:border-cyan-500 font-bold rounded-xl px-3 py-2 text-xs text-white"
                />
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">Line Items Breakdown</h3>
              <button
                onClick={handleAddItem}
                className="flex items-center gap-1 text-xs text-cyan-400 hover:underline font-semibold"
              >
                <Plus className="w-3.5 h-3.5" /> Add Row
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                    <th className="pb-2">Product Name</th>
                    <th className="pb-2 w-20">Qty</th>
                    <th className="pb-2 w-28">Unit Price</th>
                    <th className="pb-2 w-28">Total</th>
                    <th className="pb-2 w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {items.map((item, idx) => (
                    <tr key={idx} className="group">
                      <td className="py-2.5 pr-2">
                        <input
                          type="text"
                          value={item.product_name}
                          onChange={(e) => handleItemChange(idx, 'product_name', e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-lg px-2 py-1.5 text-xs text-white"
                        />
                      </td>
                      <td className="py-2.5 pr-2">
                        <input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => handleItemChange(idx, 'quantity', Number(e.target.value))}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-lg px-2 py-1.5 text-xs text-white"
                        />
                      </td>
                      <td className="py-2.5 pr-2">
                        <input
                          type="number"
                          step="0.01"
                          value={item.unit_price ?? ''}
                          placeholder="—"
                          onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value === '' ? null : Number(e.target.value))}
                          className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-lg px-2 py-1.5 text-xs text-white"
                        />
                      </td>
                      <td className="py-2.5 pr-2 font-semibold text-slate-200">
                        {item.total_price != null ? `₹${item.total_price.toFixed(2)}` : '—'}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => handleRemoveItem(idx)}
                          className="text-slate-500 hover:text-rose-400 p-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-4 text-center text-slate-500 italic">
                        No line items specified.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Raw OCR Text Box */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-3">
            <h3 className="text-sm font-bold text-slate-300">Raw OCR Text Output</h3>
            <pre className="bg-slate-950 border border-slate-800/80 rounded-2xl p-4 text-[11px] text-slate-400 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
              {receipt.raw_ocr_text || 'No OCR text extracted.'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
