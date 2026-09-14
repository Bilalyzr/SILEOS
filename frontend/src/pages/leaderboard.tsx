/**
 * Student leaderboard page (plan Task 10, spec D5/D6) — global + per-
 * enrolled-course tabs. Deliberately framed as friendly weekly motivation,
 * not competitive ranking (spec D5's "Hall of Fame page untouched" note —
 * this is a SEPARATE page from /admin/hall-of-fame's anti-ranking Wall of
 * Fame).
 */
import * as React from 'react'
import { Trophy, Globe, BookOpen } from 'lucide-react'
import { Greeting, FadeUp, SectionCard, EmptyState, Spinner } from '@/components/dashboard/primitives'
import { LeaderboardTable } from '@/components/gamification/LeaderboardTable'
import { gamificationAPI, type LeaderboardResponse, type LeaderboardScope } from '@/api/gamification'
import { courseAPI } from '@/api/course'
import { useAuth } from '@/hooks/use-auth'

interface CourseTab {
  id: number
  title: string
}

export const LeaderboardPage: React.FC = () => {
  const { user } = useAuth()
  const [courses, setCourses] = React.useState<CourseTab[]>([])
  const [activeScope, setActiveScope] = React.useState<LeaderboardScope>('global')
  const [data, setData] = React.useState<LeaderboardResponse | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    (async () => {
      try {
        const enrolled = await courseAPI.getEnrolledCourses()
        setCourses(
          (enrolled || []).map((c: any) => ({ id: c.id, title: c.post_title || c.title || `Course ${c.id}` }))
        )
      } catch {
        // Course tabs are a nice-to-have — the global tab always works.
      }
    })()
  }, [])

  const fetchLeaderboard = React.useCallback(async (scope: LeaderboardScope) => {
    try {
      setIsLoading(true)
      setError(null)
      setData(await gamificationAPI.getLeaderboard(scope))
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load the leaderboard')
    } finally {
      setIsLoading(false)
    }
  }, [])

  React.useEffect(() => { fetchLeaderboard(activeScope) }, [activeScope, fetchLeaderboard])

  const tabs: { key: LeaderboardScope; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { key: 'global', label: 'Global', icon: Globe },
    ...courses.map((c) => ({ key: `course:${c.id}` as LeaderboardScope, label: c.title, icon: BookOpen })),
  ]

  return (
    <>
      <Greeting
        name={undefined}
        chip="LEADERBOARD"
        subtitle="A friendly weekly look at who's learning the most — earn XP by completing lessons, quizzes, and more."
        className="mb-6"
      />

      <FadeUp>
        <div className="flex flex-wrap gap-2 mb-4" role="tablist">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeScope === tab.key
            return (
              <button
                key={tab.key}
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveScope(tab.key)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-full text-sm font-semibold transition ${
                  isActive
                    ? 'bg-orange-500 text-white shadow-sm'
                    : 'bg-white text-slate-600 border border-slate-200 hover:border-orange-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="truncate max-w-[160px]">{tab.label}</span>
              </button>
            )
          })}
        </div>
      </FadeUp>

      <FadeUp>
        <SectionCard title={activeScope === 'global' ? 'Global leaderboard' : 'Course leaderboard'} icon={Trophy}>
          {isLoading ? (
            <div className="flex items-center justify-center py-16"><Spinner size="md" /></div>
          ) : error ? (
            <EmptyState icon={Trophy} title="Couldn't load the leaderboard" description={error} />
          ) : (
            <LeaderboardTable
              entries={data?.entries ?? []}
              myRank={data?.my_rank}
              currentUserId={user?.id}
            />
          )}
        </SectionCard>
      </FadeUp>
    </>
  )
}

export default LeaderboardPage
