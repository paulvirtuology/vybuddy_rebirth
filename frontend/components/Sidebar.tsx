'use client'

import { useState } from 'react'
import { signOut } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useAdmin } from '@/hooks/useAdmin'
import toast from 'react-hot-toast'

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
  
  const handleSignOut = async () => {
    await signOut({ 
      redirect: true,
      callbackUrl: '/login'
    })
  }

  return (
    <div className="w-64 bg-vert-profond text-white flex flex-col h-screen">
      {/* Header avec logo */}
      <div className="p-6 border-b border-vert-profond-light">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-full bg-indigo-tropical flex items-center justify-center">
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
          <div>
            <h1 className="text-xl font-bold">VyBuddy</h1>
            <p className="text-sm text-gray-300">Support IT</p>
          </div>
        </div>
      </div>

      {/* Bouton Nouveau chat */}
      <div className="p-4">
        <button
          onClick={onNewChat}
          className="w-full bg-white text-vert-profond font-semibold py-3 px-4 rounded-lg hover:bg-sable transition-colors flex items-center justify-center gap-2"
        >
          <svg
            className="w-5 h-5"
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
          Nouveau chat
        </button>
      </div>

      {/* Séparateur */}
      <div className="border-t border-vert-profond-light"></div>

      {/* Historique */}
      <div className="flex-1 overflow-y-auto p-4">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          HISTORIQUE
        </h2>
        <div className="space-y-1">
          {chatHistory.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Aucun chat précédent</p>
          ) : (
            chatHistory.map((chat) => (
              <button
                key={chat.id}
                onClick={() => onSelectChat(chat.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  currentChatId === chat.id
                    ? 'bg-vert-profond-light text-white'
                    : 'text-gray-300 hover:bg-vert-profond-light hover:text-white'
                }`}
              >
                {chat.title}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Footer avec Support téléphonique, Paramètres et Déconnexion */}
      <div className="p-4 border-t border-vert-profond-light space-y-2">
        {isAdmin && (
          <>
            <button
              onClick={() => router.push('/admin/feedbacks')}
              className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-indigo-600 hover:text-white transition-colors flex items-center gap-3"
            >
              <svg
                className="w-5 h-5"
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
              Administration - Feedbacks
            </button>
            <button
              onClick={() => router.push('/admin/knowledge-base')}
              className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-indigo-600 hover:text-white transition-colors flex items-center gap-3"
            >
              <svg
                className="w-5 h-5"
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
              Administration - Base de connaissances
            </button>
          </>
        )}
        <button
          onClick={() => toast('Bientôt disponible')}
          className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-vert-profond-light hover:text-white transition-colors flex items-center gap-3"
        >
          <svg
            className="w-5 h-5"
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
          Support téléphonique
        </button>
        <button
          onClick={() => toast('Bientôt disponible')}
          className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-vert-profond-light hover:text-white transition-colors flex items-center gap-3"
        >
          <svg
            className="w-5 h-5"
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
          Paramètres
        </button>
        <button 
          onClick={handleSignOut}
          className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-red-600 hover:text-white transition-colors flex items-center gap-3"
        >
          <svg
            className="w-5 h-5"
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
          Déconnexion
        </button>
      </div>
    </div>
  )
}

