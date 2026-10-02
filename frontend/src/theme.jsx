import { createContext, useContext, useMemo, useState } from 'react'

const STORAGE_KEY = 'replicai-theme'
const ThemeContext = createContext({ theme: 'dark', toggleTheme: () => {} })

function readStoredTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

const resolvedInitialTheme = (() => {
  const theme = readStoredTheme()
  if (typeof document !== 'undefined') applyTheme(theme)
  return theme
})()

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(resolvedInitialTheme)

  const toggleTheme = useMemo(
    () => () => {
      setTheme((current) => {
        const next = current === 'dark' ? 'light' : 'dark'
        if (typeof document !== 'undefined') {
          document.documentElement.classList.add('theme-swap')
          applyTheme(next)
          try {
            localStorage.setItem(STORAGE_KEY, next)
          } catch {
            /* ignore quota / private mode */
          }
          const raf1 = requestAnimationFrame(() => {
            const raf2 = requestAnimationFrame(() => {
              document.documentElement.classList.remove('theme-swap')
            })
            window.setTimeout(() => cancelAnimationFrame(raf2), 60)
          })
          window.setTimeout(() => cancelAnimationFrame(raf1), 60)
        }
        return next
      })
    },
    [],
  )

  const value = useMemo(
    () => ({ theme, toggleTheme }),
    [theme, toggleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  return useContext(ThemeContext)
}
