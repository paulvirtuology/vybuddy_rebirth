'use client'

import { useState, useEffect } from 'react'
import { signOut } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useAdmin } from '@/hooks/useAdmin'
import toast from 'react-hot-toast'
import ThemeSwitch from './ThemeSwitch'

interface ChatHistory {
  id: string
  title: string
  timestamp: Date
}

interface SidebarProps {
  currentChatId: string | null
  onNewChat: () => void
  onSelectChat: (chatId: string) => void
  chatHistory: ChatHistory[]
}

export default function Sidebar({
  currentChatId,
  onNewChat,
  onSelectChat,
  chatHistory,
}: SidebarProps) {
  const router = useRouter()
  const { isAdmin } = useAdmin()
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  // Charger l'état de la sidebar depuis localStorage
  useEffect(() => {
    const savedState = localStorage.getItem('sidebarCollapsed')
    if (savedState !== null) {
      setIsCollapsed(savedState === 'true')
    }
  }, [])
  
  // Sauvegarder l'état dans localStorage
  const toggleCollapse = () => {
    const newState = !isCollapsed
    setIsCollapsed(newState)
    localStorage.setItem('sidebarCollapsed', String(newState))
  }
  
  const handleSignOut = async () => {
    await signOut({ 
      redirect: true,
      callbackUrl: '/login'
    })
  }

  return (
    <>
      {/* Mobile menu button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-vert-profond text-white dark:bg-gray-800 dark:text-gray-200"
        aria-label="Toggle menu"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          {isMobileOpen ? (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          ) : (
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          )}
        </svg>
      </button>

      {/* Overlay pour mobile */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-40
        ${isCollapsed ? 'w-16' : 'w-64'} bg-vert-profond dark:bg-gray-900 text-white flex flex-col h-screen
        transform transition-all duration-300 ease-in-out
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
      {/* Header avec logo et bouton collapse */}
          <div className="p-4 lg:p-6 border-b border-vert-profond-light dark:border-gray-700">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-full bg-indigo-tropical flex items-center justify-center flex-shrink-0">
            <svg
              className="w-6 h-6 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold truncate">VyBuddy</h1>
              <p className="text-sm text-gray-300 dark:text-gray-400 truncate">Support IT</p>
            </div>
          )}
          {/* Bouton collapse (desktop seulement) */}
          <button
            onClick={toggleCollapse}
            className="hidden lg:flex items-center justify-center w-8 h-8 rounded-lg hover:bg-vert-profond-light dark:hover:bg-gray-800 transition-colors flex-shrink-0"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={isCollapsed ? 'Développer' : 'Réduire'}
          >
            <svg
              className={`w-5 h-5 transition-transform ${isCollapsed ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Bouton Nouveau chat */}
      <div className="p-4">
        <button
          onClick={() => {
            onNewChat()
            setIsMobileOpen(false)
          }}
          className={`w-full bg-white dark:bg-gray-800 text-vert-profond dark:text-white font-semibold py-3 ${isCollapsed ? 'px-3' : 'px-4'} rounded-lg hover:bg-sable dark:hover:bg-gray-700 transition-colors flex items-center justify-center gap-2`}
          title={isCollapsed ? 'Nouveau chat' : undefined}
        >
          <svg
            className="w-5 h-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          {!isCollapsed && <span className="truncate">Nouveau chat</span>}
        </button>
      </div>

      {/* Séparateur */}
      <div className="border-t border-vert-profond-light dark:border-gray-700"></div>

      {/* Historique */}
      <div className="flex-1 overflow-y-auto p-4">
        {!isCollapsed && (
          <h2 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-3">
            HISTORIQUE
          </h2>
        )}
        <div className="space-y-1">
          {chatHistory.length === 0 ? (
            !isCollapsed && (
              <p className="text-sm text-gray-400 dark:text-gray-500 italic">Aucun chat précédent</p>
            )
          ) : (
            chatHistory.map((chat) => (
              <button
                key={chat.id}
                onClick={() => {
                  onSelectChat(chat.id)
                  setIsMobileOpen(false)
                }}
                className={`w-full ${isCollapsed ? 'flex items-center justify-center' : 'text-left'} px-3 py-2 rounded-lg text-sm transition-colors ${
                  currentChatId === chat.id
                    ? 'bg-vert-profond-light dark:bg-gray-800 text-white'
                    : 'text-gray-300 dark:text-gray-400 hover:bg-vert-profond-light dark:hover:bg-gray-800 hover:text-white'
                }`}
                title={isCollapsed ? chat.title : undefined}
              >
                {isCollapsed ? (
                  <div className="w-2 h-2 rounded-full bg-indigo-tropical"></div>
                ) : (
                  <span className="truncate block">{chat.title}</span>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Footer avec Support téléphonique, Paramètres, Thème et Déconnexion */}
      <div className="p-4 border-t border-vert-profond-light dark:border-gray-700 space-y-2">
        {/* Theme Switch */}
        {!isCollapsed && (
          <div className="mb-4">
            <ThemeSwitch />
          </div>
        )}
        {isAdmin && (
          <>
            <button
              onClick={() => {
                router.push('/admin/feedbacks')
                setIsMobileOpen(false)
              }}
              className={`w-full ${isCollapsed ? 'flex items-center justify-center' : 'text-left'} px-3 py-2 rounded-lg text-sm text-gray-300 dark:text-gray-400 hover:bg-indigo-600 dark:hover:bg-gray-800 hover:text-white transition-colors flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}
              title={isCollapsed ? 'Administration - Feedbacks' : undefined}
            >
              <svg
                className="w-5 h-5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              {!isCollapsed && <span className="truncate">Administration - Feedbacks</span>}
            </button>
            <button
              onClick={() => {
                router.push('/admin/knowledge-base')
                setIsMobileOpen(false)
              }}
              className={`w-full ${isCollapsed ? 'flex items-center justify-center' : 'text-left'} px-3 py-2 rounded-lg text-sm text-gray-300 dark:text-gray-400 hover:bg-indigo-600 dark:hover:bg-gray-800 hover:text-white transition-colors flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}
              title={isCollapsed ? 'Administration - Base de connaissances' : undefined}
            >
              <svg
                className="w-5 h-5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
              {!isCollapsed && <span className="truncate">Administration - Base de connaissances</span>}
            </button>
          </>
        )}
        <button
          onClick={() => {
            toast('Bientôt disponible')
            setIsMobileOpen(false)
          }}
          className={`w-full ${isCollapsed ? 'flex items-center justify-center' : 'text-left'} px-3 py-2 rounded-lg text-sm text-gray-300 dark:text-gray-400 hover:bg-vert-profond-light dark:hover:bg-gray-800 hover:text-white transition-colors flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}
          title={isCollapsed ? 'Support téléphonique' : undefined}
        >
          <svg
            className="w-5 h-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
            />
          </svg>
          {!isCollapsed && <span className="truncate">Support téléphonique</span>}
        </button>
        <button
          onClick={() => {
            toast('Bientôt disponible')
            setIsMobileOpen(false)
          }}
          className={`w-full ${isCollapsed ? 'flex items-center justify-center' : 'text-left'} px-3 py-2 rounded-lg text-sm text-gray-300 dark:text-gray-400 hover:bg-vert-profond-light dark:hover:bg-gray-800 hover:text-white transition-colors flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}
          title={isCollapsed ? 'Paramètres' : undefined}
        >
          <svg
            className="w-5 h-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          {!isCollapsed && <span className="truncate">Paramètres</span>}
        </button>
        <button 
          onClick={() => {
            handleSignOut()
            setIsMobileOpen(false)
          }}
          className={`w-full ${isCollapsed ? 'flex items-center justify-center' : 'text-left'} px-3 py-2 rounded-lg text-sm text-gray-300 dark:text-gray-400 hover:bg-red-600 dark:hover:bg-red-800 hover:text-white transition-colors flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}
          title={isCollapsed ? 'Déconnexion' : undefined}
        >
          <svg
            className="w-5 h-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          {!isCollapsed && <span className="truncate">Déconnexion</span>}
        </button>
      </div>
    </div>
    </>
  )
}

