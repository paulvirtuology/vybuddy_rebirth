'use client'

import { useState, useEffect, useRef } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import MessageList from './MessageList'
import MessageInput from './MessageInput'

interface Message {
  id: string
  type: 'user' | 'bot' | 'system'
  content: string
  timestamp: Date
  agent?: string
  metadata?: any
}

interface ChatInterfaceProps {
  sessionId: string
  userId: string
  onTitleUpdate?: (title: string) => void
}

export default function ChatInterface({
  sessionId,
  userId,
  onTitleUpdate,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const welcomeMessageSentRef = useRef(false)
  const streamingMessageRef = useRef<string | null>(null)

  const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'}/ws/${sessionId}`
  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(wsUrl)

  // Réinitialiser les messages et le flag de bienvenue quand la session change
  useEffect(() => {
    setMessages([])
    welcomeMessageSentRef.current = false
  }, [sessionId])

  useEffect(() => {
    setIsConnected(connectionStatus === 'Open')
  }, [connectionStatus])

  // Message de bienvenue initial - une seule fois quand la connexion est établie
  useEffect(() => {
    if (connectionStatus === 'Open' && !welcomeMessageSentRef.current) {
      // Vérifier que messages est vide avant d'ajouter le message de bienvenue
      setMessages((prev) => {
        if (prev.length === 0) {
          welcomeMessageSentRef.current = true
          const welcomeMessage: Message = {
            id: `msg-welcome-${Date.now()}`,
            type: 'bot',
            content: 'Bonjour! 👋 Je suis **VyBuddy**, votre assistant support IT de **VyGeek**. Je suis ravi de vous aider ! Comment puis-je vous assister aujourd\'hui ?',
            timestamp: new Date(),
            agent: 'system',
          }
          return [welcomeMessage]
        }
        return prev
      })
    }
  }, [connectionStatus]) // Seulement connectionStatus dans les dépendances

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data)

        if (data.type === 'stream_start') {
          // Début du streaming : créer un nouveau message vide
          setMessages((prev) => {
            const botMessage: Message = {
              id: `msg-streaming-${Date.now()}`,
              type: 'bot',
              content: '',
              timestamp: new Date(),
              agent: data.agent || 'processing',
              metadata: {},
            }
            streamingMessageRef.current = botMessage.id
            return [...prev, botMessage]
          })
        } else if (data.type === 'stream') {
          // Token reçu : ajouter au message en cours
          setMessages((prev) => {
            return prev.map((msg) => {
              if (msg.id === streamingMessageRef.current) {
                return {
                  ...msg,
                  content: msg.content + data.token,
                  agent: data.agent || msg.agent,
                }
              }
              return msg
            })
          })
        } else if (data.type === 'stream_end') {
          // Fin du streaming : finaliser le message
          setMessages((prev) => {
            const updatedMessages = prev.map((msg) => {
              if (msg.id === streamingMessageRef.current) {
                return {
                  ...msg,
                  content: data.message || msg.content,
                  agent: data.agent || msg.agent,
                  metadata: data.metadata || {},
                }
              }
              return msg
            })
            
            // Mettre à jour le titre du chat avec le premier message utilisateur
            const firstUserMessage = updatedMessages.find((msg) => msg.type === 'user')
            if (firstUserMessage && onTitleUpdate) {
              const title = firstUserMessage.content.length > 30
                ? firstUserMessage.content.substring(0, 30) + '...'
                : firstUserMessage.content
              onTitleUpdate(title)
            }
            
            streamingMessageRef.current = null
            return updatedMessages
          })
        } else if (data.type === 'response') {
          // Fallback pour les réponses non-streamées (compatibilité)
          setMessages((prev) => {
            const isDuplicate = prev.some(
              (msg) => msg.content === data.message && msg.agent === data.agent
            )
            
            if (isDuplicate) {
              return prev
            }

            const botMessage: Message = {
              id: `msg-${Date.now()}-${Math.random()}`,
              type: 'bot',
              content: data.message,
              timestamp: new Date(),
              agent: data.agent,
              metadata: data.metadata,
            }

            const updatedMessages = [...prev, botMessage]
            const firstUserMessage = updatedMessages.find((msg) => msg.type === 'user')
            if (firstUserMessage && onTitleUpdate) {
              const title = firstUserMessage.content.length > 30
                ? firstUserMessage.content.substring(0, 30) + '...'
                : firstUserMessage.content
              onTitleUpdate(title)
            }

            return updatedMessages
          })
        } else if (data.type === 'error') {
          setMessages((prev) => {
            const errorMessage: Message = {
              id: `msg-error-${Date.now()}-${Math.random()}`,
              type: 'system',
              content: data.message,
              timestamp: new Date(),
            }
            return [...prev, errorMessage]
          })
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e)
      }
    }
  }, [lastMessage, onTitleUpdate])

  const handleSendMessage = (content: string) => {
    if (!content.trim() || !isConnected) return

    // Ajout du message utilisateur
    const userMessage: Message = {
      id: `msg-${Date.now()}-${Math.random()}`,
      type: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Mettre à jour le titre si c'est le premier message
    if (messages.length <= 1 && onTitleUpdate) {
      const title = content.length > 30 ? content.substring(0, 30) + '...' : content
      onTitleUpdate(title)
    }

    // Envoi via WebSocket
    sendMessage({
      message: content,
      user_id: userId,
    })
  }

  // Scroll automatique vers le bas
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full bg-blanc">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Chat Support</h2>
          <p className="text-sm text-gray-500">Assistant IA - Temps réel</p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="px-6 py-3 bg-sable-lighter border-b border-sable">
        <div className="flex items-start gap-2">
          <svg
            className="w-5 h-5 text-indigo-tropical flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-xs text-gray-600 leading-relaxed">
            <span className="font-semibold">VyBuddy est en phase d'apprentissage</span> - Il apprend de chaque interaction pour mieux vous servir. Merci de votre patience et de votre bienveillance ! 🙏
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <MessageList messages={messages} />
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-200 bg-sable-lighter">
        <MessageInput onSend={handleSendMessage} disabled={!isConnected} />
        <p className="text-xs text-gray-500 mt-2 text-center">
          VyBuddy répondra dans les meilleurs délais. Temps moyen: 2 minutes
        </p>
      </div>
    </div>
  )
}
