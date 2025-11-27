'use client'

import { useEffect, useState } from 'react'

type Theme = 'light' | 'dark' | 'system'

export function useTheme() {
  const [theme, setTheme] = useState<Theme>('system')
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light')
  const [mounted, setMounted] = useState(false)

  // Initialiser le thème depuis localStorage ou utiliser 'system' par défaut
  useEffect(() => {
    setMounted(true)
    const stored = localStorage.getItem('theme') as Theme | null
    if (stored && ['light', 'dark', 'system'].includes(stored)) {
      setTheme(stored)
    }
  }, [])

  // Calculer le thème résolu (light ou dark) basé sur le thème sélectionné
  useEffect(() => {
    if (!mounted) return

    const root = window.document.documentElement
    root.classList.remove('light', 'dark')

    let resolved: 'light' | 'dark'

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      resolved = systemTheme
    } else {
      resolved = theme
    }

    setResolvedTheme(resolved)
    root.classList.add(resolved)

    // Écouter les changements de préférence système si le thème est 'system'
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = (e: MediaQueryListEvent) => {
        const newResolved = e.matches ? 'dark' : 'light'
        setResolvedTheme(newResolved)
        root.classList.remove('light', 'dark')
        root.classList.add(newResolved)
      }

      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [theme, mounted])

  const setThemeValue = (newTheme: Theme) => {
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
  }

  return {
    theme,
    setTheme: setThemeValue,
    resolvedTheme,
    mounted,
  }
}

