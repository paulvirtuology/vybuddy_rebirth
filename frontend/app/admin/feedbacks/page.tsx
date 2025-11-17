'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

interface Feedback {
  id: string
  user_id: string
  session_id: string
  feedback_type: string
  title?: string
  content: string
  rating?: number
  created_at: string
}

interface MessageFeedback {
  id: string
  interaction_id: string
  user_id: string
  session_id: string
  bot_message: string
  reaction?: 'like' | 'dislike'
  comment?: string
  created_at: string
}

interface FeedbackStats {
  total_feedbacks: number
  total_message_feedbacks: number
  likes_count: number
  dislikes_count: number
  avg_rating?: number
}

export default function AdminFeedbacksPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'general' | 'messages'>('messages')
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([])
  const [messageFeedbacks, setMessageFeedbacks] = useState<MessageFeedback[]>([])
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = (session as any)?.accessToken

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login')
      return
    }

    if (status === 'authenticated' && token) {
      loadData()
    }
  }, [status, token, router])

  const loadData = async () => {
    if (!token) return

    setIsLoading(true)
    setError(null)

    try {
      // Charger les statistiques
      const statsResponse = await axios.get(
        `${apiUrl}/api/v1/admin/feedbacks/stats`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      setStats(statsResponse.data.stats)

      // Charger les feedbacks sur messages
      const messagesResponse = await axios.get(
        `${apiUrl}/api/v1/admin/feedbacks/messages?limit=100`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      setMessageFeedbacks(messagesResponse.data.feedbacks)

      // Charger les feedbacks généraux
      const generalResponse = await axios.get(
        `${apiUrl}/api/v1/admin/feedbacks?limit=100`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      setFeedbacks(generalResponse.data.feedbacks)
    } catch (error: any) {
      if (error.response?.status === 403) {
        setError('Accès refusé. Vous devez être administrateur pour accéder à cette page.')
      } else {
        setError('Erreur lors du chargement des feedbacks. Veuillez réessayer.')
        console.error('Error loading feedbacks:', error)
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (status === 'loading' || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">Chargement...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-red-600 text-lg mb-4">{error}</div>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            Retour à l'accueil
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Administration - Feedbacks</h1>
              <p className="text-sm text-gray-500 mt-1">Gestion et visualisation des feedbacks</p>
            </div>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded"
            >
              Retour au chat
            </button>
          </div>
        </div>
      </header>

      {/* Stats */}
      {stats && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Feedbacks généraux</div>
              <div className="text-2xl font-bold text-gray-900">{stats.total_feedbacks}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Feedbacks messages</div>
              <div className="text-2xl font-bold text-gray-900">{stats.total_message_feedbacks}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Likes</div>
              <div className="text-2xl font-bold text-green-600">{stats.likes_count}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Dislikes</div>
              <div className="text-2xl font-bold text-red-600">{stats.dislikes_count}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500">Note moyenne</div>
              <div className="text-2xl font-bold text-gray-900">
                {stats.avg_rating ? stats.avg_rating.toFixed(1) : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('messages')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'messages'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Feedbacks sur messages ({messageFeedbacks.length})
            </button>
            <button
              onClick={() => setActiveTab('general')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'general'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Feedbacks généraux ({feedbacks.length})
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="py-6">
          {activeTab === 'messages' && (
            <div className="space-y-4">
              {messageFeedbacks.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  Aucun feedback sur les messages pour le moment.
                </div>
              ) : (
                messageFeedbacks.map((feedback) => (
                  <div key={feedback.id} className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-sm font-medium text-gray-900">
                            {feedback.user_id}
                          </span>
                          <span className="text-xs text-gray-500">
                            {format(new Date(feedback.created_at), 'PPpp', { locale: fr })}
                          </span>
                          {feedback.reaction && (
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                feedback.reaction === 'like'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {feedback.reaction === 'like' ? '👍 Like' : '👎 Dislike'}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 mb-2">
                          Session: {feedback.session_id}
                        </div>
                        <div className="text-xs text-gray-500 mb-2">
                          Interaction ID: {feedback.interaction_id}
                        </div>
                      </div>
                    </div>
                    <div className="bg-gray-50 rounded p-4 mb-3">
                      <div className="text-xs text-gray-500 mb-1">Message du bot:</div>
                      <div className="text-sm text-gray-900 whitespace-pre-wrap">
                        {feedback.bot_message.length > 500
                          ? `${feedback.bot_message.substring(0, 500)}...`
                          : feedback.bot_message}
                      </div>
                    </div>
                    {feedback.comment && (
                      <div className="bg-blue-50 rounded p-4">
                        <div className="text-xs text-gray-700 font-medium mb-1">Commentaire:</div>
                        <div className="text-sm text-gray-900 whitespace-pre-wrap">
                          {feedback.comment}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'general' && (
            <div className="space-y-4">
              {feedbacks.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  Aucun feedback général pour le moment.
                </div>
              ) : (
                feedbacks.map((feedback) => (
                  <div key={feedback.id} className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          {feedback.title && (
                            <h3 className="text-lg font-medium text-gray-900">
                              {feedback.title}
                            </h3>
                          )}
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              feedback.feedback_type === 'bug'
                                ? 'bg-red-100 text-red-800'
                                : feedback.feedback_type === 'suggestion'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {feedback.feedback_type}
                          </span>
                          {feedback.rating && (
                            <div className="flex items-center gap-1">
                              <span className="text-sm text-gray-500">Note:</span>
                              <span className="text-sm font-medium text-yellow-600">
                                {'⭐'.repeat(feedback.rating)}
                              </span>
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
                          <span>{feedback.user_id}</span>
                          <span>•</span>
                          <span>{format(new Date(feedback.created_at), 'PPpp', { locale: fr })}</span>
                          <span>•</span>
                          <span>Session: {feedback.session_id}</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-900 whitespace-pre-wrap">
                      {feedback.content}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

