/**
 * PAGE D'EXEMPLE - Intégration du widget Chat Bubble
 * 
 * Cette page montre comment intégrer le widget dans le portail Vygeek.
 * Vous pouvez copier cette structure dans votre propre portail.
 */

'use client'

import { SessionProvider } from 'next-auth/react'
import ChatBubbleWidget from '@/components/ChatBubbleWidget'

export default function PortailExemplePage() {
  return (
    <SessionProvider>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header du portail */}
        <header className="bg-white dark:bg-gray-800 shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Portail Vygeek
              </h1>
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Support IT
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Contenu principal */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Bienvenue sur le portail Vygeek
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Cette page est un exemple d'intégration du widget de chat VyBuddy.
              Le bouton de chat apparaît en bas à droite de l'écran.
            </p>
            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">
                Comment utiliser le widget :
              </h3>
              <ul className="list-disc list-inside text-sm text-blue-800 dark:text-blue-300 space-y-1">
                <li>Cliquez sur le bouton de chat en bas à droite</li>
                <li>Si vous n'êtes pas connecté, cliquez sur "Continuer avec Google"</li>
                <li>Une fois connecté, vous pouvez commencer à chatter avec VyBuddy</li>
                <li>Utilisez le bouton "+" dans le header pour créer une nouvelle conversation</li>
              </ul>
            </div>
          </div>
        </main>

        {/* Widget de chat - s'affiche sur toutes les pages */}
        <ChatBubbleWidget
          position="bottom-right"
          buttonColor="bg-indigo-tropical"
          buttonSize="large"
        />
      </div>
    </SessionProvider>
  )
}

