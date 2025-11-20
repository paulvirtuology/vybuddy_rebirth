'use client'

import { memo, useState, useEffect } from 'react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { useSession } from 'next-auth/react'
import axios from 'axios'
import toast from 'react-hot-toast'

// Fonction pour formater le markdown simple (**texte** en gras)
const formatMarkdown = (text: string): (string | JSX.Element)[] => {
  const parts: (string | JSX.Element)[] = []
  const regex = /\*\*(.+?)\*\*/g
  let lastIndex = 0
  let match
  let key = 0

  while ((match = regex.exec(text)) !== null) {
    // Ajouter le texte avant le match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index))
    }
    // Ajouter le texte en gras
    parts.push(
      <strong key={key++}>{match[1]}</strong>
    )
    lastIndex = regex.lastIndex
  }

  // Ajouter le reste du texte
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex))
  }

  return parts.length > 0 ? parts : [text]
}

interface Message {
  id: string
  type: 'user' | 'bot' | 'system'
  content: string
  timestamp: Date
  agent?: string
  metadata?: any
}

interface MessageFeedback {
  reaction?: 'like' | 'dislike'
  comment?: string
}

interface MessageListProps {
  messages: Message[]
  sessionId: string
  feedbacks: Record<string, MessageFeedback>
  setFeedbacks: React.Dispatch<React.SetStateAction<Record<string, MessageFeedback>>>
}

// Composant de message individuel mémorisé pour éviter les re-renders inutiles
const MessageItem = memo(({ 
  message, 
  sessionId,
  feedback,
  setFeedback
}: { 
  message: Message
  sessionId: string
  feedback: MessageFeedback | null
  setFeedback: (feedback: MessageFeedback | null) => void
}) => {
  const { data: session } = useSession()
  const [showCommentInput, setShowCommentInput] = useState(false)
  const [commentText, setCommentText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = (session as any)?.accessToken
  
  // Fonction pour vérifier si un ID est un UUID valide
  const isValidUUID = (id: string): boolean => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    return uuidRegex.test(id)
  }
  
  // Initialiser le commentText depuis le feedback
  useEffect(() => {
    if (feedback?.comment) {
      setCommentText(feedback.comment)
    } else {
      setCommentText('')
    }
  }, [feedback?.comment])
  
  const submitFeedback = async (reaction?: 'like' | 'dislike') => {
    if (!message.id || !token || isSubmitting) return
    
    // Vérifier que l'ID est un UUID valide avant d'envoyer le feedback
    if (!isValidUUID(message.id)) {
      console.warn('Cannot submit feedback: message ID is not a valid UUID', message.id)
      return
    }
    
    setIsSubmitting(true)
    
    try {
      const finalReaction = reaction !== undefined ? reaction : feedback?.reaction
      const finalComment = showCommentInput ? commentText : feedback?.comment
      
      await axios.post(
        `${apiUrl}/api/v1/feedbacks/messages`,
        {
          interaction_id: message.id,
          session_id: sessionId,
          bot_message: message.content,
          reaction: finalReaction || null,
          comment: finalComment || null
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      
      const newFeedback: MessageFeedback = {
        reaction: finalReaction || undefined,
        comment: finalComment || undefined
      }
      
      setFeedback(newFeedback)
      
      if (reaction !== undefined) {
        setShowCommentInput(false)
      }
      toast.success('Merci pour votre retour !')
    } catch (error) {
      console.error('Error submitting feedback:', error)
      toast.error('Impossible d’enregistrer votre feedback.')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const handleLike = () => {
    const newReaction = feedback?.reaction === 'like' ? undefined : 'like'
    submitFeedback(newReaction)
  }
  
  const handleDislike = () => {
    const newReaction = feedback?.reaction === 'dislike' ? undefined : 'dislike'
    submitFeedback(newReaction)
  }
  
  const handleCommentSubmit = () => {
    submitFeedback()
    setShowCommentInput(false)
  }
  const isHumanSupport = message.metadata?.human_support || message.agent === 'human_support'
  const isUser = message.type === 'user'
  const isSystem = message.type === 'system'
  const isBot = message.type === 'bot' && !isHumanSupport
  
  // Couleurs distinctes pour chaque type de message
  const bubbleClass = [
    'max-w-[75%]',
    'px-4',
    'py-3',
    'rounded-2xl',
    isUser
      ? 'bg-indigo-500 text-white shadow rounded-br-sm' // Utilisateur : indigo adouci
      : isHumanSupport
      ? 'bg-emerald-50 text-emerald-900 border border-emerald-200 rounded-bl-sm' // Support humain : vert pastel
      : isSystem
      ? 'bg-amber-50 text-amber-900 border border-amber-200 shadow-sm' // Système : ambre clair
      : 'bg-blue-50 text-blue-900 border border-blue-100 rounded-bl-sm' // Bot : bleu très léger
  ].join(' ')

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={bubbleClass}>
        <div className="flex items-center justify-between text-xs mb-2">
          {isUser && (
            <span className="font-semibold text-white/90">Vous</span>
          )}
          {isHumanSupport && (
            <span className="inline-flex items-center gap-1.5 text-emerald-700 font-semibold">
              <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full" />
              Support humain
            </span>
          )}
          {isBot && (
            <span className="inline-flex items-center gap-1.5 text-blue-700 font-semibold">
              <span className="w-2.5 h-2.5 bg-blue-500 rounded-full" />
              VyBuddy {message.agent && `(${message.agent})`}
            </span>
          )}
          {isSystem && (
            <span className="inline-flex items-center gap-1.5 text-amber-800 font-semibold">
              <span className="w-2.5 h-2.5 bg-amber-500 rounded-full" />
              Système
            </span>
          )}
        </div>
        <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {formatMarkdown(message.content)}
        </div>
        <div
          className={`text-xs mt-2 flex items-center gap-2 ${
            isUser 
              ? 'text-white/80' 
              : isHumanSupport 
              ? 'text-white/80' 
              : isSystem
              ? 'text-amber-700'
              : 'text-blue-600'
          }`}
        >
          <span>{format(message.timestamp, 'HH:mm', { locale: fr })}</span>
        </div>
        {message.metadata?.ticket_created && (
          <div className="mt-3 bg-green-50 border border-green-200 text-green-800 px-3 py-2 rounded text-xs">
            <div className="flex items-center gap-2 mb-1">
              <svg
                className="w-4 h-4 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="font-semibold">Ticket créé</span>
            </div>
            <div className="text-green-700">
              Un ticket a été créé dans Odoo (ID: {message.metadata.ticket_id}). Notre équipe va vous contacter prochainement.
            </div>
          </div>
        )}
        
        {/* Système de feedback pour les messages du bot */}
        {/* Afficher les boutons seulement si l'ID est un UUID valide (message sauvegardé dans Supabase) */}
        {message.type === 'bot' && isValidUUID(message.id) && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="flex items-center gap-3">
              <button
                onClick={handleLike}
                disabled={isSubmitting}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                  feedback?.reaction === 'like'
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
                title="Like"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                  />
                </svg>
                Like
              </button>
              
              <button
                onClick={handleDislike}
                disabled={isSubmitting}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                  feedback?.reaction === 'dislike'
                    ? 'bg-red-100 text-red-700 hover:bg-red-200'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
                title="Dislike"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"
                  />
                </svg>
                Dislike
              </button>
              
              <button
                onClick={() => setShowCommentInput(!showCommentInput)}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
                  feedback?.comment
                    ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title="Ajouter un commentaire"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
                Commenter
              </button>
            </div>
            
            {/* Champ de commentaire */}
            {showCommentInput && (
              <div className="mt-2">
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Ajoutez un commentaire..."
                  className="w-full px-3 py-2 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  rows={2}
                />
                <div className="flex justify-end gap-2 mt-2">
                  <button
                    onClick={() => {
                      setShowCommentInput(false)
                      setCommentText(feedback?.comment || '')
                    }}
                    className="px-3 py-1 text-xs text-gray-600 hover:text-gray-800"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleCommentSubmit}
                    disabled={isSubmitting}
                    className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {isSubmitting ? 'Envoi...' : 'Envoyer'}
                  </button>
                </div>
              </div>
            )}
            
            {/* Afficher le commentaire existant */}
            {feedback?.comment && !showCommentInput && (
              <div className="mt-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800">
                <div className="font-semibold mb-1">Votre commentaire:</div>
                <div>{feedback.comment}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
})

MessageItem.displayName = 'MessageItem'

function MessageList({ messages, sessionId, feedbacks, setFeedbacks }: MessageListProps) {
  // Fonction pour mettre à jour le feedback d'un message spécifique
  const updateFeedback = (messageId: string, feedback: MessageFeedback | null) => {
    setFeedbacks(prev => {
      if (feedback === null || (!feedback.reaction && !feedback.comment)) {
        // Supprimer le feedback s'il est vide
        const { [messageId]: _, ...rest } = prev
        return rest
      } else {
        // Mettre à jour le feedback
        return {
          ...prev,
          [messageId]: feedback
        }
      }
    })
  }
  
  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <p className="text-lg mb-2">👋 Bonjour !</p>
          <p>Comment puis-je vous aider aujourd'hui ?</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageItem 
          key={message.id} 
          message={message} 
          sessionId={sessionId}
          feedback={feedbacks[message.id] || null}
          setFeedback={(feedback) => updateFeedback(message.id, feedback)}
        />
      ))}
    </div>
  )
}

export default memo(MessageList)
