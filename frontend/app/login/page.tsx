"use client"

import { signIn } from "next-auth/react"
import { useEffect, useState, Suspense } from "react"
import { useSession } from "next-auth/react"
import { useRouter, useSearchParams } from "next/navigation"

// Composant séparé pour gérer les erreurs depuis les search params
function ErrorHandler({ onError }: { onError: (error: string | null) => void }) {
  const searchParams = useSearchParams()

  useEffect(() => {
    const errorParam = searchParams.get("error")
    if (errorParam === "AccessDenied" || errorParam === "Configuration") {
      onError("Accès refusé. Votre compte n'est pas autorisé à accéder à cette application. Veuillez contacter le support IT si vous pensez que c'est une erreur.")
    } else if (errorParam) {
      onError("Une erreur est survenue lors de la connexion. Veuillez réessayer.")
    }
  }, [searchParams, onError])

  return null
}

export default function LoginPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/")
    }
  }, [status, router])

  const handleGoogleSignIn = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const result = await signIn("google", {
        callbackUrl: "/",
        redirect: true,
      })
      
      // Si redirect: true, on ne devrait pas arriver ici
      // Mais si redirect: false, on gère l'erreur
      if (result && !result.ok && result.error) {
        if (result.error === "AccessDenied" || result.error === "Configuration") {
          setError("Accès refusé. Votre compte n'est pas autorisé à accéder à cette application. Veuillez contacter le support IT si vous pensez que c'est une erreur.")
        } else {
          setError("Une erreur est survenue lors de la connexion. Veuillez réessayer.")
        }
      }
    } catch (err) {
      setError("Une erreur est survenue lors de la connexion. Veuillez réessayer.")
    } finally {
      setIsLoading(false)
    }
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-sable-lighter">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-tropical"></div>
          <p className="mt-4 text-gray-600">Chargement...</p>
        </div>
      </div>
    )
  }

  if (status === "authenticated") {
    return null
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-sable-lighter px-4">
      <Suspense fallback={null}>
        <ErrorHandler onError={setError} />
      </Suspense>
      <div className="max-w-md w-full bg-blanc rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <div className="inline-block mb-4">
            <img 
              src="/favicon.png" 
              alt="VyBuddy" 
              className="w-16 h-16 mx-auto"
            />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            VyBuddy Support IT
          </h1>
          <p className="text-gray-600">
            Connectez-vous pour accéder à l'assistant de support
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-300 rounded-lg">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800 mb-1">
                  Accès non autorisé
                </p>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <button
            onClick={handleGoogleSignIn}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-700 font-medium hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-600"></div>
                <span>Connexion en cours...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                <span>Continuer avec Google</span>
              </>
            )}
          </button>
        </div>

        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            Accès réservé aux utilisateurs autorisés de l'entreprise
          </p>
        </div>
      </div>
    </div>
  )
}

