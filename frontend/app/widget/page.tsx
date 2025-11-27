'use client'

import { SessionProvider } from 'next-auth/react'
import ChatWidgetIframe from '@/components/ChatWidgetIframe'

export default function WidgetPage() {
  return (
    <SessionProvider>
      <ChatWidgetIframe />
    </SessionProvider>
  )
}

