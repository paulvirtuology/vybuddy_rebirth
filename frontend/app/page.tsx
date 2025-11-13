'use client'

import { useEffect, useState } from 'react'
import Sidebar from '@/components/Sidebar'
import ChatInterface from '@/components/ChatInterface'

interface ChatHistory {
  id: string
  title: string
  timestamp: Date
}

export default function Home() {
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([])
  const [userId] = useState<string>('user-1') // En production, récupérer depuis l'auth

  // Charger l'historique depuis localStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem('vybuddy_chat_history')
    if (savedHistory) {
      try {
        const history = JSON.parse(savedHistory).map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp),
        }))
        setChatHistory(history)
      } catch (e) {
        console.error('Error loading chat history:', e)
      }
    }
  }, [])

  // Créer un nouveau chat
  const handleNewChat = () => {
    const newChatId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    setCurrentChatId(newChatId)
    
    // Ajouter à l'historique
    const newChat: ChatHistory = {
      id: newChatId,
      title: 'Nouveau chat',
      timestamp: new Date(),
    }
    const updatedHistory = [newChat, ...chatHistory]
    setChatHistory(updatedHistory)
    localStorage.setItem('vybuddy_chat_history', JSON.stringify(updatedHistory))
  }

  // Sélectionner un chat existant
  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId)
  }

  // Mettre à jour le titre du chat dans l'historique
  const handleChatTitleUpdate = (chatId: string, title: string) => {
    setChatHistory((prev) => {
      const updated = prev.map((chat) =>
        chat.id === chatId ? { ...chat, title } : chat
      )
      localStorage.setItem('vybuddy_chat_history', JSON.stringify(updated))
      return updated
    })
  }

  // Créer un chat par défaut au premier chargement
  useEffect(() => {
    if (!currentChatId && chatHistory.length === 0) {
      handleNewChat()
    } else if (!currentChatId && chatHistory.length > 0) {
      setCurrentChatId(chatHistory[0].id)
    }
  }, [])

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
