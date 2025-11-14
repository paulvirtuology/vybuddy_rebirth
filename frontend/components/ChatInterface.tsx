'use client'

import { useState, useEffect, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { useWebSocket } from '@/hooks/useWebSocket'
import axios from 'axios'
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
  const { data: session } = useSession()
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMessages, setIsLoadingMessages] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const welcomeMessageSentRef = useRef(false)
  const streamingMessageRef = useRef<string | null>(null)
  
  // Buffer pour batching des tokens de streaming
  const streamBufferRef = useRef<string>('')
  const streamUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  // Track des messages déjà traités pour éviter les doublons
  const processedMessagesRef = useRef<Set<string>>(new Set())
  const lastProcessedMessageRef = useRef<string | null>(null)

  const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'}/ws/${sessionId}`
  const { sendMessage, lastMessage, connectionStatus } = useWebSocket(wsUrl)
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = (session as any)?.accessToken

  // Ref pour éviter les chargements multiples et tracker la session chargée
  const loadingRef = useRef(false)
  const loadedSessionIdRef = useRef<string | null>(null)
  
  // Charger les messages depuis Supabase UNIQUEMENT au changement de session
  useEffect(() => {
    if (!sessionId || !token) return
    
    // Ne charger que si c'est une nouvelle session (pas déjà chargée)
    if (loadingRef.current || loadedSessionIdRef.current === sessionId) return
    
    const loadMessages = async () => {
      loadingRef.current = true
      loadedSessionIdRef.current = sessionId
      
      try {
        setIsLoadingMessages(true)
        const response = await axios.get(
          `${apiUrl}/api/v1/conversations/${sessionId}/messages`,
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
        
        setMessages(loadedMessages)
        
        // Si des messages existent, ne pas afficher le message de bienvenue
        if (loadedMessages.length > 0) {
          welcomeMessageSentRef.current = true
        }
        
        // Si c'est le premier message utilisateur, mettre à jour le titre
        const firstUserMessage = loadedMessages.find(m => m.type === 'user')
        if (firstUserMessage && onTitleUpdate) {
          const title = firstUserMessage.content.length > 30 
            ? firstUserMessage.content.substring(0, 30) + '...' 
            : firstUserMessage.content
          onTitleUpdate(title)
        }
      } catch (error) {
        console.error('Error loading messages:', error)
        // En cas d'erreur, on continue avec un historique vide
        setMessages([])
      } finally {
        setIsLoadingMessages(false)
        loadingRef.current = false
      }
    }
    
    loadMessages()
  }, [sessionId]) // UNIQUEMENT sessionId - ne pas recharger si token ou apiUrl change

  // Réinitialiser les messages et le flag de bienvenue quand la session change
  useEffect(() => {
    // Ne pas réinitialiser si on charge les messages depuis Supabase
    // Les messages seront chargés par le useEffect de loadMessages
    welcomeMessageSentRef.current = false
    streamingMessageRef.current = null
    streamBufferRef.current = ''
    processedMessagesRef.current.clear() // Nettoyer les messages traités
    lastProcessedMessageRef.current = null // Réinitialiser le dernier message traité
    setIsLoading(false) // Réinitialiser le loading
    loadingRef.current = false // Réinitialiser le flag de chargement
    loadedSessionIdRef.current = null // Réinitialiser la session chargée pour permettre le rechargement
    if (streamUpdateTimeoutRef.current) {
      clearTimeout(streamUpdateTimeoutRef.current)
      streamUpdateTimeoutRef.current = null
    }
    // Note: Le WebSocket se reconnectera automatiquement via useWebSocket
    // car l'URL change avec le sessionId
  }, [sessionId])
  
  // Nettoyage au démontage
  useEffect(() => {
    return () => {
      if (streamUpdateTimeoutRef.current) {
        clearTimeout(streamUpdateTimeoutRef.current)
      }
    }
  }, [])

  useEffect(() => {
    setIsConnected(connectionStatus === 'Open')
  }, [connectionStatus])

  // Message de bienvenue initial - une seule fois quand la connexion est établie et qu'il n'y a pas de messages
  useEffect(() => {
    // Ne pas afficher le message de bienvenue si on charge encore les messages ou s'il y a déjà des messages
    if (isLoadingMessages || welcomeMessageSentRef.current) return
    
    if (connectionStatus === 'Open' && messages.length === 0) {
      welcomeMessageSentRef.current = true
      const welcomeMessage: Message = {
        id: `msg-welcome-${Date.now()}`,
        type: 'bot',
        content: 'Bonjour! 👋 Je suis **VyBuddy**, votre assistant support IT de **VyGeek**. Je suis ravi de vous aider ! Comment puis-je vous assister aujourd\'hui ?',
        timestamp: new Date(),
        agent: 'system',
      }
      setMessages([welcomeMessage])
    }
  }, [connectionStatus, isLoadingMessages]) // Retiré messages.length des dépendances pour éviter les boucles

  useEffect(() => {
    if (lastMessage) {
      // Vérifier si c'est exactement le même message que le précédent
      const messageKey = `${lastMessage.data}-${lastMessage.timeStamp || Date.now()}`
      if (lastProcessedMessageRef.current === messageKey) {
        return // Ignorer les messages identiques
      }
      lastProcessedMessageRef.current = messageKey
      
      try {
        const data = JSON.parse(lastMessage.data)
        
        // Créer un identifiant unique pour ce message WebSocket
        const messageId = `${data.type}-${data.message?.substring(0, 30) || data.token?.substring(0, 10) || Date.now()}`
        
        // Ignorer les messages déjà traités (sauf pour stream qui doit être traité plusieurs fois)
        if (data.type !== 'stream' && processedMessagesRef.current.has(messageId)) {
          return // Ignorer les doublons
        }
        
        // Marquer comme traité (sauf pour stream)
        if (data.type !== 'stream') {
          processedMessagesRef.current.add(messageId)
        }

        if (data.type === 'stream_start') {
          // Début du streaming : activer le loading et créer un nouveau message vide
          setIsLoading(true)
          const streamId = `stream-${Date.now()}`
          if (!streamingMessageRef.current) {
            setMessages((prev) => {
              // Vérifier qu'on n'a pas déjà un message en streaming
              const existingStreaming = prev.find((msg) => 
                msg.id === streamingMessageRef.current && msg.content === ''
              )
              if (existingStreaming) {
                return prev
              }
              
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
          }
        } else if (data.type === 'stream') {
          // Token reçu : ajouter au buffer (batching pour éviter trop de re-renders)
          streamBufferRef.current += data.token
          
          // Annuler le timeout précédent
          if (streamUpdateTimeoutRef.current) {
            clearTimeout(streamUpdateTimeoutRef.current)
          }
          
          // Mettre à jour l'état toutes les 150ms ou immédiatement si le buffer est trop grand (>50 chars)
          const shouldUpdateNow = streamBufferRef.current.length > 50
          const delay = shouldUpdateNow ? 0 : 150
          
          streamUpdateTimeoutRef.current = setTimeout(() => {
            const tokensToAdd = streamBufferRef.current
            streamBufferRef.current = '' // Vider le buffer
            
            setMessages((prev) => {
              // Vérifier si le message existe déjà
              const streamingMsg = prev.find((msg) => msg.id === streamingMessageRef.current)
              if (!streamingMsg) {
                // Si le message n'existe pas, créer un nouveau message
                const newMessage: Message = {
                  id: streamingMessageRef.current || `msg-streaming-${Date.now()}`,
                  type: 'bot',
                  content: tokensToAdd,
                  timestamp: new Date(),
                  agent: data.agent || 'processing',
                  metadata: {},
                }
                if (!streamingMessageRef.current) {
                  streamingMessageRef.current = newMessage.id
                }
                return [...prev, newMessage]
              }
              
              // Mettre à jour uniquement le message en cours (garder l'agent "processing" pendant le streaming)
              return prev.map((msg) => {
                if (msg.id === streamingMessageRef.current) {
                  return {
                    ...msg,
                    content: msg.content + tokensToAdd,
                    // Ne pas changer l'agent pendant le streaming, il sera mis à jour dans stream_end
                  }
                }
                return msg
              })
            })
          }, delay)
        } else if (data.type === 'stream_end') {
          // Fin du streaming : nettoyer le buffer et finaliser le message
          // Créer un identifiant unique basé UNIQUEMENT sur le contenu (ignorer l'agent pour éviter les doublons)
          const finalMessage = data.message || ''
          const contentHash = finalMessage.substring(0, 150).trim() // Utiliser les 150 premiers caractères comme identifiant
          const streamEndId = `stream_end-${contentHash}`
          
          // Vérifier si un message avec le même contenu existe déjà (peu importe l'agent)
          const existingDuplicate = messages.find((msg) => 
            msg.type === 'bot' &&
            msg.content.trim() === finalMessage.trim() &&
            finalMessage.length > 0
          )
          
          if (existingDuplicate) {
            // Le message existe déjà, ne pas le dupliquer
            console.log('Ignoring duplicate message (same content)', contentHash.substring(0, 50))
            streamBufferRef.current = ''
            streamingMessageRef.current = null
            setIsLoading(false)
            return
          }
          
          // Vérifier si ce stream_end a déjà été traité
          if (processedMessagesRef.current.has(streamEndId)) {
            console.log('Ignoring duplicate stream_end', contentHash.substring(0, 50))
            return // Ignorer les doublons
          }
          
          processedMessagesRef.current.add(streamEndId)
          
          if (streamUpdateTimeoutRef.current) {
            clearTimeout(streamUpdateTimeoutRef.current)
            streamUpdateTimeoutRef.current = null
          }
          
          setMessages((prev) => {
            // Trouver le message en streaming
            const streamingMsg = prev.find((msg) => msg.id === streamingMessageRef.current)
            
            // Si le message en streaming existe, le remplacer complètement
            if (streamingMsg) {
              const updatedMessages = prev.map((msg) => {
                if (msg.id === streamingMessageRef.current) {
                  // Remplacer complètement le message streamé par le message final
                  return {
                    ...msg,
                    content: finalMessage,
                    agent: data.agent || 'unknown',
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
              
              // Nettoyer le buffer
              streamBufferRef.current = ''
              streamingMessageRef.current = null
              setIsLoading(false) // Désactiver le loading à la fin du streaming
              return updatedMessages
            }
            
            // Si le message en streaming n'existe pas, vérifier s'il y a déjà un message avec le même contenu
            const existingMessage = prev.find((msg) => 
              msg.type === 'bot' &&
              msg.content.trim() === finalMessage.trim() &&
              finalMessage.length > 0
            )
            
            if (existingMessage) {
              // Le message existe déjà, ne pas le dupliquer
              streamBufferRef.current = ''
              streamingMessageRef.current = null
              setIsLoading(false)
              return prev
            }
            
            // Créer un nouveau message si aucun n'existe
            const newMessage: Message = {
              id: streamingMessageRef.current || `msg-${Date.now()}`,
              type: 'bot',
              content: finalMessage,
              timestamp: new Date(),
              agent: data.agent || 'unknown',
              metadata: data.metadata || {},
            }
            
            const updatedMessages = [...prev, newMessage]
            
            // Mettre à jour le titre du chat avec le premier message utilisateur
            const firstUserMessage = updatedMessages.find((msg) => msg.type === 'user')
            if (firstUserMessage && onTitleUpdate) {
              const title = firstUserMessage.content.length > 30
                ? firstUserMessage.content.substring(0, 30) + '...'
                : firstUserMessage.content
              onTitleUpdate(title)
            }
            
            // Nettoyer le buffer
            streamBufferRef.current = ''
            streamingMessageRef.current = null
            setIsLoading(false) // Désactiver le loading à la fin du streaming
            return updatedMessages
          })
        } else if (data.type === 'response') {
          // Fallback pour les réponses non-streamées (compatibilité)
          setIsLoading(false) // Désactiver le loading
          setMessages((prev) => {
            // Vérifier les doublons basés uniquement sur le contenu (ignorer l'agent)
            const isDuplicate = prev.some(
              (msg) => msg.type === 'bot' && msg.content.trim() === data.message.trim()
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
          setIsLoading(false) // Désactiver le loading en cas d'erreur
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

    // Activer le loading avant l'envoi
    setIsLoading(true)

    // Envoi via WebSocket
    sendMessage({
      message: content,
      user_id: userId,
    })
  }

  // Scroll automatique vers le bas (optimisé : throttling agressif)
  useEffect(() => {
    // Throttle le scroll pour éviter trop d'updates pendant le streaming
    let timeoutId: NodeJS.Timeout | null = null
    const scroll = () => {
      if (timeoutId) clearTimeout(timeoutId)
      timeoutId = setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' }) // 'auto' au lieu de 'smooth' pour moins de calculs
      }, 200) // Délai plus long pour regrouper les updates de streaming
    }
    
    scroll()
    
    return () => {
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [messages.length]) // Seulement la longueur, pas le contenu

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
            {isLoadingMessages ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-tropical"></div>
                  <p className="mt-4 text-gray-600">Chargement de l'historique...</p>
                </div>
              </div>
            ) : (
              <MessageList messages={messages} />
            )}
        {/* Indicateur de chargement */}
        {isLoading && (
          <div className="flex justify-start mt-4">
            <div className="bg-gray-100 rounded-lg px-4 py-3 max-w-[75%]">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5 items-center">
                  <div 
                    className="w-2 h-2 bg-indigo-tropical rounded-full animate-bounce" 
                    style={{ animationDelay: '0ms', animationDuration: '1.4s' }}
                  ></div>
                  <div 
                    className="w-2 h-2 bg-indigo-tropical rounded-full animate-bounce" 
                    style={{ animationDelay: '200ms', animationDuration: '1.4s' }}
                  ></div>
                  <div 
                    className="w-2 h-2 bg-indigo-tropical rounded-full animate-bounce" 
                    style={{ animationDelay: '400ms', animationDuration: '1.4s' }}
                  ></div>
                </div>
                <span className="text-xs text-gray-500 ml-2">VyBuddy réfléchit...</span>
              </div>
            </div>
          </div>
        )}
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
