'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import axios from 'axios'

export function useAdmin() {
  const { data: session } = useSession()
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = (session as any)?.accessToken

  useEffect(() => {
    if (!session || !token) {
      setIsAdmin(false)
      setIsLoading(false)
      return
    }

    // Tenter d'accéder à un endpoint admin pour vérifier les permissions
    // Si c'est un 403, l'utilisateur n'est pas admin
    const checkAdmin = async () => {
      try {
        const response = await axios.get(
          `${apiUrl}/api/v1/admin/feedbacks/stats`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        )
        // Si la requête réussit, l'utilisateur est admin
        setIsAdmin(true)
      } catch (error: any) {
        // Si c'est un 403, l'utilisateur n'est pas admin
        if (error.response?.status === 403) {
          setIsAdmin(false)
        } else {
          // Autre erreur, on ne peut pas déterminer
          setIsAdmin(false)
        }
      } finally {
        setIsLoading(false)
      }
    }

    checkAdmin()
  }, [session, token])

  return { isAdmin, isLoading }
}

