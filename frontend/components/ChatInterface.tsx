'use client'

import { useState, useEffect, useRef } from 'react'
import { useSession } from 'next-auth/react'
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
  const [feedbacks, setFeedbacks] = useState<Record<string, { reaction?: 'like' | 'dislike'; comment?: string }>>({})
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMessages, setIsLoadingMessages] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const welcomeMessageSentRef = useRef(false)
  const streamingMessageRef = useRef<string | null>(null)
  
  // Buffer pour batching des tokens de streaming
  const streamBufferRef = useRef<string>('')
  const streamUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
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
  
  // Réinitialiser l'état AVANT de charger les messages quand la session change
  useEffect(() => {
    // Réinitialiser complètement l'état pour une nouvelle session
    setMessages([]) // Vider les messages immédiatement
    setFeedbacks({}) // Vider les feedbacks
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
  
  // Charger les messages depuis Supabase UNIQUEMENT au changement de session
  // IMPORTANT: Ce useEffect s'exécute APRÈS la réinitialisation ci-dessus
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
        
        // Vérifier que nous sommes toujours sur la même session avant de mettre à jour
        if (loadedSessionIdRef.current === sessionId) {
          setMessages(loadedMessages)
          
          // Charger tous les feedbacks en batch pour les messages bots avec UUID valides
          const isValidUUID = (id: string): boolean => {
            const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
            return uuidRegex.test(id)
          }
          
          const botMessageIds = loadedMessages
            .filter(msg => msg.type === 'bot' && msg.id && isValidUUID(msg.id))
            .map(msg => msg.id)
          
          if (botMessageIds.length > 0 && token) {
            try {
              const feedbackResponse = await axios.post(
                `${apiUrl}/api/v1/feedbacks/messages/batch`,
                { interaction_ids: botMessageIds },
                {
                  headers: {
                    'Authorization': `Bearer ${token}`
                  }
                }
              )
              
              // Vérifier à nouveau que nous sommes toujours sur la même session
              if (loadedSessionIdRef.current === sessionId) {
                // Convertir en format {id: {reaction, comment}}
                const feedbacksMap: Record<string, { reaction?: 'like' | 'dislike'; comment?: string }> = {}
                const feedbacksData = feedbackResponse.data.feedbacks || {}
                
                for (const [id, feedback] of Object.entries(feedbacksData)) {
                  const fb = feedback as any
                  feedbacksMap[id] = {
                    reaction: fb.reaction || undefined,
                    comment: fb.comment || undefined
                  }
                }
                
                setFeedbacks(feedbacksMap)
              }
        } catch (error) {
          console.error('Error loading feedbacks batch:', error)
          toast.error('Impossible de charger les retours sur les messages.')
          // En cas d'erreur, continuer sans feedbacks
        }
          }
          
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
        }
      } catch (error) {
        console.error('Error loading messages:', error)
        toast.error('Impossible de charger l’historique de la conversation.')
        // En cas d'erreur, on continue avec un historique vide
        // Vérifier que nous sommes toujours sur la même session
        if (loadedSessionIdRef.current === sessionId) {
          setMessages([])
        }
      } finally {
        // Vérifier que nous sommes toujours sur la même session avant de réinitialiser
        if (loadedSessionIdRef.current === sessionId) {
          setIsLoadingMessages(false)
          loadingRef.current = false
        }
      }
    }
    
    loadMessages()
  }, [sessionId, token, apiUrl]) // Inclure token et apiUrl pour éviter les warnings
  
  // Nettoyage au démontage
  useEffect(() => {
    return () => {
      if (streamUpdateTimeoutRef.current) {
        clearTimeout(streamUpdateTimeoutRef.current)
      }
    }
  }, [])

  // Ref pour le polling des messages
  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastMessageTimestampRef = useRef<Date | null>(null)

  useEffect(() => {
    setIsConnected(connectionStatus === 'Open')
    
    // Fonction pour récupérer les messages récents depuis Supabase
    const fetchRecentMessages = async () => {
      if (!sessionId || !token || isLoadingMessages) return
      
      try {
        const response = await axios.get(
          `${apiUrl}/api/v1/conversations/${sessionId}/messages`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            },
            params: {
              limit: 20 // Récupérer les 20 derniers messages
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
        
        // Mettre à jour les messages seulement si on en a de nouveaux
        setMessages((prev) => {
          const existingIds = new Set(prev.map(m => m.id))
          const newMessages = loadedMessages.filter(m => !existingIds.has(m.id))
          
          if (newMessages.length > 0) {
            // Fusionner les messages en gardant l'ordre chronologique
            const allMessages = [...prev, ...newMessages].sort((a, b) => 
              a.timestamp.getTime() - b.timestamp.getTime()
            )
            
            // S'assurer que le loading est désactivé si on a reçu des messages du support humain
            if (newMessages.some(m => m.type === 'bot' && m.agent === 'human_support')) {
              setIsLoading(false)
            }
            
            // Mettre à jour le timestamp du dernier message
            const latestMessage = newMessages[newMessages.length - 1]
            if (latestMessage) {
              lastMessageTimestampRef.current = latestMessage.timestamp
            }
            
            return allMessages
          }
          
          return prev
        })
      } catch (error) {
        console.error('Error fetching recent messages:', error)
      }
    }
    
    // Récupérer les messages lors de la reconnexion WebSocket
    if (connectionStatus === 'Open' && sessionId && token && !isLoadingMessages) {
      // Attendre un peu avant de récupérer pour laisser le temps au WebSocket de se stabiliser
      const timeoutId = setTimeout(fetchRecentMessages, 1500)
      
      // Démarrer un polling périodique si la connexion est fermée ou instable
      // Cela garantit que les messages du support humain sont toujours récupérés
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
      
      // Polling toutes les 5 secondes si la connexion est fermée
      if (connectionStatus !== 'Open') {
        pollingIntervalRef.current = setInterval(fetchRecentMessages, 5000)
      }
      
      return () => {
        clearTimeout(timeoutId)
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
      }
    } else if (connectionStatus !== 'Open' && sessionId && token && !isLoadingMessages) {
      // Si la connexion est fermée, démarrer le polling
      if (!pollingIntervalRef.current) {
        pollingIntervalRef.current = setInterval(fetchRecentMessages, 5000)
      }
    }
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [connectionStatus, sessionId, token, apiUrl, isLoadingMessages])

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
          const finalMessage = data.message || ''
          
          // Pour les messages human_support, utiliser l'ID du message pour la déduplication
          // Pour les autres messages, utiliser le hash du contenu
          let streamEndId: string
          if (data.metadata?.human_support && data.id) {
            streamEndId = `stream_end-${data.id}`
          } else {
            const contentHash = finalMessage.substring(0, 200).trim()
            streamEndId = `stream_end-${contentHash.substring(0, 100)}`
          }
          
          // Vérifier si ce stream_end a déjà été traité
          if (processedMessagesRef.current.has(streamEndId)) {
            console.log('Ignoring duplicate stream_end', streamEndId.substring(0, 50))
            streamBufferRef.current = ''
            streamingMessageRef.current = null
            setIsLoading(false)
            // Annuler le timeout de sécurité s'il existe
            if (loadingTimeoutRef.current) {
              clearTimeout(loadingTimeoutRef.current)
              loadingTimeoutRef.current = null
            }
            return // Ignorer les doublons
          }
          
          processedMessagesRef.current.add(streamEndId)
          
          if (streamUpdateTimeoutRef.current) {
            clearTimeout(streamUpdateTimeoutRef.current)
            streamUpdateTimeoutRef.current = null
          }
          
          // Annuler le timeout de sécurité
          if (loadingTimeoutRef.current) {
            clearTimeout(loadingTimeoutRef.current)
            loadingTimeoutRef.current = null
          }
          
          setMessages((prev) => {
            // PRIORITÉ 1: Toujours remplacer le message en streaming s'il existe
            // Trouver le message en streaming
            const streamingMsg = prev.find((msg) => msg.id === streamingMessageRef.current)
            
            // CAS SPÉCIAL: Si c'est un message human_support et qu'il n'y a pas de message en streaming,
            // créer un nouveau message directement (les messages human_support n'ont pas de stream_start)
            if (!streamingMsg && data.metadata?.human_support) {
              // Ignorer les messages silencieux (forwarded sans confirmation)
              if (data.metadata?.silent && !finalMessage.trim()) {
                setIsLoading(false) // Désactiver le loading
                return prev // Ne pas ajouter de message
              }
              
              const messageId = (data.id || `msg-${Date.now()}`) as string
              const isValidUUID = (id: string): boolean => {
                const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
                return uuidRegex.test(id)
              }
              
              const newMessage: Message = {
                id: messageId,
                type: 'bot',
                content: finalMessage,
                timestamp: new Date(),
                agent: data.agent || 'human_support',
                metadata: data.metadata || {},
              }
              
              // Désactiver le loading pour les messages human_support
              setIsLoading(false)
              
              // Charger le feedback pour ce nouveau message bot si l'ID est un UUID valide (de manière asynchrone)
              if (isValidUUID(messageId) && token) {
                axios.post(
                  `${apiUrl}/api/v1/feedbacks/messages/batch`,
                  { interaction_ids: [messageId] },
                  {
                    headers: {
                      'Authorization': `Bearer ${token}`
                    }
                  }
                ).then(feedbackResponse => {
                  const feedbacksData = feedbackResponse.data.feedbacks || {}
                  if (feedbacksData[messageId]) {
                    const fb = feedbacksData[messageId] as any
                    setFeedbacks(prev => ({
                      ...prev,
                      [messageId]: {
                        reaction: fb.reaction || undefined,
                        comment: fb.comment || undefined
                      }
                    }))
                  }
                }).catch(() => {
                  // Pas de feedback existant, c'est normal
                })
              }
              
              return [...prev, newMessage]
            }
            
            // Si le message en streaming existe, TOUJOURS le remplacer (même si le contenu est similaire)
            // C'est le message "processing" qui doit être remplacé par le message final avec le bon agent
            if (streamingMsg) {
              // Utiliser l'ID du message sauvegardé si disponible (UUID de Supabase)
              const messageId = (data.id || streamingMessageRef.current || streamingMsg.id) as string
              const isValidUUID = (id: string): boolean => {
                const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
                return uuidRegex.test(id)
              }
              
              // Supprimer tous les messages "processing" et les doublons SAUF celui qu'on va remplacer
              // Cela évite les doublons si le streaming a créé plusieurs messages
              const messagesWithoutDuplicates = prev.filter((msg) => {
                // Garder le message en streaming (il sera remplacé)
                if (msg.id === streamingMessageRef.current) {
                  return true
                }
                // CRITIQUE: Supprimer TOUS les messages avec agent="processing" car ils seront remplacés
                // Même si le contenu est différent (ex: message avec faute)
                if (msg.type === 'bot' && msg.agent === 'processing') {
                  console.log('Removing processing message before replacement', msg.id)
                  return false
                }
                // Supprimer les autres messages bot avec le même contenu (doublons exacts)
                if (msg.type === 'bot' && 
                    msg.content.trim() === finalMessage.trim() && 
                    finalMessage.length > 10) {
                  console.log('Removing duplicate message before replacement', msg.id)
                  return false
                }
                return true
              })
              
              const updatedMessages = messagesWithoutDuplicates.map((msg) => {
                if (msg.id === streamingMessageRef.current) {
                  // Remplacer complètement le message streamé par le message final avec le bon ID et agent
                  return {
                    ...msg,
                    id: messageId, // Utiliser l'ID UUID si disponible
                    content: finalMessage,
                    agent: data.agent || 'unknown', // Utiliser le vrai agent (pas "processing")
                    metadata: data.metadata || {},
                  }
                }
                return msg
              })
              
              // Charger le feedback pour ce nouveau message bot si l'ID est un UUID valide (de manière asynchrone)
              if (isValidUUID(messageId) && token) {
                axios.post(
                  `${apiUrl}/api/v1/feedbacks/messages/batch`,
                  { interaction_ids: [messageId] },
                  {
                    headers: {
                      'Authorization': `Bearer ${token}`
                    }
                  }
                ).then(feedbackResponse => {
                  const feedbacksData = feedbackResponse.data.feedbacks || {}
                  if (feedbacksData[messageId]) {
                    const fb = feedbacksData[messageId] as any
                    setFeedbacks(prev => ({
                      ...prev,
                      [messageId]: {
                        reaction: fb.reaction || undefined,
                        comment: fb.comment || undefined
                      }
                    }))
                  }
                }).catch(() => {
                  // Pas de feedback existant, c'est normal
                })
              }
              
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
              
              // Annuler le timeout de sécurité
              if (loadingTimeoutRef.current) {
                clearTimeout(loadingTimeoutRef.current)
                loadingTimeoutRef.current = null
              }
              
              return updatedMessages
            }
            
            // PRIORITÉ 2: Si le message en streaming n'existe pas, vérifier s'il y a déjà un message avec le même contenu
            // Cela peut arriver si stream_end arrive avant stream_start (cas rare)
            const existingMessage = prev.find((msg) => 
              msg.type === 'bot' &&
              msg.content.trim() === finalMessage.trim() &&
              finalMessage.length > 10 // Seulement pour les messages significatifs
            )
            
            if (existingMessage) {
              // Le message existe déjà, mettre à jour son agent si c'est "processing"
              if (existingMessage.agent === 'processing') {
                // Remplacer l'agent "processing" par le vrai agent
                const updatedMessages = prev.map((msg) => {
                  if (msg.id === existingMessage.id) {
                    return {
                      ...msg,
                      agent: data.agent || 'unknown',
                      metadata: data.metadata || msg.metadata || {},
                      id: (data.id || msg.id) as string // Utiliser l'ID UUID si disponible
                    }
                  }
                  return msg
                })
                streamBufferRef.current = ''
                streamingMessageRef.current = null
                setIsLoading(false)
                return updatedMessages
              }
              
              // Le message existe déjà avec le bon agent, ne pas le dupliquer
              streamBufferRef.current = ''
              streamingMessageRef.current = null
              setIsLoading(false)
              return prev
            }
            
            // PRIORITÉ 3: Créer un nouveau message si aucun n'existe
            // Utiliser l'ID du message sauvegardé si disponible (UUID de Supabase)
            const messageId = (data.id || streamingMessageRef.current || `msg-${Date.now()}`) as string
            const isValidUUID = (id: string): boolean => {
              const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
              return uuidRegex.test(id)
            }
            
            const newMessage: Message = {
              id: messageId,
              type: 'bot',
              content: finalMessage,
              timestamp: new Date(),
              agent: data.agent || 'unknown',
              metadata: data.metadata || {},
            }
            
            const updatedMessages = [...prev, newMessage]
            
            // Charger le feedback pour ce nouveau message bot si l'ID est un UUID valide (de manière asynchrone)
            if (isValidUUID(messageId) && token) {
              axios.post(
                `${apiUrl}/api/v1/feedbacks/messages/batch`,
                { interaction_ids: [messageId] },
                {
                  headers: {
                    'Authorization': `Bearer ${token}`
                  }
                }
              ).then(feedbackResponse => {
                const feedbacksData = feedbackResponse.data.feedbacks || {}
                if (feedbacksData[messageId]) {
                  const fb = feedbacksData[messageId] as any
                  setFeedbacks(prev => ({
                    ...prev,
                    [messageId]: {
                      reaction: fb.reaction || undefined,
                      comment: fb.comment || undefined
                    }
                  }))
                }
              }).catch(() => {
                // Pas de feedback existant, c'est normal
              })
            }
            
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
    if (!content.trim() || !isConnected) {
      console.warn('Cannot send message:', { isConnected, hasContent: !!content.trim() })
      return
    }

    // Vérifier que le WebSocket est bien connecté à la bonne session
    if (connectionStatus !== 'Open') {
      console.warn('WebSocket not open, cannot send message', { connectionStatus, sessionId })
      toast.error('Connexion non établie. Veuillez réessayer.')
      return
    }

    console.log('Sending message to session:', sessionId, { content: content.substring(0, 50) + '...' })

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

    // Annuler le timeout précédent s'il existe
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current)
    }

    // Timeout de sécurité : désactiver le loading après 60 secondes si pas de réponse
    loadingTimeoutRef.current = setTimeout(() => {
      console.warn('Loading timeout - disabling loading state after 60s')
      setIsLoading(false)
      streamBufferRef.current = ''
      streamingMessageRef.current = null
      loadingTimeoutRef.current = null
    }, 60000) // 60 secondes

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
          <p className="text-sm text-gray-500">Assistant IA</p>
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
            <span className="font-semibold">VyBuddy est en phase d'apprentissage</span> - Il apprend de chaque interaction pour mieux vous servir. N'hésitez pas à remonter les feedbacks avec les boutons dédiés ! 🙏
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
              <MessageList messages={messages} sessionId={sessionId} feedbacks={feedbacks} setFeedbacks={setFeedbacks} />
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
          VyBuddy répondra dans les meilleurs délais. Temps moyen: 1 minute
        </p>
      </div>
    </div>
  )
}
