import NextAuth, { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import jwt from "jsonwebtoken"

// Configuration Supabase pour vérifier les utilisateurs autorisés
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!

let supabaseClient: any = null

function getSupabaseClient() {
  if (!supabaseClient && supabaseUrl && supabaseServiceKey) {
    const { createClient } = require("@supabase/supabase-js")
    supabaseClient = createClient(supabaseUrl, supabaseServiceKey)
  }
  return supabaseClient
}

const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user, account, profile }) {
      if (account?.provider === "google" && user.email) {
        try {
          const supabase = getSupabaseClient()
          
          // Vérifier si l'utilisateur est autorisé dans la table users
          const { data, error } = await supabase.rpc(
            "is_user_authorized",
            { user_email: user.email }
          )
          
          if (error) {
            console.error("Error checking user authorization:", error)
            return false
          }
          
          // Si l'utilisateur est autorisé, mettre à jour/créer son profil
          if (data === true) {
            const { data: userData, error: userError } = await supabase.rpc(
              "get_user_by_email",
              { user_email: user.email }
            )
            
            if (userError) {
              console.error("Error fetching user:", userError)
            } else if (userData && userData.length > 0) {
              // Mettre à jour les infos Google si nécessaire
              await supabase
                .from("users")
                .update({
                  google_id: account.providerAccountId,
                  picture: user.image,
                  name: user.name,
                  updated_at: new Date().toISOString(),
                })
                .eq("email", user.email)
            }
            
            return true
          }
          
          // Utilisateur non autorisé - retourner une erreur explicite
          throw new Error("UNAUTHORIZED")
        } catch (error) {
          console.error("Sign in error:", error)
          // Si c'est une erreur d'autorisation, la propager
          if (error instanceof Error && error.message === "UNAUTHORIZED") {
            throw error
          }
          return false
        }
      }
      return false
    },
    async jwt({ token, user, account }) {
      // Initial sign in
      if (account && user) {
        token.email = user.email
        token.name = user.name
        token.picture = user.image
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.email = token.email as string
        session.user.name = token.name as string
        session.user.image = token.picture as string
        // Créer un JWT pour le backend avec les mêmes infos
        const backendToken = jwt.sign(
          {
            email: token.email,
            name: token.name,
            picture: token.picture,
          },
          process.env.NEXTAUTH_SECRET!,
          { expiresIn: "30d" }
        )
        ;(session as any).accessToken = backendToken
      }
      return session
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 jours
  },
  secret: process.env.NEXTAUTH_SECRET,
}

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }

