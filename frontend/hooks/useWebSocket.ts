'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'

interface UseWebSocketReturn {
  sendMessage: (data: any) => void
  lastMessage: MessageEvent | null
  connectionStatus: 'Connecting' | 'Open' | 'Closing' | 'Closed'
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const { data: session } = useSession()
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<
    'Connecting' | 'Open' | 'Closing' | 'Closed'
  >('Connecting')
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  const connect = useCallback(() => {
    if (!session) {
      setConnectionStatus('Closed')
      return
    }
    
    try {
      // Ajouter le token dans l'URL pour l'authentification WebSocket
      const token = (session as any).accessToken
      const wsUrlWithAuth = token ? `${url}?token=${encodeURIComponent(token)}` : url
      
      ws.current = new WebSocket(wsUrlWithAuth)

      ws.current.onopen = () => {
        setConnectionStatus('Open')
        console.log('WebSocket connected')
      }

      ws.current.onmessage = (event) => {
        setLastMessage(event)
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.current.onclose = (event) => {
        setConnectionStatus('Closed')
        console.log('WebSocket disconnected', { code: event.code, reason: event.reason })
        
        // Ne pas reconnecter automatiquement si :
        // - Code 1000 (fermeture normale)
        // - Code 1001 (départ du serveur)
        // - Code 1008 (erreur de politique)
        // - Code 1006 (connexion anormale mais peut-être temporaire)
        // Reconnecter uniquement pour les erreurs réseau (1006) ou autres erreurs
        if (event.code === 1000 || event.code === 1001 || event.code === 1008) {
          console.log('WebSocket closed normally, not reconnecting')
          return
        }
        
        // Reconnexion automatique après 3 secondes uniquement pour les erreurs réseau
        reconnectTimeoutRef.current = setTimeout(() => {
          setConnectionStatus('Connecting')
          connect()
        }, 3000)
      }
    } catch (error) {
      console.error('WebSocket connection error:', error)
      setConnectionStatus('Closed')
    }
  }, [url, session])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (ws.current) {
        ws.current.close()
      }
    }
  }, [connect])

  const sendMessage = useCallback((data: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket is not open. Message not sent.')
    }
  }, [])

  return {
    sendMessage,
    lastMessage,
    connectionStatus,
  }
}

