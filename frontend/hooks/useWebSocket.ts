'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

interface UseWebSocketReturn {
  sendMessage: (data: any) => void
  lastMessage: MessageEvent | null
  connectionStatus: 'Connecting' | 'Open' | 'Closing' | 'Closed'
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<
    'Connecting' | 'Open' | 'Closing' | 'Closed'
  >('Connecting')
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url)

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

      ws.current.onclose = () => {
        setConnectionStatus('Closed')
        console.log('WebSocket disconnected')
        
        // Reconnexion automatique après 3 secondes
        reconnectTimeoutRef.current = setTimeout(() => {
          setConnectionStatus('Connecting')
          connect()
        }, 3000)
      }
    } catch (error) {
      console.error('WebSocket connection error:', error)
      setConnectionStatus('Closed')
    }
  }, [url])

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

