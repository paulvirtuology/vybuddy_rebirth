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
  const currentUrlRef = useRef<string>(url)
  const isIntentionallyClosingRef = useRef(false)

  const connect = useCallback(() => {
    if (!session) {
      setConnectionStatus('Closed')
      return
    }
    
    // Fermer l'ancienne connexion si elle existe et si l'URL a changé
    if (ws.current && currentUrlRef.current !== url) {
      console.log('URL changed, closing old WebSocket connection', { 
        oldUrl: currentUrlRef.current, 
        newUrl: url 
      })
      isIntentionallyClosingRef.current = true
      ws.current.close(1000, 'URL changed')
      ws.current = null
    }
    
    // Si l'URL n'a pas changé et qu'on est déjà connecté, ne pas reconnecter
    if (ws.current && ws.current.readyState === WebSocket.OPEN && currentUrlRef.current === url) {
      console.log('WebSocket already connected to this URL')
      return
    }
    
    try {
      // Mettre à jour l'URL courante
      currentUrlRef.current = url
      isIntentionallyClosingRef.current = false
      
      // Ajouter le token dans l'URL pour l'authentification WebSocket
      const token = (session as any).accessToken
      const wsUrlWithAuth = token ? `${url}?token=${encodeURIComponent(token)}` : url
      
      console.log('Connecting WebSocket to:', wsUrlWithAuth.replace(/\?token=.*/, '?token=***'))
      setConnectionStatus('Connecting')
      
      ws.current = new WebSocket(wsUrlWithAuth)

      ws.current.onopen = () => {
        setConnectionStatus('Open')
        console.log('WebSocket connected to:', url.replace(/\/ws\/.*/, '/ws/***'))
      }

      ws.current.onmessage = (event) => {
        setLastMessage(event)
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.current.onclose = (event) => {
        setConnectionStatus('Closed')
        console.log('WebSocket disconnected', { 
          code: event.code, 
          reason: event.reason,
          wasIntentional: isIntentionallyClosingRef.current
        })
        
        // Ne pas reconnecter si la fermeture était intentionnelle (changement d'URL)
        if (isIntentionallyClosingRef.current) {
          console.log('WebSocket closed intentionally (URL changed), not reconnecting')
          isIntentionallyClosingRef.current = false
          return
        }
        
        // Ne pas reconnecter automatiquement si :
        // - Code 1000 (fermeture normale)
        // - Code 1001 (départ du serveur)
        // - Code 1008 (erreur de politique)
        if (event.code === 1000 || event.code === 1001 || event.code === 1008) {
          console.log('WebSocket closed normally, not reconnecting')
          return
        }
        
        // Reconnexion automatique après 3 secondes uniquement pour les erreurs réseau
        reconnectTimeoutRef.current = setTimeout(() => {
          // Vérifier que l'URL n'a pas changé avant de reconnecter
          if (currentUrlRef.current === url) {
            setConnectionStatus('Connecting')
            connect()
          }
        }, 3000)
      }
    } catch (error) {
      console.error('WebSocket connection error:', error)
      setConnectionStatus('Closed')
    }
  }, [url, session])

  useEffect(() => {
    // Si l'URL change, fermer l'ancienne connexion et se reconnecter
    if (currentUrlRef.current !== url) {
      if (ws.current) {
        console.log('URL changed, closing WebSocket and reconnecting', {
          oldUrl: currentUrlRef.current,
          newUrl: url
        })
        isIntentionallyClosingRef.current = true
        ws.current.close(1000, 'URL changed')
        ws.current = null
      }
    }
    
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (ws.current) {
        isIntentionallyClosingRef.current = true
        ws.current.close(1000, 'Component unmounting')
        ws.current = null
      }
    }
  }, [connect, url])

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

