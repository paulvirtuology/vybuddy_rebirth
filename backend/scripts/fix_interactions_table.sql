-- Script de correction URGENT pour la table interactions
-- À exécuter IMMÉDIATEMENT dans l'éditeur SQL de Supabase

-- Étape 1: Vérifier et supprimer les contraintes NOT NULL sur les anciennes colonnes
DO $$
BEGIN
    -- Rendre user_message et bot_response nullable si elles existent
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'interactions' AND column_name = 'user_message'
    ) THEN
        ALTER TABLE interactions ALTER COLUMN user_message DROP NOT NULL;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'interactions' AND column_name = 'bot_response'
    ) THEN
        ALTER TABLE interactions ALTER COLUMN bot_response DROP NOT NULL;
    END IF;
END $$;

-- Étape 2: Ajouter les nouvelles colonnes si elles n'existent pas
ALTER TABLE interactions 
ADD COLUMN IF NOT EXISTS message_type TEXT,
ADD COLUMN IF NOT EXISTS content TEXT,
ADD COLUMN IF NOT EXISTS agent_used TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Étape 3: Migrer les données existantes si les anciennes colonnes existent
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'interactions' AND column_name = 'user_message'
    ) THEN
        -- Migrer les messages utilisateur
        UPDATE interactions 
        SET 
            message_type = 'user',
            content = user_message,
            agent_used = NULL,
            metadata = '{}'::jsonb
        WHERE user_message IS NOT NULL 
        AND (content IS NULL OR content = '');
        
        -- Migrer les messages bot
        UPDATE interactions 
        SET 
            message_type = 'bot',
            content = bot_response,
            agent_used = COALESCE(agent_used, 'unknown'),
            metadata = '{}'::jsonb
        WHERE bot_response IS NOT NULL 
        AND (content IS NULL OR content = '');
    END IF;
END $$;

-- Étape 4: Rendre les nouvelles colonnes obligatoires
ALTER TABLE interactions 
ALTER COLUMN message_type SET NOT NULL,
ALTER COLUMN content SET NOT NULL;

-- Étape 5: Supprimer les anciennes colonnes (décommentez si vous êtes sûr)
-- ALTER TABLE interactions DROP COLUMN IF EXISTS user_message;
-- ALTER TABLE interactions DROP COLUMN IF EXISTS bot_response;

-- Vérification finale
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'interactions'
ORDER BY ordinal_position;

