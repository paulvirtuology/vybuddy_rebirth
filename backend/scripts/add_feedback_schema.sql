-- Schema pour le système de feedback
-- À exécuter dans l'éditeur SQL de Supabase

-- Table pour les utilisateurs admin (séparée des utilisateurs normaux)
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id),
    UNIQUE(email)
);

-- Index pour les recherches rapides
CREATE INDEX IF NOT EXISTS idx_admin_users_user_id ON admin_users(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);

-- Table pour les feedbacks généraux
CREATE TABLE IF NOT EXISTS feedbacks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL, -- 'general', 'bug', 'suggestion', etc.
    title TEXT,
    content TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5), -- Note de 1 à 5 (nullable)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les recherches de feedbacks
CREATE INDEX IF NOT EXISTS idx_feedbacks_user_id ON feedbacks(user_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_session_id ON feedbacks(session_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_created_at ON feedbacks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedbacks_feedback_type ON feedbacks(feedback_type);

-- Table pour les réactions sur les messages du bot (like/dislike + commentaires)
CREATE TABLE IF NOT EXISTS message_feedbacks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    interaction_id UUID NOT NULL, -- ID du message dans la table interactions
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    bot_message TEXT NOT NULL, -- Contenu du message du bot (pour référence rapide)
    reaction TEXT CHECK (reaction IN ('like', 'dislike')), -- Like ou dislike (nullable)
    comment TEXT, -- Commentaire optionnel
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(interaction_id, user_id) -- Un utilisateur ne peut réagir qu'une fois par message
);

-- Index pour les recherches de feedbacks sur messages
CREATE INDEX IF NOT EXISTS idx_message_feedbacks_interaction_id ON message_feedbacks(interaction_id);
CREATE INDEX IF NOT EXISTS idx_message_feedbacks_user_id ON message_feedbacks(user_id);
CREATE INDEX IF NOT EXISTS idx_message_feedbacks_session_id ON message_feedbacks(session_id);
CREATE INDEX IF NOT EXISTS idx_message_feedbacks_reaction ON message_feedbacks(reaction);
CREATE INDEX IF NOT EXISTS idx_message_feedbacks_created_at ON message_feedbacks(created_at DESC);

-- Fonction pour vérifier si un utilisateur est admin
CREATE OR REPLACE FUNCTION is_admin_user(user_email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM admin_users au
        INNER JOIN users u ON au.user_id = u.id
        WHERE u.email = user_email
        AND u.is_active = TRUE
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Fonction pour obtenir tous les feedbacks (admin uniquement)
CREATE OR REPLACE FUNCTION get_all_feedbacks(limit_count INTEGER DEFAULT 100)
RETURNS TABLE (
    id UUID,
    user_id TEXT,
    session_id TEXT,
    feedback_type TEXT,
    title TEXT,
    content TEXT,
    rating INTEGER,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        f.id,
        f.user_id,
        f.session_id,
        f.feedback_type,
        f.title,
        f.content,
        f.rating,
        f.created_at
    FROM feedbacks f
    ORDER BY f.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour obtenir tous les feedbacks sur messages (admin uniquement)
CREATE OR REPLACE FUNCTION get_all_message_feedbacks(limit_count INTEGER DEFAULT 100)
RETURNS TABLE (
    id UUID,
    interaction_id UUID,
    user_id TEXT,
    session_id TEXT,
    bot_message TEXT,
    reaction TEXT,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mf.id,
        mf.interaction_id,
        mf.user_id,
        mf.session_id,
        mf.bot_message,
        mf.reaction,
        mf.comment,
        mf.created_at
    FROM message_feedbacks mf
    ORDER BY mf.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour obtenir les statistiques des feedbacks
CREATE OR REPLACE FUNCTION get_feedback_stats()
RETURNS TABLE (
    total_feedbacks BIGINT,
    total_message_feedbacks BIGINT,
    likes_count BIGINT,
    dislikes_count BIGINT,
    avg_rating NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*)::BIGINT FROM feedbacks) as total_feedbacks,
        (SELECT COUNT(*)::BIGINT FROM message_feedbacks) as total_message_feedbacks,
        (SELECT COUNT(*)::BIGINT FROM message_feedbacks WHERE reaction = 'like') as likes_count,
        (SELECT COUNT(*)::BIGINT FROM message_feedbacks WHERE reaction = 'dislike') as dislikes_count,
        (SELECT AVG(rating)::NUMERIC FROM feedbacks WHERE rating IS NOT NULL) as avg_rating;
END;
$$ LANGUAGE plpgsql;

