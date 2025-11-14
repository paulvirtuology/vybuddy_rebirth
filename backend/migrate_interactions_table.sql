-- Script de migration pour mettre à jour la table interactions
-- À exécuter dans l'éditeur SQL de Supabase

-- Vérifier si la colonne 'content' existe, sinon l'ajouter
DO $$
BEGIN
    -- Vérifier si la colonne 'content' n'existe pas
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'interactions' 
        AND column_name = 'content'
    ) THEN
        -- Si l'ancienne structure existe (user_message, bot_response)
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'interactions' 
            AND column_name = 'user_message'
        ) THEN
            -- Ajouter les nouvelles colonnes (sans NOT NULL pour agent_used)
            ALTER TABLE interactions 
            ADD COLUMN IF NOT EXISTS message_type TEXT,
            ADD COLUMN IF NOT EXISTS content TEXT,
            ADD COLUMN IF NOT EXISTS agent_used TEXT,
            ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
            
            -- S'assurer que agent_used est nullable (au cas où il aurait été créé avec NOT NULL)
            -- Vérifier d'abord si la colonne existe et a une contrainte NOT NULL
            IF EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'interactions' 
                AND column_name = 'agent_used'
                AND is_nullable = 'NO'
            ) THEN
                ALTER TABLE interactions 
                ALTER COLUMN agent_used DROP NOT NULL;
            END IF;
            
            -- Migrer les données existantes
            UPDATE interactions 
            SET 
                message_type = 'user',
                content = user_message,
                agent_used = NULL,
                metadata = '{}'::jsonb
            WHERE user_message IS NOT NULL AND (content IS NULL OR content = '');
            
            UPDATE interactions 
            SET 
                message_type = 'bot',
                content = bot_response,
                agent_used = COALESCE(agent_used, 'unknown'),
                metadata = '{}'::jsonb
            WHERE bot_response IS NOT NULL AND (content IS NULL OR content = '');
            
            -- Rendre les colonnes obligatoires après migration (agent_used reste nullable)
            ALTER TABLE interactions 
            ALTER COLUMN message_type SET NOT NULL,
            ALTER COLUMN content SET NOT NULL;
            
            -- Supprimer les anciennes colonnes (optionnel, décommenter si vous voulez les supprimer)
            -- ALTER TABLE interactions DROP COLUMN IF EXISTS user_message;
            -- ALTER TABLE interactions DROP COLUMN IF EXISTS bot_response;
        ELSE
            -- Si la table n'a pas l'ancienne structure, ajouter simplement les colonnes
            ALTER TABLE interactions 
            ADD COLUMN IF NOT EXISTS message_type TEXT NOT NULL DEFAULT 'user',
            ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS agent_used TEXT,
            ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
        END IF;
    ELSE
        -- Si content existe déjà, vérifier si agent_used a une contrainte NOT NULL et la supprimer
        IF EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = 'interactions' 
            AND column_name = 'agent_used'
            AND is_nullable = 'NO'
        ) THEN
            ALTER TABLE interactions 
            ALTER COLUMN agent_used DROP NOT NULL;
        END IF;
    END IF;
END $$;

-- Vérifier que tout est en place
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'interactions'
ORDER BY ordinal_position;
