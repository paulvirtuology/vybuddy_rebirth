'use client'

import { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

interface KnowledgeBaseFile {
  path: string
  name: string
  type: string
  category?: string
  size: number
  modified: string
}

export default function AdminKnowledgeBasePage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [files, setFiles] = useState<KnowledgeBaseFile[]>([])
  const [selectedFile, setSelectedFile] = useState<KnowledgeBaseFile | null>(null)
  const [fileContent, setFileContent] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isReindexing, setIsReindexing] = useState(false)
  const [isCreatingNew, setIsCreatingNew] = useState(false)
  const [newFileName, setNewFileName] = useState('')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = (session as any)?.accessToken

  // Fonction pour encoder le chemin en préservant les / (slash)
  // encodeURIComponent encode / en %2F, ce qui cause des problèmes CORS
  // On encode seulement les caractères spéciaux mais on garde les /
  const encodeFilePath = (filePath: string): string => {
    // Encoder chaque segment du chemin séparément, puis les joindre avec /
    return filePath.split('/').map(segment => encodeURIComponent(segment)).join('/')
  }

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login')
      return
    }

    if (status === 'authenticated' && token) {
      loadFiles()
    }
  }, [status, token, router])

  const loadFiles = async () => {
    if (!token) return

    setIsLoading(true)

    try {
      const response = await axios.get(
        `${apiUrl}/api/v1/admin/knowledge-base/files`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      setFiles(response.data.files)
    } catch (error: any) {
      if (error.response?.status === 403) {
        const message = 'Accès refusé. Vous devez être administrateur pour accéder à cette page.'
        toast.error(message)
      } else {
        const message = 'Erreur lors du chargement des fichiers. Veuillez réessayer.'
        console.error('Error loading files:', error)
        toast.error(message)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const loadFile = async (filePath: string) => {
    if (!token) return

    setIsLoading(true)

    try {
      const response = await axios.get(
        `${apiUrl}/api/v1/admin/knowledge-base/files/${encodeFilePath(filePath)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      setSelectedFile(response.data)
      setFileContent(response.data.content)
      setIsCreatingNew(false)
    } catch (error: any) {
      const message = 'Erreur lors du chargement du fichier. Veuillez réessayer.'
      console.error('Error loading file:', error)
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  const saveFile = async () => {
    if (!token) {
      toast.error('Vous devez être connecté pour sauvegarder un fichier.')
      return
    }
    
    if (!isCreatingNew && !selectedFile) {
      toast.error('Aucun fichier sélectionné.')
      return
    }
    
    if (isCreatingNew && !newFileName.trim()) {
      toast.error('Veuillez entrer un nom de fichier.')
      return
    }

    setIsSaving(true)

    try {
      const filePath = isCreatingNew ? `${newFileName.trim()}.md` : selectedFile!.path
      const encodedPath = encodeFilePath(filePath)
      const url = `${apiUrl}/api/v1/admin/knowledge-base/files/${encodedPath}`
      
      console.log('Saving file:', { filePath, encodedPath, url, isCreatingNew })
      
      const response = await axios.put(
        url,
        { content: fileContent },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )
      
      console.log('File saved successfully:', response.data)
      
      toast.success('Fichier sauvegardé avec succès !')
      setIsCreatingNew(false)
      await loadFiles()
      
      // Utiliser le path retourné par le backend (normalisé) pour recharger le fichier
      const savedFilePath = response.data.path || filePath
      await loadFile(savedFilePath)
      
      if (isCreatingNew) {
        setNewFileName('')
      }
    } catch (error: any) {
      console.error('Error saving file:', error)
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText
      })
      
      let message = 'Erreur lors de la sauvegarde du fichier. Veuillez réessayer.'
      
      if (error.response?.data?.detail) {
        message = error.response.data.detail
      } else if (error.response?.status === 403) {
        message = 'Accès refusé. Vous devez être administrateur pour sauvegarder des fichiers.'
      } else if (error.response?.status === 400) {
        message = error.response.data?.detail || 'Requête invalide. Vérifiez le nom du fichier et le contenu.'
      } else if (error.response?.status === 500) {
        message = error.response.data?.detail || 'Erreur serveur. Vérifiez que le bucket Supabase existe et que les permissions sont correctes.'
      } else if (error.message) {
        message = `Erreur: ${error.message}`
      }
      
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  const deleteFile = async (filePath: string) => {
    if (!token) return
    if (!confirm(`Êtes-vous sûr de vouloir supprimer le fichier "${filePath}" ?`)) return

    try {
      await axios.delete(
        `${apiUrl}/api/v1/admin/knowledge-base/files/${encodeFilePath(filePath)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      
      toast.success('Fichier supprimé avec succès !')
      setSelectedFile(null)
      setFileContent('')
      await loadFiles()
    } catch (error: any) {
      const message = 'Erreur lors de la suppression du fichier. Veuillez réessayer.'
      console.error('Error deleting file:', error)
      toast.error(message)
    }
  }

  const reindex = async () => {
    if (!token) return
    if (!confirm('Êtes-vous sûr de vouloir re-indexer la base de connaissances dans Pinecone ? Cela peut prendre quelques minutes.')) return

    setIsReindexing(true)

    try {
      await axios.post(
        `${apiUrl}/api/v1/admin/knowledge-base/reindex`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      
      toast.success('Base de connaissances re-indexée avec succès dans Pinecone !')
    } catch (error: any) {
      const message = 'Erreur lors de la re-indexation. Veuillez réessayer.'
      console.error('Error reindexing:', error)
      toast.error(message)
    } finally {
      setIsReindexing(false)
    }
  }

  const handleNewFile = () => {
    setSelectedFile(null)
    setFileContent('')
    setIsCreatingNew(true)
    setNewFileName('')
  }

  const handleCancelNew = () => {
    setIsCreatingNew(false)
    setNewFileName('')
    setSelectedFile(null)
    setFileContent('')
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


  // Organiser les fichiers par catégorie
  const mainFiles = files.filter(f => !f.category)
  const procedureFiles = files.filter(f => f.category === 'procedures')

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar avec la liste des fichiers */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Fichiers</h2>
            <button
              onClick={handleNewFile}
              className="px-3 py-1 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Nouveau
            </button>
          </div>
          <button
            onClick={reindex}
            disabled={isReindexing}
            className="w-full px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isReindexing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Re-indexation...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Re-indexer Pinecone
              </>
            )}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {/* Fichiers principaux */}
          {mainFiles.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Base de connaissances
              </h3>
              <div className="space-y-1">
                {mainFiles.map((file) => (
                  <button
                    key={file.path}
                    onClick={() => loadFile(file.path)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                      selectedFile?.path === file.path
                        ? 'bg-indigo-100 text-indigo-900'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{file.name}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteFile(file.path)
                        }}
                        className="ml-2 text-red-600 hover:text-red-800"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Procédures */}
          {procedureFiles.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Procédures
              </h3>
              <div className="space-y-1">
                {procedureFiles.map((file) => (
                  <button
                    key={file.path}
                    onClick={() => loadFile(file.path)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                      selectedFile?.path === file.path
                        ? 'bg-indigo-100 text-indigo-900'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{file.name}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteFile(file.path)
                        }}
                        className="ml-2 text-red-600 hover:text-red-800"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {files.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <p>Aucun fichier trouvé</p>
            </div>
          )}
        </div>
      </div>

      {/* Zone d'édition principale */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Administration - Base de connaissances</h1>
              <p className="text-sm text-gray-500 mt-1">Gestion des fichiers de la base de connaissances</p>
            </div>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded"
            >
              Retour au chat
            </button>
          </div>
        </header>

        {/* Zone d'édition */}
        <div className="flex-1 p-6">
          {isCreatingNew ? (
            <div className="bg-white rounded-lg shadow h-full flex flex-col">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center gap-4">
                  <input
                    type="text"
                    value={newFileName}
                    onChange={(e) => setNewFileName(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ''))}
                    placeholder="Nom du fichier (sans extension)"
                    className="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="text-gray-500">.md</span>
                  <div className="flex-1"></div>
                  <button
                    onClick={handleCancelNew}
                    className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={saveFile}
                    disabled={!newFileName || isSaving}
                    className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSaving ? 'Sauvegarde...' : 'Créer'}
                  </button>
                </div>
              </div>
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                className="flex-1 w-full p-4 border-0 focus:outline-none font-mono text-sm"
                placeholder="Contenu du fichier Markdown..."
              />
            </div>
          ) : selectedFile ? (
            <div className="bg-white rounded-lg shadow h-full flex flex-col">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{selectedFile.name}</h2>
                    <p className="text-sm text-gray-500">
                      Modifié le {format(new Date(selectedFile.modified), 'PPpp', { locale: fr })} • {selectedFile.size} octets
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => deleteFile(selectedFile.path)}
                      className="px-4 py-2 text-red-600 hover:bg-red-50 rounded"
                    >
                      Supprimer
                    </button>
                    <button
                      onClick={saveFile}
                      disabled={isSaving}
                      className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSaving ? 'Sauvegarde...' : 'Enregistrer'}
                    </button>
                  </div>
                </div>
              </div>
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                className="flex-1 w-full p-4 border-0 focus:outline-none font-mono text-sm"
              />
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">Aucun fichier sélectionné</h3>
              <p className="mt-1 text-sm text-gray-500">Sélectionnez un fichier dans la liste pour commencer l'édition</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

