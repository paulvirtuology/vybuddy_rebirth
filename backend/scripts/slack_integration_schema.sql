-- ============================================
-- Schema SQL pour l'intégration Slack
-- ============================================
-- Ce fichier contient les modifications nécessaires à la base de données
-- pour supporter l'intégration Slack dans VyBuddy
--
-- Note: Les tables existantes (conversations, interactions) sont déjà utilisées
-- pour stocker les conversations Slack. Ce fichier documente les champs
-- utilisés dans les métadonnées et les extensions possibles.
--
-- ============================================
-- Extension de la table interactions (métadonnées)
-- ============================================
-- La table interactions existe déjà et contient un champ metadata (JSONB)
-- Les conversations Slack utilisent ce champ pour stocker:
--
-- Pour les messages utilisateur:
-- {
--   "platform": "slack",
--   "slack_channel": "C1234567890",
--   "slack_user": "U1234567890",
--   "slack_user_name": "John Doe",
--   "slack_ts": "1234567890.123456",
--   "thread_ts": "1234567890.123456" (optionnel, si dans un thread)
-- }
--
-- Pour les messages bot:
-- {
--   "platform": "slack",
--   "slack_channel": "C1234567890",
--   "ticket_created": true (optionnel),
--   "ticket_id": "123" (optionnel),
--   "human_support": true,            -- message renvoyé depuis le support humain
--   "responder": "Nom du collègue"    -- informations sur l'agent humain
-- }
--
-- ============================================
-- Extension optionnelle: Table slack_channels
-- ============================================
-- Si vous souhaitez tracker les canaux Slack séparément,
-- vous pouvez créer cette table (optionnel):

CREATE TABLE IF NOT EXISTS slack_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slack_channel_id VARCHAR(255) UNIQUE NOT NULL,
    channel_name VARCHAR(255),
    channel_type VARCHAR(50), -- 'public', 'private', 'im', 'mpim'
    team_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_slack_channels_channel_id ON slack_channels(slack_channel_id);
CREATE INDEX IF NOT EXISTS idx_slack_channels_team_id ON slack_channels(team_id);

-- ============================================
-- Extension optionnelle: Table slack_users
-- ============================================
-- Si vous souhaitez tracker les utilisateurs Slack séparément,
-- vous pouvez créer cette table (optionnel):

CREATE TABLE IF NOT EXISTS slack_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slack_user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    real_name VARCHAR(255),
    display_name VARCHAR(255),
    team_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_slack_users_user_id ON slack_users(slack_user_id);
CREATE INDEX IF NOT EXISTS idx_slack_users_email ON slack_users(email);
CREATE INDEX IF NOT EXISTS idx_slack_users_team_id ON slack_users(team_id);

-- ============================================
-- Vue pour les conversations Slack
-- ============================================
-- Vue utile pour analyser les conversations Slack:

CREATE OR REPLACE VIEW slack_conversations_view AS
SELECT 
    c.id,
    c.session_id,
    c.user_id,
    c.title,
    c.created_at,
    c.updated_at,
    COUNT(i.id) as message_count,
    MAX(i.created_at) as last_message_at,
    (i.metadata->>'slack_channel')::text as slack_channel,
    (i.metadata->>'slack_user_name')::text as slack_user_name
FROM conversations c
LEFT JOIN interactions i ON c.session_id = i.session_id
WHERE (i.metadata->>'platform') = 'slack'
   OR c.session_id LIKE 'slack_%'
GROUP BY c.id, c.session_id, c.user_id, c.title, c.created_at, c.updated_at, 
         (i.metadata->>'slack_channel')::text, (i.metadata->>'slack_user_name')::text;

-- ============================================
-- Fonction pour obtenir les statistiques Slack
-- ============================================
-- Fonction utile pour obtenir des statistiques sur l'utilisation Slack:

CREATE OR REPLACE FUNCTION get_slack_stats(
    start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '30 days',
    end_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
RETURNS TABLE (
    total_messages BIGINT,
    total_conversations BIGINT,
    unique_users BIGINT,
    unique_channels BIGINT,
    avg_response_time INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_messages,
        COUNT(DISTINCT session_id)::BIGINT as total_conversations,
        COUNT(DISTINCT user_id)::BIGINT as unique_users,
        COUNT(DISTINCT metadata->>'slack_channel')::BIGINT as unique_channels,
        AVG(
            CASE 
                WHEN message_type = 'bot' THEN 
                    created_at - LAG(created_at) OVER (PARTITION BY session_id ORDER BY created_at)
                ELSE NULL
            END
        )::INTERVAL as avg_response_time
    FROM interactions
    WHERE metadata->>'platform' = 'slack'
      AND created_at BETWEEN start_date AND end_date;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Index pour améliorer les performances
-- ============================================
-- Index sur les métadonnées pour les requêtes Slack:

CREATE INDEX IF NOT EXISTS idx_interactions_metadata_platform 
ON interactions ((metadata->>'platform'));

CREATE INDEX IF NOT EXISTS idx_interactions_metadata_slack_channel 
ON interactions ((metadata->>'slack_channel'));

CREATE INDEX IF NOT EXISTS idx_conversations_session_slack 
ON conversations(session_id) 
WHERE session_id LIKE 'slack_%';

-- ============================================
-- Notes d'implémentation
-- ============================================
-- 1. Les conversations Slack utilisent des session_id au format:
--    - "slack_{channel_id}_{thread_ts}" pour les threads
--    - "slack_{channel_id}_{ts}" pour les messages directs
--    - "slack_cmd_{channel_id}_{user_id}" pour les commandes slash
--
-- 2. Les messages sont stockés dans la table interactions existante avec:
--    - message_type: 'user' ou 'bot'
--    - content: le texte du message
--    - metadata: JSONB contenant les infos Slack
--
-- 3. Les conversations sont stockées dans la table conversations existante
--    avec le session_id correspondant
--
-- 4. Pour activer ces extensions, exécutez ce script dans Supabase SQL Editor
--    ou via votre client PostgreSQL

