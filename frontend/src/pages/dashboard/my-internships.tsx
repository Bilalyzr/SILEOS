/**
 * MyInternshipsPage — student-facing dedicated page for tracking enrolled
 * internships, voucher status, real course progress, and certificates.
 */
import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Briefcase, Award, Ticket, CheckCircle2, Clock, PlayCircle,
  Download, ExternalLink, Copy,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  DashboardShell, StatCard, SectionCard, EmptyState,
  StaggerGrid, FadeUp,
} from '@/components/dashboard/primitives'
import { internshipApi } from '@/api/internship'
import { MyInternshipCharts } from '@/components/dashboard/MyInternshipCharts'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type InternshipStatus = 'in-progress' | 'completed' | 'pending'

interface StudentInternship {
  id: number
  slug?: string
  title: string
  spoc_name: string
  start_date: string
  voucher_code: string
  voucher_redeemed: boolean
  status: InternshipStatus
  progress: number
  certificate_issued: boolean
  course_id?: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<InternshipStatus, { bg: string; text: string; label: string; Icon: any }> = {
  'in-progress': { bg: 'bg-orange-100',  text: 'text-orange-700',  label: 'In progress', Icon: PlayCircle },
  'completed':   { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Completed',   Icon: CheckCircle2 },
  'pending':     { bg: 'bg-amber-100',   text: 'text-amber-800',   label: 'Pending',     Icon: Clock },
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export const MyInternshipsPage: React.FC = () => {
  const [items, setItems] = useState<StudentInternship[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await internshipApi.myVouchers()
      // A non-array payload (an HTML error page, an error envelope) must not
      // reach .map below — surface it through the error state instead.
      if (!Array.isArray(data)) {
        throw new Error('Unexpected response from the server')
      }
      const mapped: StudentInternship[] = data.map((v) => {
        const redeemed = v.status === 'redeemed'
        const completed = !!v.course_progress?.is_completed || v.engagement_status === 'completed'
        return {
        id: v.id,
        slug: v.internship_slug ?? undefined,
        title: v.internship_title ?? 'Internship',
        spoc_name: v.spoc_name ?? '—',
        start_date: v.redeemed_at || v.created_at,
        voucher_code: v.code,
        voucher_redeemed: redeemed,
        status: (completed ? 'completed' : redeemed ? 'in-progress' : 'pending') as InternshipStatus,
        progress: v.course_progress?.progress_percentage ?? 0,
        certificate_issued: v.certificate_issued,
        course_id: v.redeemed_course_id ?? undefined,
      }})
      setItems(mapped)
    } catch {
      setError('Could not load your internships. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const list = items

  const stats = useMemo(() => {
    const active   = list.filter((i) => i.voucher_redeemed && i.status !== 'completed').length
    const redeemed = list.filter((i) => i.voucher_redeemed).length
    const pending  = list.filter((i) => !i.voucher_redeemed).length
    const certs    = list.filter((i) => i.certificate_issued).length
    return { active, redeemed, pending, certs }
  }, [list])

  const copyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code)
      toast.success('Voucher code copied')
    } catch {
      toast.error('Copy failed')
    }
  }

  return (
    <DashboardShell navbar={false}>
      <FadeUp>
        <div className="dash-chip mb-3">STUDENT WORKSPACE</div>
        <h1 className="dash-h1">My <span className="dash-underline">internships</span></h1>
        <p className="text-slate-600 mt-2 text-sm md:text-base max-w-2xl">
          Track your enrolled internships, voucher status, and certificate progress.
        </p>
      </FadeUp>

      {error && (
        <div role="alert" className="mt-5 flex flex-wrap items-center gap-3 rounded-xl bg-red-50 p-4 text-sm text-red-800">
          <span>{error}</span>
          <button
            onClick={load}
            className="px-3 py-1.5 rounded-lg bg-red-800 text-white text-xs font-semibold hover:bg-red-900"
          >
            Try again
          </button>
        </div>
      )}

      {/* Stat cards */}
      <StaggerGrid className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <StatCard title="Active internships"  value={stats.active}   icon={Ticket}        tone="orange" />
        <StatCard title="Redeemed"            value={stats.redeemed} icon={CheckCircle2}  tone="emerald" />
        <StatCard title="Pending"             value={stats.pending}  icon={Clock}         tone="amber" />
        <StatCard title="Certificates earned" value={stats.certs}    icon={Award}         tone="purple" />
      </StaggerGrid>

      {/* Charts */}
      <MyInternshipCharts list={list} />

      {/* Internship cards */}
      <div className="mt-8">
        <SectionCard
          title="Your internships"
          description="Internships you are enrolled in or have purchased a voucher for."
          icon={Briefcase}
          action={{ label: 'Browse more', to: '/internships' }}
        >
          {loading && list.length === 0 ? (
            <div className="text-center text-slate-500 py-8 text-sm">Loading…</div>
          ) : list.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="No internships available"
              description="You are not enrolled in any internship yet. Browse paid internships and purchase a voucher to get started."
              action={{ label: 'Explore internships', to: '/internships' }}
            />
          ) : (
            <StaggerGrid className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {list.map((it) => {
                const s = STATUS_STYLES[it.status]
                const StatusIcon = s.Icon
                return (
                  <FadeUp key={it.id}>
                    <div className="dash-card dash-card-hoverable p-5 h-full flex flex-col">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="font-semibold text-secondary-900 text-base leading-snug">
                            {it.title}
                          </h3>
                          <p className="text-xs text-slate-500 mt-1">
                            SPOC · {it.spoc_name}
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {it.voucher_redeemed ? 'Started' : 'Purchased'} · {formatDate(it.start_date)}
                          </p>
                        </div>
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-semibold flex-shrink-0 ${s.bg} ${s.text}`}>
                          <StatusIcon className="w-3 h-3" /> {s.label}
                        </span>
                      </div>

                      {/* voucher code chip */}
                      <div className="mt-4 flex items-center gap-2">
                        <code className="bg-slate-100 px-2 py-1 rounded font-mono text-[11px] text-secondary-800">
                          {it.voucher_code}
                        </code>
                        <button
                          onClick={() => copyCode(it.voucher_code)}
                          className="text-slate-400 hover:text-secondary-700 transition"
                          title="Copy code"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                        {it.voucher_redeemed ? (
                          <span className="text-[11px] font-semibold text-emerald-700">Redeemed</span>
                        ) : (
                          <span className="text-[11px] font-semibold text-amber-700">Not yet redeemed</span>
                        )}
                      </div>

                      {/* progress */}
                      <div className="mt-4">
                        <div className="flex items-center justify-between text-xs mb-1.5">
                          <span className="text-slate-500">Progress</span>
                          <span className="font-semibold text-secondary-900">{it.progress}%</span>
                        </div>
                        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              it.status === 'completed' ? 'bg-emerald-500'
                              : it.status === 'pending' ? 'bg-amber-400'
                              : 'bg-orange-500'
                            }`}
                            style={{ width: `${it.progress}%` }}
                          />
                        </div>
                      </div>

                      {/* actions */}
                      <div className="mt-5 flex items-center gap-2 flex-wrap">
                        {it.slug && (
                          <Link
                            to={`/dashboard/my-internships/${it.slug}`}
                            className="dash-cta-ghost text-xs"
                          >
                            <ExternalLink className="w-3.5 h-3.5" /> View
                          </Link>
                        )}
                        {it.course_id && (
                          <Link
                            to={`/courses/${it.course_id}/learn`}
                            className="dash-cta text-xs"
                          >
                            <PlayCircle className="w-3.5 h-3.5" /> Open course
                          </Link>
                        )}
                        {it.certificate_issued && it.course_id && (
                          <Link
                            to={`/certificates/${it.course_id}`}
                            className="dash-cta-ghost text-xs"
                          >
                            <Download className="w-3.5 h-3.5" /> Download cert
                          </Link>
                        )}
                      </div>
                    </div>
                  </FadeUp>
                )
              })}
            </StaggerGrid>
          )}
        </SectionCard>
      </div>
    </DashboardShell>
  )
}

export default MyInternshipsPage
