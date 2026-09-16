import * as React from 'react'

export type Theme = 'purple' | 'blue' | 'green' | 'orange' | 'pink' | 'dark'

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const ThemeContext = React.createContext<ThemeContextType | undefined>(undefined)

export const themeConfig = {
  purple: {
    primary: {
      50: '#faf5ff',
      100: '#f3e8ff',
      200: '#e9d5ff',
      300: '#d8b4fe',
      400: '#c084fc',
      500: '#a855f7',
      600: '#9333ea',
      700: '#7e22ce',
      800: '#6b21a8',
      900: '#581c87',
    },
    gradient: {
      from: 'from-purple-600',
      to: 'to-purple-700',
      via: 'via-purple-500',
    },
    text: 'text-purple-600',
    bg: 'bg-purple-600',
    border: 'border-purple-600',
    hover: 'hover:bg-purple-700',
  },
  blue: {
    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
    },
    gradient: {
      from: 'from-blue-600',
      to: 'to-blue-700',
      via: 'via-blue-500',
    },
    text: 'text-blue-600',
    bg: 'bg-blue-600',
    border: 'border-blue-600',
    hover: 'hover:bg-blue-700',
  },
  green: {
    primary: {
      50: '#f0fdf4',
      100: '#dcfce7',
      200: '#bbf7d0',
      300: '#86efac',
      400: '#4ade80',
      500: '#22c55e',
      600: '#16a34a',
      700: '#15803d',
      800: '#166534',
      900: '#14532d',
    },
    gradient: {
      from: 'from-green-600',
      to: 'to-green-700',
      via: 'via-green-500',
    },
    text: 'text-green-600',
    bg: 'bg-green-600',
    border: 'border-green-600',
    hover: 'hover:bg-green-700',
  },
  orange: {
    primary: {
      50: '#fff7ed',
      100: '#ffedd5',
      200: '#fed7aa',
      300: '#fdba74',
      400: '#fb923c',
      500: '#f97316',
      600: '#ea580c',
      700: '#c2410c',
      800: '#9a3412',
      900: '#7c2d12',
    },
    gradient: {
      from: 'from-orange-600',
      to: 'to-orange-700',
      via: 'via-orange-500',
    },
    text: 'text-orange-600',
    bg: 'bg-orange-600',
    border: 'border-orange-600',
    hover: 'hover:bg-orange-700',
  },
  pink: {
    primary: {
      50: '#fdf2f8',
      100: '#fce7f3',
      200: '#fbcfe8',
      300: '#f9a8d4',
      400: '#f472b6',
      500: '#ec4899',
      600: '#db2777',
      700: '#be185d',
      800: '#9d174d',
      900: '#831843',
    },
    gradient: {
      from: 'from-pink-600',
      to: 'to-pink-700',
      via: 'via-pink-500',
    },
    text: 'text-pink-600',
    bg: 'bg-pink-600',
    border: 'border-pink-600',
    hover: 'hover:bg-pink-700',
  },
  dark: {
    primary: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
    gradient: {
      from: 'from-slate-600',
      to: 'to-slate-700',
      via: 'via-slate-500',
    },
    text: 'text-slate-600',
    bg: 'bg-slate-600',
    border: 'border-slate-600',
    hover: 'hover:bg-slate-700',
  },
}

// The user's real light/dark choice lives in the Aurum display preferences
// (aurum_theme, default dark). The color themes below (purple/blue/orange…)
// have no light/dark meaning, so sf-* components' dark styles must follow the
// Aurum choice — otherwise this provider's boot effect overwrites the bridge
// applied by AurumDisplayControls/AstraRouteTheme and forces "light".
function aurumIsDark(): boolean {
  try {
    return localStorage.getItem('aurum_theme') !== 'light'
  } catch {
    return true
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(() => {
    const stored = localStorage.getItem('app-theme')
    return stored && Object.prototype.hasOwnProperty.call(themeConfig, stored) ? stored as Theme : 'orange'
  })

  const setTheme = React.useCallback((newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem('app-theme', newTheme)

    // Update CSS custom properties
    const config = themeConfig[newTheme]
    const root = document.documentElement
    root.dataset.sashaTheme = newTheme === 'dark' || aurumIsDark() ? 'dark' : 'light'

    Object.entries(config.primary).forEach(([key, value]) => {
      root.style.setProperty(`--primary-${key}`, value)
    })
  }, [])

  React.useEffect(() => {
    // Initialize CSS variables
    const config = themeConfig[theme]
    const root = document.documentElement
    root.dataset.sashaTheme = theme === 'dark' || aurumIsDark() ? 'dark' : 'light'

    Object.entries(config.primary).forEach(([key, value]) => {
      root.style.setProperty(`--primary-${key}`, value)
    })
  }, [theme])

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = React.useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}
