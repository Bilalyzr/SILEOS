import { api } from './axios'

// ============================================================================
// Types
// ============================================================================

export interface BillingProfile {
  name: string
  gstin: string
  legal_name: string
  billing_address: string
  state_code: string
}

export interface BillingProfileUpdate {
  gstin?: string
  legal_name?: string
  billing_address?: string
  state_code?: string
}

export type InvoiceStatus = 'issued' | 'paid' | 'cancelled'

export interface InvoiceItem {
  description: string
  quantity: number
  unit_price: number
  line_total: number
}

export interface Invoice {
  id: number
  invoice_number: string | null
  status: InvoiceStatus
  subtotal: number
  cgst: number
  sgst: number
  igst: number
  total: number
  tax_note: string
  due_date: string | null
  issued_at: string | null
  paid_at: string | null
  notes: string
  items: InvoiceItem[]
}

export interface InvoicePayOrder {
  order_id: string
  amount: number
  currency: string
  key_id: string
}

export interface SeatPool {
  id: number
  course_id: number | null
  bundle_id: number | null
  course_title: string | null
  bundle_name: string | null
  total_seats: number
  used_seats: number
}

export interface SeatAssignment {
  user_id: number
  email: string
  assigned_at: string | null
  granted_course_ids?: number[]
  already_had_course_ids?: number[]
}

// ============================================================================
// Profile
// ============================================================================

export const fetchBillingProfile = async (): Promise<BillingProfile> => {
  const { data } = await api.get('/companies/billing/profile')
  return data
}

export const updateBillingProfile = async (
  update: BillingProfileUpdate
): Promise<BillingProfile> => {
  const { data } = await api.patch('/companies/billing/profile', update)
  return data
}

// ============================================================================
// Invoices
// ============================================================================

export const fetchInvoices = async (): Promise<Invoice[]> => {
  const { data } = await api.get('/companies/billing/invoices')
  return data
}

/**
 * Download an invoice PDF via an authenticated GET (the file lives behind
 * auth, so a plain <a href> would 401 — fetch as a blob, wrap it in an
 * object URL, and click a throwaway anchor).
 */
export const downloadInvoicePdf = async (invoiceId: number, filename?: string): Promise<void> => {
  const { data } = await api.get(`/companies/billing/invoices/${invoiceId}/pdf`, {
    responseType: 'blob',
  })
  const blob = new Blob([data], { type: 'application/pdf' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || `invoice-${invoiceId}.pdf`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export const createInvoiceOrder = async (invoiceId: number): Promise<InvoicePayOrder> => {
  const { data } = await api.post(`/companies/billing/invoices/${invoiceId}/pay`)
  return data
}

export const verifyInvoicePayment = async (p: {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
  invoice_id: number
}): Promise<{ success: boolean; message: string }> => {
  const { data } = await api.post('/payments/verify', p)
  return data
}

// ============================================================================
// Seat pools
// ============================================================================

export const fetchSeatPools = async (): Promise<SeatPool[]> => {
  const { data } = await api.get('/companies/billing/seat-pools')
  return data
}

export const assignSeat = async (poolId: number, email: string): Promise<SeatAssignment> => {
  const { data } = await api.post(`/companies/billing/seat-pools/${poolId}/assign`, { email })
  return data
}

export const fetchSeatAssignments = async (poolId: number): Promise<SeatAssignment[]> => {
  const { data } = await api.get(`/companies/billing/seat-pools/${poolId}/assignments`)
  return data
}
