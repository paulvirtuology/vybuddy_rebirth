'use client'

import { useTheme } from '@/hooks/useTheme'

export default function ThemeSwitch() {
  const { theme, setTheme, resolvedTheme, mounted } = useTheme()

  if (!mounted) {
    // Éviter le flash de contenu non stylé
    return (
      <div className="w-full px-3 py-2">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
      </div>
    )
  }

  return (
    <div className="w-full px-3 py-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-300 dark:text-gray-400">
          Thème
        </span>
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => setTheme('light')}
          className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
            theme === 'light'
              ? 'bg-white text-vert-profond dark:bg-gray-700 dark:text-white'
              : 'bg-vert-profond-light text-gray-300 hover:bg-vert-profond-medium dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
          }`}
          title="Clair"
        >
          <div className="flex flex-col items-center gap-1">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
              />
            </svg>
            <span>Clair</span>
          </div>
        </button>
        <button
          onClick={() => setTheme('dark')}
          className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
            theme === 'dark'
              ? 'bg-white text-vert-profond dark:bg-gray-700 dark:text-white'
              : 'bg-vert-profond-light text-gray-300 hover:bg-vert-profond-medium dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
          }`}
          title="Sombre"
        >
          <div className="flex flex-col items-center gap-1">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
              />
            </svg>
            <span>Sombre</span>
          </div>
        </button>
        <button
          onClick={() => setTheme('system')}
          className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
            theme === 'system'
              ? 'bg-white text-vert-profond dark:bg-gray-700 dark:text-white'
              : 'bg-vert-profond-light text-gray-300 hover:bg-vert-profond-medium dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
          }`}
          title="Système"
        >
          <div className="flex flex-col items-center gap-1">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
            <span>Système</span>
          </div>
        </button>
      </div>
    </div>
  )
}

