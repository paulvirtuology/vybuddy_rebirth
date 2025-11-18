-- Schema Supabase pour VyBuddy Rebirth
-- À exécuter dans l'éditeur SQL de Supabase

-- Table des conversations (sessions de chat)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'Nouveau chat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les recherches par utilisateur
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);

-- Table des interactions (messages dans les conversations)
CREATE TABLE IF NOT EXISTS interactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    message_type TEXT NOT NULL, -- 'user' ou 'bot'
    content TEXT NOT NULL,
    agent_used TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les recherches par session
CREATE INDEX IF NOT EXISTS idx_interactions_session_id ON interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created_at ON interactions(created_at ASC);

-- Contrainte de clé étrangère (optionnelle, pour garantir l'intégrité)
-- ALTER TABLE interactions ADD CONSTRAINT fk_interactions_conversation 
--   FOREIGN KEY (session_id) REFERENCES conversations(session_id) ON DELETE CASCADE;

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

-- Table des procédures
CREATE TABLE IF NOT EXISTS procedures (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    diagnostic_questions JSONB DEFAULT '[]'::jsonb,
    resolution_steps JSONB DEFAULT '[]'::jsonb,
    ticket_creation JSONB DEFAULT '{}'::jsonb,
    common_issues JSONB DEFAULT '[]'::jsonb,
    source_tickets_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(category, title)
);

-- Index pour les recherches de procédures
CREATE INDEX IF NOT EXISTS idx_procedures_category ON procedures(category);
CREATE INDEX IF NOT EXISTS idx_procedures_title ON procedures(title);

-- Table de suivi d'utilisation des procédures
CREATE TABLE IF NOT EXISTS procedure_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    procedure_id UUID REFERENCES procedures(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN DEFAULT true,
    feedback TEXT
);

-- Index pour les statistiques d'utilisation
CREATE INDEX IF NOT EXISTS idx_procedure_usage_procedure_id ON procedure_usage(procedure_id);
CREATE INDEX IF NOT EXISTS idx_procedure_usage_used_at ON procedure_usage(used_at DESC);

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
        AVG(LENGTH(i.content))::NUMERIC as avg_response_length
    FROM interactions i
    WHERE i.created_at >= NOW() - (days || ' days')::INTERVAL
    AND i.message_type = 'bot'
    GROUP BY i.agent_used
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Table des données Jamf
CREATE TABLE IF NOT EXISTS jamf_devices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_jss_id INTEGER NOT NULL,
    hostname TEXT NOT NULL,
    serial TEXT NOT NULL,
    username TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_filevault_user BOOLEAN DEFAULT FALSE,
    uid INTEGER,
    home_directory TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(device_jss_id, serial, username)
);

-- Index pour les recherches rapides
CREATE INDEX IF NOT EXISTS idx_jamf_devices_serial ON jamf_devices(serial);
CREATE INDEX IF NOT EXISTS idx_jamf_devices_hostname ON jamf_devices(hostname);
CREATE INDEX IF NOT EXISTS idx_jamf_devices_username ON jamf_devices(username);
CREATE INDEX IF NOT EXISTS idx_jamf_devices_device_jss_id ON jamf_devices(device_jss_id);

-- Fonction pour vérifier si un MacBook est enrollé dans Jamf
CREATE OR REPLACE FUNCTION is_device_jamf_enrolled(serial_number TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM jamf_devices 
        WHERE serial = serial_number 
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Fonction pour obtenir les informations d'un device Jamf
CREATE OR REPLACE FUNCTION get_jamf_device_info(serial_number TEXT)
RETURNS TABLE (
    device_jss_id INTEGER,
    hostname TEXT,
    serial TEXT,
    is_enrolled BOOLEAN,
    users_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        jd.device_jss_id,
        jd.hostname,
        jd.serial,
        TRUE as is_enrolled,
        COUNT(DISTINCT jd.username)::INTEGER as users_count
    FROM jamf_devices jd
    WHERE jd.serial = serial_number
    GROUP BY jd.device_jss_id, jd.hostname, jd.serial;
END;
$$ LANGUAGE plpgsql;

-- Table des utilisateurs autorisés
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    google_id TEXT UNIQUE,
    picture TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les recherches rapides
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Table des sessions (pour tracking et sécurité)
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour les recherches de sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Fonction pour vérifier si un utilisateur est autorisé
CREATE OR REPLACE FUNCTION is_user_authorized(user_email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users 
        WHERE email = user_email 
        AND is_active = TRUE
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Fonction pour obtenir les informations d'un utilisateur
CREATE OR REPLACE FUNCTION get_user_by_email(user_email TEXT)
RETURNS TABLE (
    id UUID,
    email TEXT,
    name TEXT,
    google_id TEXT,
    picture TEXT,
    is_active BOOLEAN,
    role TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id,
        u.email,
        u.name,
        u.google_id,
        u.picture,
        u.is_active,
        u.role
    FROM users u
    WHERE u.email = user_email
    AND u.is_active = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour nettoyer les sessions expirées
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour obtenir les procédures par catégorie
CREATE OR REPLACE FUNCTION get_procedures_by_category(category_filter TEXT)
RETURNS TABLE (
    id UUID,
    category TEXT,
    title TEXT,
    description TEXT,
    diagnostic_questions JSONB,
    resolution_steps JSONB,
    ticket_creation JSONB,
    common_issues JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.category,
        p.title,
        p.description,
        p.diagnostic_questions,
        p.resolution_steps,
        p.ticket_creation,
        p.common_issues
    FROM procedures p
    WHERE p.category = category_filter
    ORDER BY p.source_tickets_count DESC, p.title;
END;
$$ LANGUAGE plpgsql;

