'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import Sidebar from '@/components/Sidebar'
import ChatInterface from '@/components/ChatInterface'

interface ChatHistory {
  id: string
  title: string
  timestamp: Date
}

export default function Home() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  
  const userId = session?.user?.email || 'unknown'
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = (session as any)?.accessToken

  // Ref pour s'assurer que le chargement initial ne se fait qu'une fois
  const conversationsLoadedRef = useRef(false)

  // Rediriger vers login si non authentifié
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login')
    }
  }, [status, router])

  // Créer un nouveau chat
  const handleNewChat = useCallback(async () => {
    if (!token) return
    
    const newChatId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    setCurrentChatId(newChatId)
    
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
    }
    
    // Ajouter à l'historique local
    const newChat: ChatHistory = {
      id: newChatId,
      title: 'Nouveau chat',
      timestamp: new Date(),
    }
    setChatHistory((prev) => [newChat, ...prev])
  }, [apiUrl, token])

  // Charger l'historique depuis Supabase UNE SEULE FOIS au démarrage
  useEffect(() => {
    if (status !== 'authenticated' || !token || conversationsLoadedRef.current) return
    
    const loadConversations = async () => {
      conversationsLoadedRef.current = true
      
      try {
        setIsLoadingHistory(true)
        const response = await axios.get(`${apiUrl}/api/v1/conversations`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        const conversations = response.data.conversations.map((conv: any) => ({
          id: conv.id,
          title: conv.title,
          timestamp: new Date(conv.timestamp)
        }))
        
        setChatHistory(conversations)
      } catch (error) {
        console.error('Error loading conversations:', error)
        // En cas d'erreur, on continue avec un historique vide
        setChatHistory([])
      } finally {
        setIsLoadingHistory(false)
      }
    }
    
    loadConversations()
  }, [status, token, apiUrl])

  // Sélectionner un chat existant
  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId)
  }

  // Mettre à jour le titre du chat dans l'historique
  const handleChatTitleUpdate = async (chatId: string, title: string) => {
    // Mettre à jour dans Supabase
    try {
      const encodedTitle = encodeURIComponent(title)
      await axios.post(
        `${apiUrl}/api/v1/conversations/${chatId}/title?title=${encodedTitle}`,
        null,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
    } catch (error) {
      console.error('Error updating conversation title:', error)
    }
    
    // Mettre à jour l'historique local
    setChatHistory((prev) => {
      return prev.map((chat) =>
        chat.id === chatId ? { ...chat, title } : chat
      )
    })
  }

  // Créer un chat par défaut au premier chargement
  useEffect(() => {
    if (isLoadingHistory || status !== 'authenticated') return
    
    if (!currentChatId && chatHistory.length === 0) {
      handleNewChat()
    } else if (!currentChatId && chatHistory.length > 0) {
      setCurrentChatId(chatHistory[0].id)
    }
  }, [isLoadingHistory, chatHistory, currentChatId, handleNewChat, status])
  
  // Attendre que la session soit chargée
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-tropical"></div>
          <p className="mt-4 text-gray-600">Chargement...</p>
        </div>
      </div>
    )
  }
  
  if (!session) {
    return null
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        currentChatId={currentChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        chatHistory={chatHistory}
      />
      <div className="flex-1 flex flex-col bg-blanc">
        {currentChatId ? (
          <ChatInterface
            sessionId={currentChatId}
            userId={userId}
            onTitleUpdate={(title) => handleChatTitleUpdate(currentChatId, title)}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>Sélectionnez un chat ou créez-en un nouveau</p>
          </div>
        )}
      </div>
    </div>
  )
}
