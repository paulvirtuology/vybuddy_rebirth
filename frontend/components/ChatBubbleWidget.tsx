'use client'

import { useState, useEffect } from 'react'
import { useSession, signIn } from 'next-auth/react'
import ChatWidgetWindow from './ChatWidgetWindow'

interface ChatBubbleWidgetProps {
  /** Position du widget sur l'écran */
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
  /** Couleur du bouton (optionnel) */
  buttonColor?: string
  /** Taille du bouton (optionnel) */
  buttonSize?: 'small' | 'medium' | 'large'
}

export default function ChatBubbleWidget({
  position = 'bottom-right',
  buttonColor = 'bg-indigo-tropical',
  buttonSize = 'large',
}: ChatBubbleWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const { data: session, status } = useSession()

  // Fermer le widget si l'utilisateur se déconnecte
  useEffect(() => {
    if (status === 'unauthenticated') {
      setIsOpen(false)
    }
  }, [status])

  const positionClasses = {
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
  }

  const sizeClasses = {
    small: 'w-12 h-12',
    medium: 'w-14 h-14',
    large: 'w-16 h-16',
  }

  const iconSizeClasses = {
    small: 'w-6 h-6',
    medium: 'w-7 h-7',
    large: 'w-8 h-8',
  }

  return (
    <>
      {/* Bouton flottant */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          fixed ${positionClasses[position]} z-50
          ${sizeClasses[buttonSize]}
          ${buttonColor} text-white
          rounded-full shadow-lg
          hover:shadow-xl
          transition-all duration-300
          flex items-center justify-center
          group
        `}
        aria-label="Ouvrir le chat"
      >
        {isOpen ? (
          <svg
            className={`${iconSizeClasses[buttonSize]} transition-transform duration-300`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        ) : (
          <svg
            className={`${iconSizeClasses[buttonSize]} transition-transform duration-300 group-hover:scale-110`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        )}
      </button>

      {/* Fenêtre de chat */}
      {isOpen && (
        <ChatWidgetWindow
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          session={session}
          status={status}
          onSignIn={() => signIn('google', { callbackUrl: window.location.href })}
        />
      )}
    </>
  )
}

