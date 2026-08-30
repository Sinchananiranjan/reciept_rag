export interface User {
  id: number;
  email: string;
  full_name?: string;
  created_at: string;
}

export interface ReceiptItem {
  id?: number;
  receipt_id?: number;
  product_name: string;
  quantity: number;
  unit_price?: number;
  total_price?: number;
  sku?: string;
}

export interface Receipt {
  id: number;
  user_id: number;
  original_filename: string;
  file_path: string;
  file_hash?: string;
  upload_date: string;
  entry_type: 'UPLOAD' | 'MANUAL';
  merchant_name?: string;
  merchant_address?: string;
  phone?: string;
  gstin?: string;
  receipt_date?: string;
  receipt_time?: string;
  receipt_number?: string;
  currency: string;
  subtotal?: number;
  tax?: number;
  cgst?: number;
  sgst?: number;
  igst?: number;
  discount?: number;
  total?: number;
  category?: string;
  payment_method?: string;
  raw_ocr_text?: string;
  extracted_json?: string;
  validation_notes?: string;
  is_duplicate: boolean;
  duplicate_of_id?: number;
  processing_status: 'UPLOADING' | 'PENDING' | 'PROCESSING' | 'OCR_PROCESSING' | 'EXTRACTING' | 'VALIDATING' | 'INDEXING' | 'COMPLETED' | 'NEEDS_REVIEW' | 'FAILED';
  created_at: string;
  updated_at: string;
  items: ReceiptItem[];
}

export interface SourceCitation {
  receipt_id: number;
  merchant_name: string;
  receipt_date: string;
  total: number;
  category: string;
  snippet: string;
}

export interface ChatBreakdownTable {
  title: string;
  columns: string[];
  rows: string[][];
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant';
  content: string;
  sources: SourceCitation[];
  breakdown?: ChatBreakdownTable | null;
  created_at: string;
}

export interface ChatSession {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface SpendingSummary {
  total_spending: number;
  total_receipts: number;
  avg_receipt_amount: number;
  highest_purchase: number;
  current_month_spending: number;
  current_year_spending: number;
  currency: string;
}

export interface CategoryBreakdownItem {
  category: string;
  amount: number;
  percentage: number;
  count: number;
}

export interface MerchantBreakdownItem {
  merchant: string;
  amount: number;
  count: number;
}

export interface SpendingTrendPoint {
  date_label: string;
  amount: number;
  count: number;
}

export interface MonthlyAnalyticsPoint {
  month_name: string;
  year: number;
  amount: number;
  receipt_count: number;
  category_breakdown: Record<string, number>;
}

export interface YearlyAnalyticsPoint {
  year: number;
  amount: number;
  receipt_count: number;
  category_breakdown: Record<string, number>;
}

export interface AIInsightItem {
  title: string;
  description: string;
  type: 'trend' | 'warning' | 'stat' | 'tip';
}

export interface AnalyticsOverview {
  summary: SpendingSummary;
  categories: CategoryBreakdownItem[];
  merchants: MerchantBreakdownItem[];
  trends: SpendingTrendPoint[];
  monthly_analytics: MonthlyAnalyticsPoint[];
  yearly_analytics: YearlyAnalyticsPoint[];
  highest_spending_month?: string;
  highest_spending_year?: number;
  payment_methods: { method: string; amount: number }[];
  insights: AIInsightItem[];
}

export interface ItemBreakdownItem {
  product_name: string;
  purchase_count: number;
  total_quantity: number;
  total_amount: number;
  avg_price: number;
}

export interface ComparisonStat {
  label: string;
  current: number;
  previous: number;
  change_pct?: number | null;
}

export interface DailyTrendPoint {
  day: number;
  date_label: string;
  amount: number;
}

export interface MonthTrendPoint {
  month: number;
  month_name: string;
  amount: number;
  receipt_count: number;
}

export interface MonthlyReview {
  year: number;
  month: number;
  month_name: string;
  has_data: boolean;
  total_spending: number;
  total_receipts: number;
  avg_purchase: number;
  highest_purchase: number;
  highest_purchase_merchant?: string | null;
  total_tax: number;
  total_discount: number;
  categories: CategoryBreakdownItem[];
  stores: MerchantBreakdownItem[];
  top_items: ItemBreakdownItem[];
  daily_trend: DailyTrendPoint[];
  spending_comparison?: ComparisonStat | null;
  receipts_comparison?: ComparisonStat | null;
  insights: AIInsightItem[];
}

export interface YearlyReview {
  year: number;
  has_data: boolean;
  total_spending: number;
  total_receipts: number;
  avg_purchase: number;
  highest_purchase: number;
  total_tax: number;
  total_discount: number;
  monthly_trend: MonthTrendPoint[];
  categories: CategoryBreakdownItem[];
  stores: MerchantBreakdownItem[];
  top_items: ItemBreakdownItem[];
  highest_spending_month?: string | null;
  lowest_spending_month?: string | null;
  spending_comparison?: ComparisonStat | null;
  insights: AIInsightItem[];
}

export interface AvailablePeriods {
  years: number[];
  months_by_year: Record<number, number[]>;
}
