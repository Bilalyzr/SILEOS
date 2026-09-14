/**
 * Themed recharts wrappers for dashboards. All colors come from the
 * primary (orange) + secondary (navy) brand palette so charts feel
 * native to the hero section.
 */
import * as React from 'react'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell, ResponsiveContainer,
  XAxis, YAxis, CartesianGrid, Tooltip,
  type TooltipProps,
} from 'recharts'
import { fadeUp } from './primitives'

// Brand-aligned palette for chart series
export const CHART_COLORS = {
  orange: '#f97316',
  orangeLight: '#fb923c',
  navy: '#20345b',
  sky: '#0ea5e9',
  emerald: '#10b981',
  purple: '#a855f7',
  rose: '#f43f5e',
  amber: '#f59e0b',
  slate: '#64748b',
}

export const CHART_PALETTE = [
  CHART_COLORS.orange,
  CHART_COLORS.sky,
  CHART_COLORS.emerald,
  CHART_COLORS.purple,
  CHART_COLORS.rose,
  CHART_COLORS.amber,
  CHART_COLORS.navy,
  CHART_COLORS.slate,
]

// ---------------------------------------------------------------------------
// Tooltip — common to every chart
// ---------------------------------------------------------------------------

const ThemeTooltip = ({ active, payload, label }: TooltipProps<any, any>) => {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="dash-chart-tooltip">
      {label != null && <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1 font-semibold">{label}</div>}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-sm" style={{ background: p.color }} />
          <span className="font-medium text-secondary-900">{p.name}:</span>
          <span className="font-bold text-secondary-900">
            {typeof p.value === 'number' ? p.value.toLocaleString('en-IN') : p.value ?? '-'}
          </span>
        </div>
      ))}
    </div>
  )
}

const axisStyle = {
  fontSize: 11,
  fontFamily: 'inherit',
  fill: '#94a3b8',
}

// ---------------------------------------------------------------------------
// AreaChartCard — trend over time, single or stacked series
// ---------------------------------------------------------------------------

export interface AreaSeries {
  key: string
  label: string
  color?: string
}

export const AreaChartCard: React.FC<{
  data: Record<string, any>[]
  series: AreaSeries[]
  /** key in the data row used for x-axis labels (e.g. 'date') */
  xKey: string
  height?: number
  className?: string
  /** stack series so they sum to a total per x value (allocation view) */
  stacked?: boolean
}> = ({ data, series, xKey, height = 240, className = '', stacked = false }) => {
  if (!data || data.length === 0) {
    return (
      <motion.div variants={fadeUp} className={className} style={{ height }} />
    )
  }
  return (
  <motion.div variants={fadeUp} className={className} style={{ height }}>
    <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          {series.map((s, i) => {
            const color = s.color || CHART_PALETTE[i % CHART_PALETTE.length]
            return (
              <linearGradient key={s.key} id={`area-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            )
          })}
        </defs>
        <CartesianGrid stroke="#eef2f7" vertical={false} />
        <XAxis dataKey={xKey} tick={axisStyle as any} tickLine={false} axisLine={false} />
        <YAxis tick={axisStyle as any} tickLine={false} axisLine={false} width={48} />
        <Tooltip content={<ThemeTooltip />} cursor={{ stroke: '#cbd5e1', strokeDasharray: '3 3' }} />
        {series.map((s, i) => {
          const color = s.color || CHART_PALETTE[i % CHART_PALETTE.length]
          return (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stackId={stacked ? 'rev' : undefined}
              stroke={color}
              strokeWidth={2}
              fill={`url(#area-${s.key})`}
              animationDuration={800}
              animationEasing="ease-out"
            />
          )
        })}
      </AreaChart>
    </ResponsiveContainer>
  </motion.div>
  )
}

// ---------------------------------------------------------------------------
// LineChartCard
// ---------------------------------------------------------------------------

export const LineChartCard: React.FC<{
  data: Record<string, any>[]
  series: AreaSeries[]
  xKey: string
  height?: number
  className?: string
}> = ({ data, series, xKey, height = 240, className = '' }) => {
  if (!data || data.length === 0) {
    return (
      <motion.div variants={fadeUp} className={className} style={{ height }} />
    )
  }
  return (
  <motion.div variants={fadeUp} className={className} style={{ height }}>
    <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke="#eef2f7" vertical={false} />
        <XAxis dataKey={xKey} tick={axisStyle as any} tickLine={false} axisLine={false} />
        <YAxis tick={axisStyle as any} tickLine={false} axisLine={false} width={48} />
        <Tooltip content={<ThemeTooltip />} cursor={{ stroke: '#cbd5e1', strokeDasharray: '3 3' }} />
        {series.map((s, i) => {
          const color = s.color || CHART_PALETTE[i % CHART_PALETTE.length]
          return (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={color}
              strokeWidth={2.4}
              dot={{ r: 3, fill: color, strokeWidth: 0 }}
              activeDot={{ r: 5, stroke: '#ffffff', strokeWidth: 2 }}
              animationDuration={900}
            />
          )
        })}
      </LineChart>
    </ResponsiveContainer>
  </motion.div>
  )
}

// ---------------------------------------------------------------------------
// BarChartCard
// ---------------------------------------------------------------------------

export const BarChartCard: React.FC<{
  data: Record<string, any>[]
  series: AreaSeries[]
  xKey: string
  height?: number
  className?: string
  /** Stack the bars instead of side-by-side. */
  stacked?: boolean
}> = ({ data, series, xKey, height = 240, className = '', stacked = false }) => {
  if (!data || data.length === 0) {
    return (
      <motion.div variants={fadeUp} className={className} style={{ height }} />
    )
  }
  return (
  <motion.div variants={fadeUp} className={className} style={{ height }}>
    <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke="#eef2f7" vertical={false} />
        <XAxis dataKey={xKey} tick={axisStyle as any} tickLine={false} axisLine={false} />
        <YAxis tick={axisStyle as any} tickLine={false} axisLine={false} width={48} />
        <Tooltip content={<ThemeTooltip />} cursor={{ fill: 'rgba(241, 245, 249, 0.6)' }} />
        {series.map((s, i) => {
          const color = s.color || CHART_PALETTE[i % CHART_PALETTE.length]
          return (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label}
              fill={color}
              radius={[6, 6, 0, 0]}
              stackId={stacked ? 'stack' : undefined}
              animationDuration={800}
            />
          )
        })}
      </BarChart>
    </ResponsiveContainer>
  </motion.div>
  )
}

// ---------------------------------------------------------------------------
// DonutCard — proportions chart with a center label
// ---------------------------------------------------------------------------

export const DonutCard: React.FC<{
  data: { name: string; value: number; color?: string }[]
  /** Total label shown in the center (defaults to sum of values). */
  centerLabel?: string
  centerValue?: string | number
  height?: number
  className?: string
}> = ({ data, centerLabel = 'Total', centerValue, height = 240, className = '' }) => {
  if (!data || data.length === 0) {
    return (
      <motion.div variants={fadeUp} className={`relative ${className}`} style={{ height }} />
    )
  }
  const total = data.reduce((s, d) => s + d.value, 0)
  return (
    <motion.div variants={fadeUp} className={`relative ${className}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
        <PieChart>
          <Pie
            data={data}
            innerRadius="62%"
            outerRadius="92%"
            paddingAngle={2}
            dataKey="value"
            stroke="white"
            strokeWidth={2}
            animationDuration={800}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color || CHART_PALETTE[i % CHART_PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip content={<ThemeTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <div className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold">{centerLabel}</div>
        <div className="text-2xl font-bold text-secondary-900 tabular-nums">{centerValue ?? total.toLocaleString('en-IN')}</div>
      </div>
    </motion.div>
  )
}

// Simple legend used alongside DonutCard
export const ChartLegend: React.FC<{
  items: { name: string; value: number; color?: string }[]
  format?: (n: number) => string
  className?: string
}> = ({ items, format, className = '' }) => (
  <ul className={`space-y-2 ${className}`}>
    {items.map((it, i) => (
      <li key={i} className="flex items-center justify-between text-sm gap-3">
        <span className="flex items-center gap-2 min-w-0">
          <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: it.color || CHART_PALETTE[i % CHART_PALETTE.length] }} />
          <span className="text-slate-700 truncate">{it.name}</span>
        </span>
        <span className="font-semibold text-secondary-900 tabular-nums flex-shrink-0">
          {format ? format(it.value) : it.value.toLocaleString('en-IN')}
        </span>
      </li>
    ))}
  </ul>
)

// ---------------------------------------------------------------------------
// Axis helpers
// ---------------------------------------------------------------------------
//
// genTrend() and buildSeriesRows() lived here — pseudo-random walks that stood
// in "until the backend exposes time-series". Every dashboard wired them into
// its stat cards and charts, so students, instructors, SPOCs and admins all
// read invented history as real. They are gone; a card with no real series now
// renders without one. Do not reintroduce them: chart real data or nothing.

/** Days going back from today, formatted as "Mar 1". */
export function lastNDayLabels(n: number): string[] {
  const out: string[] = []
  const now = new Date()
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(now.getDate() - i)
    out.push(d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }))
  }
  return out
}
