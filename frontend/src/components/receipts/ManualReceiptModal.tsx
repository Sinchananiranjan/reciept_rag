import React, { useState } from 'react';
import { X, Plus, Trash2, Edit3, Loader2, CheckCircle2 } from 'lucide-react';
import { apiClient } from '../../services/api';
import { ReceiptItem } from '../../types';

interface ManualReceiptModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ManualReceiptModal: React.FC<ManualReceiptModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [merchantName, setMerchantName] = useState('');
  const [receiptDate, setReceiptDate] = useState('');
  const [receiptTime, setReceiptTime] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [category, setCategory] = useState('Other');
  const [paymentMethod, setPaymentMethod] = useState('Cash');
  const [subtotal, setSubtotal] = useState<number | ''>('');
  const [tax, setTax] = useState<number | ''>('');
  const [discount, setDiscount] = useState<number | ''>('');
  const [total, setTotal] = useState<number | ''>('');
  const [phone, setPhone] = useState('');
  const [gstin, setGstin] = useState('');
  const [receiptNumber, setReceiptNumber] = useState('');
  const [items, setItems] = useState<ReceiptItem[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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

  if (!isOpen) return null;

  const handleAddItem = () => {
    setItems((prev) => [
      ...prev,
      { product_name: 'New Product', quantity: 1, unit_price: 0, total_price: 0 },
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchantName || total === '') {
      setErrorMsg('Merchant Name and Total Amount are required.');
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      await apiClient.post('/receipts/manual', {
        merchant_name: merchantName,
        receipt_date: receiptDate || new Date().toISOString().split('T')[0],
        receipt_time: receiptTime,
        currency,
        category,
        payment_method: paymentMethod,
        subtotal: subtotal === '' ? null : Number(subtotal),
        tax: tax === '' ? null : Number(tax),
        discount: discount === '' ? null : Number(discount),
        total: Number(total),
        phone,
        gstin,
        receipt_number: receiptNumber,
        items,
      });

      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to create manual receipt.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-2xl p-6 shadow-2xl space-y-5 relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Edit3 className="w-5 h-5 text-cyan-400" />
            Enter Receipt Manually
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Add a purchase or bill record directly without uploading an image.
          </p>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">Merchant / Store Name *</label>
              <input
                type="text"
                value={merchantName}
                onChange={(e) => setMerchantName(e.target.value)}
                placeholder="e.g. Local Supermarket"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-white"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Total Amount *</label>
              <input
                type="number"
                step="0.01"
                value={total}
                onChange={(e) => setTotal(e.target.value ? Number(e.target.value) : '')}
                placeholder="0.00"
                className="w-full bg-slate-950 border border-cyan-500/50 focus:border-cyan-500 font-bold rounded-xl px-3 py-2 text-white"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Receipt Date</label>
              <input
                type="date"
                value={receiptDate}
                onChange={(e) => setReceiptDate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-white"
              >
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Payment Method</label>
              <input
                type="text"
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                placeholder="UPI, Cash, Card"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-white"
              >
                <option value="INR">INR (₹)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Subtotal</label>
              <input
                type="number"
                step="0.01"
                value={subtotal}
                onChange={(e) => setSubtotal(e.target.value ? Number(e.target.value) : '')}
                placeholder="0.00"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Tax Amount</label>
              <input
                type="number"
                step="0.01"
                value={tax}
                onChange={(e) => setTax(e.target.value ? Number(e.target.value) : '')}
                placeholder="0.00"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-white"
              />
            </div>
          </div>

          {/* Line Items Table */}
          <div className="pt-2 border-t border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">Line Items</span>
              <button
                type="button"
                onClick={handleAddItem}
                className="text-xs text-cyan-400 hover:underline flex items-center gap-1 font-semibold"
              >
                <Plus className="w-3.5 h-3.5" /> Add Row
              </button>
            </div>

            {items.map((item, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs">
                <input
                  type="text"
                  placeholder="Product name"
                  value={item.product_name}
                  onChange={(e) => handleItemChange(idx, 'product_name', e.target.value)}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-white"
                />
                <input
                  type="number"
                  placeholder="Qty"
                  value={item.quantity}
                  onChange={(e) => handleItemChange(idx, 'quantity', Number(e.target.value))}
                  className="w-16 bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-white"
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="Price"
                  value={item.unit_price || 0}
                  onChange={(e) => handleItemChange(idx, 'unit_price', Number(e.target.value))}
                  className="w-24 bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5 text-white"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveItem(idx)}
                  className="text-slate-500 hover:text-rose-400 p-1"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-800 text-xs font-semibold text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 text-white font-semibold text-xs shadow-lg shadow-cyan-500/25 disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              Save Manual Receipt
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
