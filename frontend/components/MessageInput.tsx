'use client'

import { useState, KeyboardEvent, useRef, useEffect } from 'react'

interface MessageInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export default function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }, [message])

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim())
      setMessage('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex gap-3 items-end">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={disabled ? 'Connexion en cours...' : 'Décrivez votre problème...'}
          disabled={disabled}
          rows={1}
          className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-tropical dark:focus:ring-indigo-400 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 resize-none min-h-[48px] max-h-[120px] overflow-y-auto"
        />
      </div>
      <button
        onClick={handleSend}
        disabled={disabled || !message.trim()}
        className="p-3 bg-indigo-tropical dark:bg-indigo-600 text-white rounded-lg hover:bg-indigo-tropical-medium dark:hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center min-w-[48px] h-[48px]"
        aria-label="Envoyer le message"
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
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
      </button>
    </div>
  )
}
