'use client'

import { memo } from 'react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

interface Message {
  id: string
  type: 'user' | 'bot' | 'system'
  content: string
  timestamp: Date
  agent?: string
  metadata?: any
}

interface MessageListProps {
  messages: Message[]
}

// Composant de message individuel mémorisé pour éviter les re-renders inutiles
const MessageItem = memo(({ message }: { message: Message }) => {
  return (
    <div
      className={`flex ${
        message.type === 'user' ? 'justify-end' : 'justify-start'
      }`}
    >
      <div
        className={`max-w-[75%] rounded-lg px-4 py-3 ${
          message.type === 'user'
            ? 'bg-gray-200 text-gray-900'
            : message.type === 'system'
            ? 'bg-yellow-50 text-yellow-800 border border-yellow-200'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {message.content}
        </div>
        <div
          className={`text-xs mt-2 flex items-center gap-2 ${
            message.type === 'user'
              ? 'text-gray-500'
              : 'text-gray-500'
          }`}
        >
          <span>{format(message.timestamp, 'HH:mm', { locale: fr })}</span>
          {message.agent && message.type === 'bot' && (
            <>
              <span>•</span>
              <span>Agent: {message.agent}</span>
            </>
          )}
        </div>
        {message.metadata?.ticket_created && (
          <div className="mt-3 bg-green-50 border border-green-200 text-green-800 px-3 py-2 rounded text-xs flex items-center gap-2">
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
                d="M5 13l4 4L19 7"
              />
            </svg>
            Ticket créé (ID: {message.metadata.ticket_id})
          </div>
        )}
      </div>
    </div>
  )
})

MessageItem.displayName = 'MessageItem'

function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <p className="text-lg mb-2">👋 Bonjour !</p>
          <p>Comment puis-je vous aider aujourd'hui ?</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
    </div>
  )
}

export default memo(MessageList)
