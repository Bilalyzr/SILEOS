/**
 * Student Live Classes — Upcoming (with countdown + Join state machine),
 * a LIVE-now strip, and Past (with recording links).
 *
 * No page-level shell here: this route renders inside StudentLayout ->
 * DashboardWorkspace, which already supplies the dash-bg, decorative shapes
 * and the max-w-7xl padded container (see my-courses.tsx for the same
 * convention).
 */
import * as React from 'react'
import { Link } from 'react-router-dom'
import { Video, Radio, History, Download } from 'lucide-react'
import { motion } from 'framer-motion'
import {
  Greeting, SectionCard, EmptyState, ErrorState, StaggerGrid, fadeUp,
} from '@/components/dashboard/primitives'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/use-auth'
import { listLiveClasses, fetchLiveNow, type LiveClassOut } from '@/api/liveClasses'
import { ClassCountdown } from '@/components/live/ClassCountdown'
import { LiveStatusBadge } from '@/components/live/LiveStatusBadge'
import { joinButtonState } from '@/components/live/joinButtonState'

function formatScheduled(iso: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      weekday: 'short', month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit', timeZone: timezone,
    }).format(new Date(iso))
  } catch {
    return new Date(iso).toLocaleString()
  }
}

const ClassCard: React.FC<{ cls: LiveClassOut; fetchedAtLocal: Date; showRecording?: boolean }> = ({
  cls, fetchedAtLocal, showRecording,
}) => {
  const state = joinButtonState(cls, new Date())
  // The countdown only makes sense while counting down to something in the
  // future (join-opens or the scheduled start). Once the class is live,
  // scheduled_start is in the past, so a countdown targeting it would sit
  // permanently on "starting now" right next to the LIVE badge — just hide
  // it; the badge alone already communicates the state.
  const showCountdown = cls.status === 'scheduled'

  return (
    <motion.div variants={fadeUp} className="dash-card p-0 overflow-hidden flex flex-col">
      <div className="p-4 flex-1 flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-base font-semibold text-secondary-900 line-clamp-2">{cls.title}</h3>
          <LiveStatusBadge status={cls.status} />
        </div>

        {cls.description && (
          <p className="text-xs text-slate-500 line-clamp-2">{cls.description}</p>
        )}

        <p className="text-xs text-slate-500">{formatScheduled(cls.scheduled_start, cls.timezone)}</p>

        {showCountdown && (
          <p className="text-xs font-medium text-orange-600">
            <ClassCountdown
              serverTs={cls.server_ts}
              fetchedAtLocal={fetchedAtLocal}
              target={cls.join_opens_at}
            />
          </p>
        )}

        <div className="mt-auto pt-2 flex items-center gap-2">
          {state.action === 'join' && (
            <Link to={`/student/live-classes/${cls.id}/join`} className="flex-1">
              <Button className="w-full" disabled={state.disabled}>
                <Video className="h-4 w-4 mr-1.5" />
                {state.label}
              </Button>
            </Link>
          )}
          {state.action === 'recording' && showRecording && (
            <Link to={`/student/live-classes/${cls.id}/recording`} className="flex-1">
              <Button variant="outline" className="w-full">
                <Download className="h-4 w-4 mr-1.5" />
                {state.label}
              </Button>
            </Link>
          )}
          {state.action === 'none' && (
            <Button className="w-full" disabled variant="ghost">
              {state.label}
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export function StudentLiveClassesPage() {
  const { fullName } = useAuth()
  const [upcoming, setUpcoming] = React.useState<LiveClassOut[]>([])
  const [past, setPast] = React.useState<LiveClassOut[]>([])
  const [liveNow, setLiveNow] = React.useState<LiveClassOut[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [fetchedAtLocal, setFetchedAtLocal] = React.useState<Date>(() => new Date())

  const load = React.useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [upcomingRes, pastRes, liveNowRes] = await Promise.all([
        listLiveClasses({ scope: 'upcoming', page_size: 50 }),
        listLiveClasses({ scope: 'past', page_size: 20 }),
        fetchLiveNow(),
      ])
      setFetchedAtLocal(new Date())
      setUpcoming(upcomingRes.items)
      setPast(pastRes.items)
      setLiveNow(liveNowRes.classes)
    } catch (err: any) {
      setError(err?.message || 'Failed to load live classes')
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    load()
  }, [load])

  return (
    <>
      <Greeting
        name={fullName}
        chip="LIVE CLASSES"
        subtitle="Join scheduled live sessions for your enrolled courses, or catch up on recordings."
        className="mb-6"
      />

      {liveNow.length > 0 && (
        <motion.div variants={fadeUp} initial="hidden" animate="show" className="mb-6">
          <div className="rounded-lg border border-danger-200 bg-danger-50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Radio className="h-4 w-4 text-danger-600" />
              <h2 className="text-sm font-semibold text-danger-700">Live now</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {liveNow.map((cls) => (
                <Link
                  key={cls.id}
                  to={`/student/live-classes/${cls.id}/join`}
                  className="flex items-center justify-between gap-2 rounded-md bg-white border border-danger-100 px-3 py-2 hover:shadow-medium transition-shadow"
                >
                  <span className="text-sm font-medium text-secondary-900 line-clamp-1">{cls.title}</span>
                  <Badge variant="danger">Join</Badge>
                </Link>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      <SectionCard title="Upcoming" description="Classes you can join soon" icon={Video} className="mb-6">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map((i) => (
              <div key={i} className="dash-card p-4 space-y-3">
                <div className="h-4 w-3/4 dash-skeleton" />
                <div className="h-3 w-1/2 dash-skeleton" />
                <div className="h-8 w-full dash-skeleton" />
              </div>
            ))}
          </div>
        ) : error ? (
          <ErrorState onRetry={load} />
        ) : upcoming.length === 0 ? (
          <EmptyState
            icon={Video}
            title="No upcoming classes"
            description="Your instructors haven't scheduled a live class yet. Check back soon."
          />
        ) : (
          <StaggerGrid className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {upcoming.map((cls) => (
              <ClassCard key={cls.id} cls={cls} fetchedAtLocal={fetchedAtLocal} />
            ))}
          </StaggerGrid>
        )}
      </SectionCard>

      <SectionCard title="Past" description="Recordings from classes that have ended" icon={History}>
        {loading ? null : past.length === 0 ? (
          <EmptyState icon={History} title="No past classes yet" />
        ) : (
          <StaggerGrid className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {past.map((cls) => (
              <ClassCard key={cls.id} cls={cls} fetchedAtLocal={fetchedAtLocal} showRecording />
            ))}
          </StaggerGrid>
        )}
      </SectionCard>
    </>
  )
}

export default StudentLiveClassesPage
