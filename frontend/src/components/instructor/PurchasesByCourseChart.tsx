/**
 * "Purchases by Course" — ranked horizontal bar chart for the instructor
 * analytics page.
 *
 * One measure (purchases) across one dimension (course), so: one hue, bars
 * ranked highest-first, no legend. Course titles are long, so the category axis
 * runs down the left where labels have room and the full title lives in the
 * tooltip. Replaces the CSS progress-bar list that used to sit here — same
 * numbers, but with a shared value scale, gridlines and hover detail.
 */
import React, { useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
  type TooltipProps,
} from 'recharts'

const BAR_HUE = '#f97316'   // brand orange — single series, so a single hue
const AXIS_INK = '#94a3b8'
const TICK_INK = '#475569'
const GRID_INK = '#eef2f7'
const BAR_THICKNESS = 20    // <= 24px; the leftover band is deliberate air
const ROW_HEIGHT = 40
const COLLAPSED_ROWS = 8    // past this the category labels stop being readable

export interface CoursePurchases {
  courseId: number
  title: string
  enrollments: number
}

interface ChartRow {
  name: string
  fullName: string
  purchases: number
  share: number
}

function truncate(title: string, max = 20): string {
  return title.length > max ? `${title.slice(0, max - 1)}…` : title
}

const PurchasesTooltip = ({ active, payload }: TooltipProps<number, string>) => {
  if (!active || !payload?.length) return null
  const row = payload[0].payload as ChartRow
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-lg">
      <p className="mb-1 max-w-[220px] text-xs font-semibold text-gray-900">{row.fullName}</p>
      <p className="flex items-center gap-1.5 text-xs text-gray-600">
        <span className="h-2 w-2 rounded-sm" style={{ background: BAR_HUE }} />
        <span className="font-semibold tabular-nums text-gray-900">{row.purchases.toLocaleString()}</span>
        purchase{row.purchases === 1 ? '' : 's'}
        <span className="text-gray-400">· {row.share.toFixed(1)}% of total</span>
      </p>
    </div>
  )
}

export const PurchasesByCourseChart: React.FC<{
  courses: CoursePurchases[]
  /** Headline total, so the subtitle matches the KPI cards exactly. */
  totalPurchases: number
}> = ({ courses, totalPurchases }) => {
  const [showAll, setShowAll] = useState(false)

  const allRows: ChartRow[] = useMemo(() => {
    const sorted = [...courses].sort((a, b) => b.enrollments - a.enrollments)
    const total = sorted.reduce((s, c) => s + c.enrollments, 0)
    return sorted.map(c => ({
      name: truncate(c.title),
      fullName: c.title,
      purchases: c.enrollments,
      share: total > 0 ? (c.enrollments / total) * 100 : 0,
    }))
  }, [courses])

  const rows = showAll ? allRows : allRows.slice(0, COLLAPSED_ROWS)
  const hidden = allRows.length - rows.length

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Purchases by Course</h2>
          <p className="text-sm text-gray-500 mt-1">
            {allRows.length > 0
              ? `${totalPurchases.toLocaleString()} purchases across ${allRows.length} course${allRows.length === 1 ? '' : 's'}, highest first.`
              : 'Purchases per course, highest first.'}
          </p>
        </div>
        {(hidden > 0 || showAll) && (
          <button
            onClick={() => setShowAll(v => !v)}
            className="text-xs font-medium text-orange-600 hover:text-orange-700 border border-orange-200 hover:bg-orange-50 rounded-md px-3 py-1.5 transition-colors"
          >
            {showAll ? `Show top ${COLLAPSED_ROWS}` : `Show all ${allRows.length}`}
          </button>
        )}
      </div>

      {rows.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No course data available yet</div>
      ) : (
        <>
          <div style={{ height: Math.max(200, rows.length * ROW_HEIGHT + 40) }}>
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <BarChart
                data={rows}
                layout="vertical"
                margin={{ top: 4, right: 44, left: 4, bottom: 4 }}
              >
                <CartesianGrid stroke={GRID_INK} horizontal={false} />
                <XAxis
                  type="number"
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: AXIS_INK }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  tick={{ fontSize: 12, fill: TICK_INK }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip content={<PurchasesTooltip />} cursor={{ fill: 'rgba(241, 245, 249, 0.6)' }} />
                <Bar
                  dataKey="purchases"
                  name="Purchases"
                  fill={BAR_HUE}
                  barSize={BAR_THICKNESS}
                  radius={[0, 4, 4, 0]}
                  animationDuration={700}
                >
                  <LabelList
                    dataKey="purchases"
                    position="right"
                    offset={8}
                    style={{ fontSize: 11, fill: TICK_INK, fontWeight: 600 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {hidden > 0 && (
            <p className="mt-2 text-xs text-gray-400">
              {hidden} more course{hidden === 1 ? '' : 's'} not shown — every course is listed under Course Performance.
            </p>
          )}
        </>
      )}
    </div>
  )
}

export default PurchasesByCourseChart
