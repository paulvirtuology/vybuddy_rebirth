'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Session } from 'next-auth'
import { useWebSocket } from '@/hooks/useWebSocket'
import axios from 'axios'
import toast from 'react-hot-toast'
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

interface ChatWidgetWindowProps {
  isOpen: boolean
  onClose: () => void
  session: Session | null
  status: 'loading' | 'authenticated' | 'unauthenticated'
  onSignIn: () => void
}

export default function ChatWidgetWindow({
  isOpen,
  onClose,
  session,
  status,
  onSignIn,
}: ChatWidgetWindowProps) {
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [feedbacks, setFeedbacks] = useState<Record<string, { reaction?: 'like' | 'dislike'; comment?: string }>>({})
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMessages, setIsLoadingMessages] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const welcomeMessageSentRef = useRef(false)
  const streamingMessageRef = useRef<string | null>(null)
  const streamBufferRef = useRef<string>('')
  const streamUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const processedMessagesRef = useRef<Set<string>>(new Set())
  const lastProcessedMessageRef = useRef<string | null>(null)
  const loadingRef = useRef(false)
  const loadedSessionIdRef = useRef<string | null>(null)

  const userId = session?.user?.email || 'unknown'
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = (session as any)?.accessToken

  // Créer un nouveau chat
  const handleNewChat = useCallback(async () => {
    if (!token || status !== 'authenticated') return

    const newChatId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    setCurrentChatId(newChatId)

    // Réinitialiser l'état
    setMessages([])
    setFeedbacks({})
    welcomeMessageSentRef.current = false
    streamingMessageRef.current = null
    streamBufferRef.current = ''
    processedMessagesRef.current.clear()
    lastProcessedMessageRef.current = null
    setIsLoading(false)
    loadingRef.current = false
    loadedSessionIdRef.current = null

    // Créer la conversation dans Supabase
    try {
      await axios.post(
        `${apiUrl}/api/v1/conversations/${newChatId}/title?title=Nouveau%20chat`,
        null,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
    } catch (error) {
      console.error('Error creating conversation:', error)
      toast.error('Impossible de créer une nouvelle conversation.')
    }
  }, [apiUrl, token, status])

  // Créer un chat par défaut au premier chargement si authentifié
  useEffect(() => {
    if (status === 'authenticated' && !currentChatId && token) {
      handleNewChat()
    }
  }, [status, currentChatId, token, handleNewChat])

  // WebSocket connection
  const wsUrl = currentChatId
    ? `${process.env.NEXT_PUBLIC_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'}/ws/${currentChatId}`
    : ''
  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(wsUrl)

  // Réinitialiser l'état quand la session change
  useEffect(() => {
    if (currentChatId) {
      setMessages([])
      setFeedbacks({})
      welcomeMessageSentRef.current = false
      streamingMessageRef.current = null
      streamBufferRef.current = ''
      processedMessagesRef.current.clear()
      lastProcessedMessageRef.current = null
      setIsLoading(false)
      loadingRef.current = false
      loadedSessionIdRef.current = null
    }
  }, [currentChatId])

  // Charger les messages depuis Supabase
  useEffect(() => {
    if (!currentChatId || !token || status !== 'authenticated') return
    if (loadingRef.current || loadedSessionIdRef.current === currentChatId) return

    const loadMessages = async () => {
      loadingRef.current = true
      loadedSessionIdRef.current = currentChatId

      try {
        setIsLoadingMessages(true)
        const response = await axios.get(
          `${apiUrl}/api/v1/conversations/${currentChatId}/messages`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        )

        const loadedMessages: Message[] = response.data.messages.map((msg: any) => ({
          id: msg.id,
          type: msg.type === 'user' ? 'user' : 'bot',
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          agent: msg.agent,
          metadata: msg.metadata || {}
        }))

        setMessages(loadedMessages.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime()))
      } catch (error) {
        console.error('Error loading messages:', error)
      } finally {
        setIsLoadingMessages(false)
        loadingRef.current = false
      }
    }

    loadMessages()
  }, [currentChatId, token, apiUrl, status])

  // Gérer la connexion WebSocket
  useEffect(() => {
    setIsConnected(connectionStatus === 'Open')

    // Fetch recent messages on reconnect
    if (connectionStatus === 'Open' && currentChatId && token && !isLoadingMessages) {
      const fetchRecentMessages = async () => {
        await new Promise(resolve => setTimeout(resolve, 1500))
        try {
          const response = await axios.get(
            `${apiUrl}/api/v1/conversations/${currentChatId}/messages`,
            {
              headers: { 'Authorization': `Bearer ${token}` },
              params: { limit: 20 }
            }
          )
          const loadedMessages: Message[] = response.data.messages.map((msg: any) => ({
            id: msg.id,
            type: msg.type === 'user' ? 'user' : 'bot',
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            agent: msg.agent,
            metadata: msg.metadata || {}
          }))

          setMessages(prevMessages => {
            const newMessages = loadedMessages.filter(
              (lm) => !prevMessages.some((pm) => pm.id === lm.id)
            )
            if (newMessages.length > 0) {
              if (newMessages.some(msg => msg.agent === 'human_support')) {
                setIsLoading(false)
              }
              return [...prevMessages, ...newMessages].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
            }
            return prevMessages
          })
        } catch (error) {
          console.error('Error fetching recent messages on reconnect:', error)
        }
      }
      fetchRecentMessages()
    }
  }, [connectionStatus, currentChatId, token, apiUrl, isLoadingMessages])

  // Traiter les messages WebSocket
  useEffect(() => {
    if (!lastMessage || !currentChatId) return

    try {
      const data = JSON.parse(lastMessage.data)

      if (data.type === 'stream_token') {
        if (!streamingMessageRef.current) {
          streamingMessageRef.current = `msg-streaming-${Date.now()}`
          setMessages((prev) => [
            ...prev,
            {
              id: streamingMessageRef.current!,
              type: 'bot',
              content: '',
              timestamp: new Date(),
              agent: data.agent,
            },
          ])
        }

        streamBufferRef.current += data.token

        if (streamUpdateTimeoutRef.current) {
          clearTimeout(streamUpdateTimeoutRef.current)
        }

        streamUpdateTimeoutRef.current = setTimeout(() => {
          if (streamingMessageRef.current) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamingMessageRef.current
                  ? { ...msg, content: streamBufferRef.current }
                  : msg
              )
            )
          }
        }, 50)
      } else if (data.type === 'stream_end') {
        if (streamingMessageRef.current) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamingMessageRef.current
                ? { ...msg, content: streamBufferRef.current }
                : msg
            )
          )
          streamingMessageRef.current = null
          streamBufferRef.current = ''
          setIsLoading(false)
        }
        if (loadingTimeoutRef.current) {
          clearTimeout(loadingTimeoutRef.current)
          loadingTimeoutRef.current = null
        }
      } else if (data.type === 'message') {
        const messageId = data.message_id || `msg-${Date.now()}-${Math.random()}`
        
        if (processedMessagesRef.current.has(messageId)) {
          return
        }

        processedMessagesRef.current.add(messageId)
        lastProcessedMessageRef.current = messageId

        const newMessage: Message = {
          id: messageId,
          type: data.sender === 'user' ? 'user' : 'bot',
          content: data.content || data.message || '',
          timestamp: new Date(data.timestamp || Date.now()),
          agent: data.agent,
          metadata: data.metadata || {},
        }

        setMessages((prev) => {
          const exists = prev.some((m) => m.id === messageId)
          if (exists) return prev
          return [...prev, newMessage].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
        })

        if (data.agent === 'human_support') {
          setIsLoading(false)
        }
      } else if (data.type === 'ticket_created') {
        const ticketMessage: Message = {
          id: `ticket-${Date.now()}`,
          type: 'system',
          content: `Ticket créé dans Odoo (ID: ${data.ticket_id})`,
          timestamp: new Date(),
          metadata: { ticket_id: data.ticket_id },
        }
        setMessages((prev) => [...prev, ticketMessage])
        setIsLoading(false)
      } else if (data.type === 'error') {
        toast.error(data.message || 'Une erreur est survenue')
        setIsLoading(false)
      }
    } catch (e) {
      console.error('Error parsing WebSocket message:', e)
    }
  }, [lastMessage, currentChatId])

  const handleSendMessage = (content: string) => {
    if (!content.trim() || !isConnected || !currentChatId) {
      console.warn('Cannot send message:', { isConnected, hasContent: !!content.trim(), currentChatId })
      return
    }

    if (connectionStatus !== 'Open') {
      toast.error('Connexion non établie. Veuillez réessayer.')
      return
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}-${Math.random()}`,
      type: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current)
    }

    loadingTimeoutRef.current = setTimeout(() => {
      setIsLoading(false)
      streamBufferRef.current = ''
      streamingMessageRef.current = null
      loadingTimeoutRef.current = null
    }, 60000)

    sendMessage({
      message: content,
      user_id: userId,
    })
  }

  // Scroll automatique
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black bg-opacity-20 pointer-events-auto"
        onClick={onClose}
      />

      {/* Fenêtre de chat */}
      <div className="absolute bottom-20 right-4 w-[calc(100vw-2rem)] sm:w-96 h-[calc(100vh-6rem)] sm:h-[600px] max-h-[600px] bg-white dark:bg-gray-900 rounded-lg shadow-2xl flex flex-col pointer-events-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-indigo-tropical text-white rounded-t-lg">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h3 className="font-semibold">VyBuddy Support</h3>
          </div>
          <div className="flex items-center gap-2">
            {status === 'authenticated' && (
              <button
                onClick={handleNewChat}
                className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded transition-colors"
                title="Nouvelle conversation"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded transition-colors"
              title="Fermer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Contenu */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {status === 'loading' ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-tropical"></div>
                <p className="mt-4 text-gray-600 dark:text-gray-400">Chargement...</p>
              </div>
            </div>
          ) : status === 'unauthenticated' ? (
            <div className="flex-1 flex items-center justify-center p-6">
              <div className="text-center w-full">
                <div className="mb-6">
                  <img
                    src="/logo.png"
                    alt="VyBuddy"
                    className="w-16 h-16 mx-auto object-contain mb-4"
                  />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                    Connectez-vous pour commencer
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                    Accédez au support Vygeek en vous connectant avec votre compte Google
                  </p>
                </div>
                <button
                  onClick={onSignIn}
                  className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                  <span>Continuer avec Google</span>
                </button>
                <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                  Accès réservé aux utilisateurs de Virtuology
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800">
                {isLoadingMessages ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-tropical"></div>
                      <p className="mt-4 text-gray-600 dark:text-gray-400">Chargement des messages...</p>
                    </div>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center text-gray-500 dark:text-gray-400">
                      <p className="mb-2">Bonjour ! Comment puis-je vous aider ?</p>
                      <p className="text-sm">Posez votre question ci-dessous</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <MessageList
                      messages={messages}
                      sessionId={currentChatId || ''}
                      feedbacks={feedbacks}
                      setFeedbacks={setFeedbacks}
                    />
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-900">
                <MessageInput
                  onSend={handleSendMessage}
                  disabled={!isConnected || isLoading}
                />
                {isLoading && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
                    VyBuddy réfléchit...
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

