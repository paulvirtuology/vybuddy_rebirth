-- Schema Supabase pour VyBuddy Rebirth
-- À exécuter dans l'éditeur SQL de Supabase

-- Table des interactions
CREATE TABLE IF NOT EXISTS interactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    agent_used TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les recherches par session
CREATE INDEX IF NOT EXISTS idx_interactions_session_id ON interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created_at ON interactions(created_at DESC);

-- Table des tickets créés
CREATE TABLE IF NOT EXISTS tickets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL, -- ID du ticket Odoo
    issue_description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les recherches de tickets
CREATE INDEX IF NOT EXISTS idx_tickets_session_id ON tickets(session_id);
CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_ticket_id ON tickets(ticket_id);

-- Fonction pour obtenir les statistiques
CREATE OR REPLACE FUNCTION get_agent_stats(days INTEGER DEFAULT 7)
RETURNS TABLE (
    agent_used TEXT,
    count BIGINT,
    avg_response_length NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.agent_used,
        COUNT(*)::BIGINT as count,
        AVG(LENGTH(i.bot_response))::NUMERIC as avg_response_length
    FROM interactions i
    WHERE i.created_at >= NOW() - (days || ' days')::INTERVAL
    GROUP BY i.agent_used
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

