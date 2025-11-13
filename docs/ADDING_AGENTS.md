# Guide : Ajouter un Nouvel Agent

Ce guide explique comment ajouter un nouvel agent spécialisé au système VyBuddy Rebirth.

## Vue d'ensemble du Processus

```
┌─────────────────────────────────────────────────────────────┐
│                    Ajouter un Nouvel Agent                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  1. Créer le fichier de l'agent      │
        │     backend/app/agents/votre_agent.py│
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  2. Ajouter au LangGraph Swarm        │
        │     - Import                           │
        │     - Initialisation                   │
        │     - Nœud dans le graphe              │
        │     - Méthode du nœud                  │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  3. Mettre à jour le Router Agent     │
        │     - Prompt d'analyse                 │
        │     - Format JSON                      │
        │     - Fallback routing                 │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │  4. Tester l'intégration              │
        └───────────────────────────────────────┘
```

Pour ajouter un nouvel agent, vous devez :

1. **Créer le fichier de l'agent** dans `backend/app/agents/`
2. **Ajouter l'agent au LangGraph Swarm** dans `backend/app/services/langgraph_swarm.py`
3. **Mettre à jour le Router Agent** pour reconnaître le nouvel agent
4. **Tester l'intégration**

## Étape 1 : Créer le Fichier de l'Agent

### Template de Base

Créez un nouveau fichier `backend/app/agents/votre_agent.py` :

```python
"""
Votre Agent - Description de la spécialité
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent

logger = structlog.get_logger()


class VotreAgent(BaseAgent):
    """Agent spécialisé dans [domaine]"""
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "openai"  # ou "anthropic" ou "gemini"
    ) -> Dict[str, Any]:
        """
        Traite une demande liée à [domaine]
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        system_prompt = """Vous êtes un expert en support IT spécialisé dans [domaine].

Votre rôle:
1. [Rôle 1]
2. [Rôle 2]
3. [Rôle 3]
4. Si le problème persiste, indiquer qu'un ticket sera créé

Solutions courantes:
- [Solution 1]
- [Solution 2]
- [Solution 3]

Toujours être professionnel et clair. Si le problème persiste, indiquez qu'un ticket sera créé.
"""
        
        prompt = f"""Contexte de la conversation:
{context}

Message actuel de l'utilisateur: {message}

Analysez le problème [domaine] et répondez de manière appropriée. Si vous avez besoin d'informations, posez UNE question. Si vous avez une solution, proposez-la clairement.
"""
        
        try:
            response = await llm.ainvoke(prompt)
            response_text = response.content
            
            needs_ticket = (
                "needs_ticket: true" in response_text.lower() or
                "créer un ticket" in response_text.lower() or
                "ticket sera créé" in response_text.lower()
            )
            
            response_text = response_text.replace("needs_ticket: true", "").strip()
            
            logger.info(
                "VotreAgent response",
                session_id=session_id,
                needs_ticket=needs_ticket
            )
            
            return {
                "message": response_text,
                "needs_ticket": needs_ticket,
                "agent": "votre_agent"
            }
            
        except Exception as e:
            logger.error("VotreAgent error", error=str(e), exc_info=True)
            return {
                "message": "Une erreur est survenue lors du diagnostic [domaine]. Un ticket va être créé.",
                "needs_ticket": True,
                "agent": "votre_agent"
            }
```

### Points Importants

- **Héritez de `BaseAgent`** : Cela vous donne accès aux LLMs et aux méthodes utilitaires
- **Implémentez `process()`** : C'est la méthode principale appelée par le système
- **Retournez un dictionnaire** avec `message`, `needs_ticket`, et `agent`
- **Gérez les erreurs** : Retournez toujours une réponse, même en cas d'erreur

## Étape 2 : Ajouter l'Agent au LangGraph Swarm

Modifiez `backend/app/services/langgraph_swarm.py` :

### 2.1 Importer l'agent

```python
from app.agents.votre_agent import VotreAgent
```

### 2.2 Initialiser l'agent dans `__init__`

```python
def __init__(self):
    # ... agents existants ...
    self.votre_agent = VotreAgent()
    
    # Construction du graphe LangGraph
    self.graph = self._build_graph()
```

### 2.3 Ajouter le nœud dans `_build_graph()`

```python
def _build_graph(self) -> StateGraph:
    workflow = StateGraph(dict)
    
    # Ajout des nœuds existants
    workflow.add_node("network", self._network_node)
    # ... autres nœuds ...
    
    # Ajouter votre nouveau nœud
    workflow.add_node("votre_agent", self._votre_agent_node)
    
    # Mettre à jour le routage conditionnel
    workflow.set_conditional_entry_point(
        route_agent,
        {
            "network": "network",
            # ... autres agents ...
            "votre_agent": "votre_agent",  # Ajouter ici
        }
    )
    
    # Ajouter l'edge vers le ticket
    workflow.add_edge("votre_agent", "ticket")
    
    # ... reste du code ...
```

### 2.4 Créer la méthode du nœud

```python
async def _votre_agent_node(self, state: dict) -> dict:
    """Nœud Votre Agent"""
    try:
        response = await self.votre_agent.process(
            message=state["message"],
            session_id=state["session_id"],
            user_id=state["user_id"],
            history=state.get("history", []),
            llm_provider=state["routing_decision"]["llm"]
        )
        state["response"] = response
        state["agent_used"] = "votre_agent"
        return state
    except Exception as e:
        logger.error("VotreAgent error", error=str(e))
        state["response"] = {
            "message": "Erreur lors du diagnostic [domaine]",
            "needs_ticket": True
        }
        return state
```

## Étape 3 : Mettre à jour le Router Agent

Modifiez `backend/app/services/router_agent.py` :

### 3.1 Mettre à jour le prompt d'analyse

Dans la méthode `analyze_and_route()`, ajoutez votre agent dans les règles de routage :

```python
analysis_prompt = f"""Analysez l'intention de l'utilisateur et déterminez:
1. Le type de problème (wifi, macos, workspace, knowledge, votre_domaine, autre)
2. Le LLM le plus adapté (openai, anthropic, gemini)
3. L'agent spécialisé à utiliser

Règles de routage:
- Problèmes WiFi/Réseau → Network Agent avec Anthropic
- Problèmes MacOS → MacOS Agent avec OpenAI
- Problèmes Google Workspace → Workspace Agent avec Gemini
- Questions procédures/connaissances → Knowledge Agent avec Anthropic
- Problèmes [Votre Domaine] → Votre Agent avec [LLM préféré]  # Ajouter ici
- Autres → Router Agent avec OpenAI

Message utilisateur: {message}
...
"""
```

### 3.2 Mettre à jour le format JSON

```python
Répondez au format JSON:
{{
    "intent": "wifi|macos|workspace|knowledge|votre_domaine|other",
    "llm": "openai|anthropic|gemini",
    "agent": "network|macos|workspace|knowledge|votre_agent|router",
    "confidence": 0.0-1.0
}}
```

### 3.3 Ajouter le fallback routing

Dans `_fallback_routing()`, ajoutez :

```python
elif any(word in message_lower for word in ["mot_clé_1", "mot_clé_2", "mot_clé_3"]):
    return {
        "intent": "votre_domaine",
        "llm": "openai",  # ou anthropic, gemini selon votre préférence
        "agent": "votre_agent",
        "confidence": 0.7
    }
```

## Étape 4 : Exemple Concret - Agent Monday

Voici un exemple complet d'un agent pour Monday.com :

### Fichier : `backend/app/agents/monday_agent.py`

```python
"""
Monday Agent - Support Monday.com
Spécialisé dans les problèmes liés à Monday.com
"""
from typing import Dict, Any, List
import structlog

from app.agents.base_agent import BaseAgent

logger = structlog.get_logger()


class MondayAgent(BaseAgent):
    """Agent spécialisé dans Monday.com"""
    
    async def process(
        self,
        message: str,
        session_id: str,
        user_id: str,
        history: List[Dict[str, str]] = None,
        llm_provider: str = "openai"
    ) -> Dict[str, Any]:
        """
        Traite une demande liée à Monday.com
        """
        llm = self.get_llm(llm_provider)
        context = self.build_context(message, history or [])
        
        system_prompt = """Vous êtes un expert en support IT spécialisé dans Monday.com.

Votre rôle:
1. Aider avec les problèmes d'accès à Monday.com
2. Expliquer comment utiliser les fonctionnalités de Monday
3. Résoudre les problèmes de permissions et de partage
4. Si le problème persiste, indiquer qu'un ticket sera créé

Solutions courantes:
- Problèmes de connexion: vérifier les identifiants, réinitialiser le mot de passe
- Problèmes de permissions: vérifier les droits d'accès au board
- Problèmes de synchronisation: vérifier la connexion, forcer la synchronisation
- Problèmes d'intégration: vérifier les webhooks et les intégrations

Toujours être professionnel et clair. Si le problème persiste, indiquez qu'un ticket sera créé.
"""
        
        prompt = f"""Contexte de la conversation:
{context}

Message actuel de l'utilisateur: {message}

Analysez le problème Monday.com et répondez de manière appropriée. Si vous avez besoin d'informations, posez UNE question. Si vous avez une solution, proposez-la clairement.
"""
        
        try:
            response = await llm.ainvoke(prompt)
            response_text = response.content
            
            needs_ticket = (
                "needs_ticket: true" in response_text.lower() or
                "créer un ticket" in response_text.lower() or
                "ticket sera créé" in response_text.lower()
            )
            
            response_text = response_text.replace("needs_ticket: true", "").strip()
            
            logger.info(
                "Monday agent response",
                session_id=session_id,
                needs_ticket=needs_ticket
            )
            
            return {
                "message": response_text,
                "needs_ticket": needs_ticket,
                "agent": "monday"
            }
            
        except Exception as e:
            logger.error("Monday agent error", error=str(e), exc_info=True)
            return {
                "message": "Une erreur est survenue lors du diagnostic Monday.com. Un ticket va être créé.",
                "needs_ticket": True,
                "agent": "monday"
            }
```

## Checklist de Vérification

Avant de déployer votre nouvel agent, vérifiez :

- [ ] Le fichier de l'agent est créé et hérite de `BaseAgent`
- [ ] L'agent est importé dans `langgraph_swarm.py`
- [ ] L'agent est initialisé dans `__init__` du `LangGraphSwarm`
- [ ] Le nœud est ajouté dans `_build_graph()`
- [ ] La méthode du nœud est créée (ex: `_votre_agent_node`)
- [ ] L'edge vers "ticket" est ajouté
- [ ] Le Router Agent reconnaît le nouvel agent dans le prompt
- [ ] Le fallback routing inclut les mots-clés appropriés
- [ ] Les tests fonctionnent correctement

## Bonnes Pratiques

1. **Nommage cohérent** : Utilisez des noms en minuscules avec underscores pour les agents
2. **Logging** : Toujours logger les actions importantes
3. **Gestion d'erreurs** : Toujours retourner une réponse, même en cas d'erreur
4. **Documentation** : Documentez la spécialité de votre agent
5. **Tests** : Testez avec différents types de messages

## Intégrations Avancées

Si votre agent a besoin d'intégrations externes (APIs, bases de données), vous pouvez :

1. **Ajouter des dépendances** dans `requirements.txt`
2. **Créer un client dédié** dans `app/integrations/`
3. **Utiliser les clients existants** (Supabase, Redis, Pinecone)

Exemple avec une intégration API :

```python
from app.integrations.monday_client import MondayClient

class MondayAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.monday_client = MondayClient()
    
    async def process(self, ...):
        # Utiliser self.monday_client pour appeler l'API
        ...
```

## Support

Pour toute question ou problème lors de l'ajout d'un agent, consultez :
- Les agents existants comme exemples
- La documentation LangGraph
- Les logs du système pour le débogage

