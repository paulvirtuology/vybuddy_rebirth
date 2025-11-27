/**
 * EXEMPLE D'INTÉGRATION DU WIDGET CHAT BUBBLE
 * 
 * Pour intégrer le widget dans votre portail Vygeek:
 * 
 * 1. Importez le composant et le SessionProvider dans votre layout ou page:
 */

'use client'

import { SessionProvider } from 'next-auth/react'
import ChatBubbleWidget from '@/components/ChatBubbleWidget'

export default function PortalPage() {
  return (
    <SessionProvider>
      {/* Votre contenu du portail */}
      <div>
        <h1>Portail Vygeek</h1>
        {/* ... reste du contenu ... */}
      </div>

      {/* Widget de chat - s'affiche automatiquement en bas à droite */}
      <ChatBubbleWidget />
    </SessionProvider>
  )
}

/**
 * OPTIONS DE PERSONNALISATION:
 * 
 * <ChatBubbleWidget
 *   position="bottom-right"  // ou "bottom-left", "top-right", "top-left"
 *   buttonColor="bg-indigo-tropical"  // couleur du bouton
 *   buttonSize="large"  // "small", "medium", ou "large"
 * />
 * 
 * EXEMPLE AVEC OPTIONS:
 * 
 * <ChatBubbleWidget
 *   position="bottom-left"
 *   buttonColor="bg-blue-600"
 *   buttonSize="medium"
 * />
 */

