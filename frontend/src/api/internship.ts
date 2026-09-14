import { api } from './axios'

// ---------------- Public ----------------

export interface PublicInternship {
  id: number
  slug: string
  title: string
  description: string
  cover_image: string | null
  price: number
  spoc_name: string | null
}

// ---------------- Student ----------------

export interface RazorpayOrder {
  order_id: string
  amount: number
  currency: string
  key_id: string
}

export interface VoucherIssuedResponse {
  code: string
  voucher_id: number
}

export interface MyVoucher {
  id: number
  code: string
  status: string // "issued" | "redeemed" (backend-controlled)
  internship_id: number
  internship_title: string
  internship_slug: string | null
  spoc_name: string | null
  redeemed_course_id: number | null
  redeemed_course_title: string | null
  company_name: string | null
  attendance_count?: number
  engagement_status: 'active' | 'completed' | 'closed'
  certificate_issued: boolean
  issued_certificate_id: number | null
  created_at: string
  redeemed_at: string | null
  // Issue 6: progress of the course this voucher was redeemed for.
  // Null until the voucher is redeemed on a course.
  course_progress?: {
    progress_percentage: number
    enrollment_status: string
    is_completed: boolean
    completion_date: string | null
  } | null
}

// ---------------- Admin ----------------

export interface AdminInternshipRow {
  id: number
  slug: string
  title: string
  description: string
  cover_image: string | null
  price: number
  spoc_user_id: number
  spoc_name: string | null
  is_published: boolean
  vouchers_issued: number
  vouchers_redeemed: number
  created_at: string
}

export interface AdminInternshipCreatePayload {
  title: string
  description: string
  price: number
  spoc_user_id: number
  cover_image?: string
  is_published?: boolean
}

export interface AdminInternshipUpdatePayload {
  title?: string
  description?: string
  price?: number
  spoc_user_id?: number
  cover_image?: string
  is_published?: boolean
}

export interface AdminVoucherRow {
  code: string
  buyer_name: string
  buyer_email: string
  status: string
  redeemed_on_course_title: string | null
  created_at: string
  redeemed_at: string | null
}

export interface AdminRosterRow {
  voucher_id: number
  voucher_code: string
  status: string
  buyer_id: number | null
  buyer_name: string
  buyer_email: string
  redeemed_course_id: number | null
  redeemed_course_title: string | null
  enrollment_id: number | null
  progress_pct: number | null
  completion_date: string | null
  certs_count: number | null
  issued_certificate_id: number | null
  hired_by_company: string | null
  hired_by_source: 'override' | 'auto' | null
  attendance_count: number
}

export interface AdminAttendanceRow {
  id: number
  user_id: number
  attended_at: string
  status: 'present' | 'absent' | 'late' | 'excused' | string
  notes: string
  marked_by: number | null
  created_at: string
  updated_at: string
}

export interface ApprovedCompanyRow {
  id: number
  name: string
  slug?: string
  is_approved: boolean
}

// ---------------- Razorpay helper ----------------

export async function ensureRazorpayLoaded(): Promise<void> {
  if ((window as any).Razorpay) return
  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]'
    )
    if (existing) {
      if ((window as any).Razorpay) return resolve()
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('Failed to load Razorpay SDK')))
      return
    }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Razorpay SDK'))
    document.body.appendChild(script)
  })
  // Race guard — onload can fire before the global binding attaches in some
  // browsers / ad-block scenarios.
  if (!(window as any).Razorpay) {
    throw new Error('Razorpay SDK did not initialize. Please disable ad-blockers and retry.')
  }
}

// ---------------- API ----------------

export const internshipApi = {
  // Public
  list: () =>
    api.get<PublicInternship[]>('/internships').then(r => r.data),
  getBySlug: (slug: string) =>
    api.get<PublicInternship>(`/internships/${slug}`).then(r => r.data),

  // Student
  createOrder: (internshipId: number) =>
    api.post<RazorpayOrder>(`/internships/${internshipId}/purchase`).then(r => r.data),
  verifyPurchase: (payload: {
    razorpay_order_id: string
    razorpay_payment_id: string
    razorpay_signature: string
    internship_id: number
  }) =>
    api.post<VoucherIssuedResponse>('/internships/purchase/verify', payload).then(r => r.data),
  myVouchers: () =>
    api.get<MyVoucher[]>('/internships/my-vouchers').then(r => r.data),

  // Admin
  adminList: () =>
    api.get<AdminInternshipRow[]>('/admin/internships').then(r => r.data),
  adminGet: (id: number) =>
    api.get<AdminInternshipRow>(`/admin/internships/${id}`).then(r => r.data),
  adminCreate: (body: AdminInternshipCreatePayload) =>
    api.post<AdminInternshipRow>('/admin/internships', body).then(r => r.data),
  adminUpdate: (id: number, body: AdminInternshipUpdatePayload) =>
    api.put<AdminInternshipRow>(`/admin/internships/${id}`, body).then(r => r.data),
  adminDelete: (id: number) =>
    api.delete(`/admin/internships/${id}`).then(r => r.data),
  adminVouchers: async (id: number): Promise<AdminVoucherRow[]> => {
    // Backend returns {total, items: [...]} with buyer nested inside each
    // row — flatten to the shape the admin UI expects.
    const { data } = await api.get<any>(`/admin/internships/${id}/vouchers`)
    const raw = Array.isArray(data) ? data : (data?.items || [])
    return raw.map((v: any) => ({
      code: v.code,
      buyer_name: v.buyer?.display_name || '',
      buyer_email: v.buyer?.email || '',
      status: v.status,
      redeemed_on_course_title: v.redeemed_course_title ?? null,
      created_at: v.created_at,
      redeemed_at: v.redeemed_at ?? null,
    }))
  },
  adminRoster: async (id: number): Promise<AdminRosterRow[]> => {
    // Backend returns {internship_id, total, items: [...]}.
    const { data } = await api.get<any>(`/admin/internships/${id}/roster`)
    const raw = Array.isArray(data) ? data : (data?.items || [])
    return raw as AdminRosterRow[]
  },

  // Admin — attendance
  adminAttendanceList: async (
    internshipId: number,
    userId?: number,
    from?: string,
    to?: string,
  ): Promise<AdminAttendanceRow[]> => {
    const params: Record<string, string> = {}
    if (userId != null) params.user_id = String(userId)
    if (from) params.from = from
    if (to) params.to = to
    const qs = new URLSearchParams(params).toString()
    const url = `/admin/internships/${internshipId}/attendance${qs ? `?${qs}` : ''}`
    const { data } = await api.get<any>(url)
    return (data?.items || []) as AdminAttendanceRow[]
  },
  adminAttendanceMark: (
    internshipId: number,
    body: { user_id: number; attended_at: string; status?: string; notes?: string },
  ) =>
    api
      .post<AdminAttendanceRow>(`/admin/internships/${internshipId}/attendance`, body)
      .then(r => r.data),
  adminAttendanceDelete: (internshipId: number, recordId: number) =>
    api
      .delete(`/admin/internships/${internshipId}/attendance/${recordId}`)
      .then(r => r.data),

  // Admin — assign company (hiring override)
  adminAssignCompany: (internshipId: number, voucherId: number, companyId: number) =>
    api
      .post(
        `/admin/internships/${internshipId}/vouchers/${voucherId}/assign-company`,
        { company_id: companyId },
      )
      .then(r => r.data),
  adminClearCompanyOverride: (internshipId: number, voucherId: number) =>
    api
      .delete(`/admin/internships/${internshipId}/vouchers/${voucherId}/assign-company`)
      .then(r => r.data),
  adminDeleteVoucher: (internshipId: number, voucherId: number, force = false) =>
    api
      .delete(`/admin/internships/${internshipId}/vouchers/${voucherId}?force=${force}`)
      .then(r => r.data),
  adminMoveVoucher: (internshipId: number, voucherId: number, targetInternshipId: number) =>
    api
      .post(`/admin/internships/${internshipId}/vouchers/${voucherId}/move`, {
        target_internship_id: targetInternshipId,
      })
      .then(r => r.data),

  // Admin — approved companies (for assign-company dropdown)
  listApprovedCompanies: async (): Promise<ApprovedCompanyRow[]> => {
    // Use the unified admin companies endpoint with status=active (approved + setup complete)
    // status=active returns: is_approved=True AND (approval_source!='admin_invite' OR owner.is_verified=True)
    try {
      const { data } = await api.get<any>('/companies/admin/all?status=active')
      const raw = Array.isArray(data) ? data : (data?.items || [])
      return raw.map((c: any) => ({
        id: c.id,
        name: c.name,
        slug: c.slug,
        is_approved: !!c.is_approved,
      }))
    } catch (e) {
      console.error('Failed to fetch approved companies:', e)
      return []
    }
  },

  // Admin — certificate issue / revoke
  adminIssueCertForEnrollment: (enrollmentId: number, forceCompletion: boolean) =>
    api
      .post(`/certificates/admin/enrollments/${enrollmentId}/issue`, {
        force_completion: forceCompletion,
      })
      .then(r => r.data),
  adminRevokeCert: (issuedCertId: number, reason: string) =>
    api
      .post(`/certificates/admin/${issuedCertId}/revoke`, { reason })
      .then(r => r.data),

  // Admin — manual voucher creation
  adminCreateManualVoucher: (
    internshipId: number,
    body: { user_id: number; amount_paid?: number; notes?: string }
  ) =>
    api
      .post<any>(`/admin/internships/${internshipId}/vouchers`, body)
      .then(r => r.data),

  // SPOC — their own view
  spocMyInternships: () =>
    api.get<AdminInternshipRow[]>('/spoc/my-internships').then(r => r.data),
  spocRoster: async (id: number): Promise<AdminRosterRow[]> => {
    const { data } = await api.get<any>(`/spoc/internships/${id}/roster`)
    const raw = Array.isArray(data) ? data : (data?.items || [])
    return raw as AdminRosterRow[]
  },
}

/**
 * Open Razorpay for an internship purchase and resolve with the issued voucher code.
 *
 * Mirrors the pattern in `checkout.tsx` / `course-detail.tsx` handleEnroll:
 *   1. Create a Razorpay order server-side
 *   2. Ensure the Razorpay SDK is loaded (adblock-safe)
 *   3. Open the Razorpay modal
 *   4. In the handler, call verify and issue a voucher
 *
 * Caller can pass `prefill` to pre-populate the Razorpay form.
 */
export async function purchaseAndVerify(
  internshipId: number,
  opts: { prefill?: { name?: string; email?: string; contact?: string } } = {}
): Promise<VoucherIssuedResponse> {
  const order = await internshipApi.createOrder(internshipId)
  await ensureRazorpayLoaded()

  return new Promise<VoucherIssuedResponse>((resolve, reject) => {
    const options: any = {
      key: order.key_id,
      amount: order.amount,
      currency: order.currency || 'INR',
      name: 'SashaInfinity Internships',
      description: 'Paid Internship Program',
      order_id: order.order_id,
      prefill: opts.prefill || {},
      theme: { color: '#f59e0b' },
      handler: async (paymentResponse: any) => {
        try {
          const voucher = await internshipApi.verifyPurchase({
            razorpay_order_id: paymentResponse.razorpay_order_id,
            razorpay_payment_id: paymentResponse.razorpay_payment_id,
            razorpay_signature: paymentResponse.razorpay_signature,
            internship_id: internshipId,
          })
          resolve(voucher)
        } catch (err: any) {
          reject(err)
        }
      },
      modal: {
        ondismiss: () => reject(new Error('Payment cancelled')),
      },
    }
    const rzp = new (window as any).Razorpay(options)
    rzp.on('payment.failed', (resp: any) => {
      reject(new Error(resp?.error?.description || 'Payment failed'))
    })
    rzp.open()
  })
}
