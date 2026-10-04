# Guide des agents MediNova

Ce document explique le comportement des agents actuellement intégrés à MediNova. Pour démarrer l'application et comprendre les composants techniques, voir le [guide d'architecture](architecture.md). La configuration effective se trouve dans [`config/agents.yaml`](../config/agents.yaml) ; les consignes détaillées de chaque agent sont versionnées dans [`prompts/`](../prompts/).

## Parcours d'une question

```text
Utilisateur → interface/API → concierge → A2A → agent(s) spécialisé(s)
                                        → MCP → outil(s) → source(s) de données
                       ← réponses des spécialistes ←
            ← réponse synthétisée par le concierge ←
```

Le **concierge** décide quels spécialistes consulter. A2A transporte sa question vers le service du spécialiste choisi et lui renvoie une réponse textuelle. Le spécialiste utilise MCP pour découvrir et appeler les outils autorisés qui accèdent à ses sources. Le concierge rassemble ensuite les résultats. Une question peut mobiliser plusieurs spécialistes ; aucun nombre fixe d'agents n'est inscrit dans son prompt.

Les noms `ask_policy`, `ask_research` et `ask_healthcare_provider` sont générés à partir de la liste `delegates` du concierge. Leur description vient du champ `description` de chaque spécialiste : elle aide le modèle à choisir le bon agent, avec les règles de [`prompts/concierge.md`](../prompts/concierge.md). Le champ `tools` de chaque spécialiste indique les outils MCP qu'il peut effectivement utiliser ; `mcp_servers` indique où les découvrir. Un outil absent de la liste `tools` n'est pas présenté à l'agent, même si le serveur MCP l'expose.

| Agent | Rôle | Outil ou délégation | Source principale |
| --- | --- | --- | --- |
| `concierge` | Oriente et synthétise | `ask_*` via A2A ; `tools: []` | Réponses des spécialistes |
| `policy` | Répond sur le contrat d'assurance | `search_policy` via MCP | PDF d'assurance partagé |
| `research` | Recherche des informations médicales générales | `web_search` via MCP | Résultats de recherche web |
| `healthcare_provider` | Cherche des professionnels de santé | `list_doctors` via MCP | Annuaire JSON local |

## Concierge

**Quand intervient-il ?** Il reçoit chaque question du chat. Il est construit dans le processus backend avec le rôle `manager`, le runtime `smolagents` et le modèle `default` configuré dans `config/agents.yaml`. Le backend lui transmet la question et un extrait borné des échanges précédents. Il ne dispose pas d'outil MCP propre (`tools: []`).

**Comment travaille-t-il ?** Il choisit les délégations pertinentes d'après les descriptions des spécialistes et son prompt. Pour chaque domaine, il reformule une question autonome avec les contraintes utiles, puis appelle le spécialiste par A2A. Il peut, par exemple, consulter `policy` pour une franchise et `healthcare_provider` pour des psychiatres à Paris dans le même tour. Il compose une réponse qui distingue les faits du contrat, les informations médicales générales et les résultats de l'annuaire. Le backend enregistre les noms des spécialistes réellement appelés dans `agents_used`.

**Limites.** Il doit s'appuyer sur les réponses des spécialistes plutôt que déduire lui-même une couverture, une disponibilité de rendez-vous ou une appartenance au réseau d'assurance. L'historique est conservé dans le backend ; chaque appel A2A transmet une question autonome, pas toute la conversation. Si aucun spécialiste ne couvre le sujet, le concierge doit indiquer l'information manquante.

**À consulter :** [`prompts/concierge.md`](../prompts/concierge.md), [`agents/runtime.py`](../agents/runtime.py), [`tools/delegation.py`](../tools/delegation.py).

## Policy : contrat d'assurance

**Quand l'appeler ?** Pour les questions sur la couverture, la franchise, les quotes-parts, la coassurance ou les exclusions du contrat chargé dans l'application. Ce spécialiste utilise `langchain` et le profil de modèle `default`.

**Parcours.** Le concierge l'interroge par A2A. Son runtime charge le serveur MCP `policy_documents`, ne conserve que l'outil `search_policy` autorisé dans la configuration, puis l'agent recherche des passages pertinents dans `data/2026AnthemgHIPSBC.pdf`. L'outil renvoie jusqu'à trois pages correspondantes, avec leurs numéros et des extraits. L'agent formule sa réponse à partir de ces passages et cite la page quand elle est disponible.

**Limites.** Ce n'est pas un moteur d'interprétation exhaustif du contrat : la recherche classe les pages par présence des termes de la requête et peut manquer un passage formulé autrement. Le PDF est partagé par l'application ; ce n'est pas un contrat propre à chaque utilisateur. L'agent ne recherche pas de médecins et ne fournit pas de conseil médical. Si la réponse n'est pas trouvée, il doit le dire.

**À consulter :** [`prompts/policy.md`](../prompts/policy.md), [`mcp_servers/policy.py`](../mcp_servers/policy.py).

## Research : information médicale générale

**Quand l'appeler ?** Pour une question générale sur une pathologie, des symptômes, des traitements, des procédures ou des options de soins. Ce spécialiste utilise `langchain` et le profil de modèle `default`.

**Parcours.** Après l'appel A2A, l'agent découvre `web_search` sur le serveur MCP `research_web`. Cet outil lance une recherche DDGS et renvoie au plus dix résultats, avec titre, URL et extrait. Le prompt demande à l'agent de privilégier les sources médicales et de santé publique fiables et de citer les URL lorsqu'elles sont disponibles.

**Limites.** Les extraits de recherche ne constituent pas une vérification clinique des pages, et la qualité des résultats dépend du web et du service de recherche. L'agent fournit des informations générales, pas un diagnostic ni un avis médical personnalisé. Il ne détermine pas la couverture d'assurance et ne consulte pas l'annuaire des médecins.

**À consulter :** [`prompts/research.md`](../prompts/research.md), [`mcp_servers/research.py`](../mcp_servers/research.py).

## Healthcare provider : recherche de professionnels

**Quand l'appeler ?** Pour chercher des médecins selon une ville, une région ou une spécialité. Ce spécialiste utilise `langchain` et le profil de modèle `provider_search` configuré pour Hugging Face.

**Parcours.** Après l'appel A2A, l'agent découvre `list_doctors` sur le serveur MCP `healthcare_providers`. L'outil lit `data/doctors.json` et filtre les entrées par `state`, `city` et `specialty` ; les critères fournis se cumulent et la comparaison ignore la casse. Il renvoie les entrées correspondantes en JSON. Si aucun critère n'est fourni, l'outil renvoie une erreur et le prompt demande une précision à l'utilisateur.

**Limites.** L'annuaire est un jeu de données local et statique. Un résultat ne prouve ni la disponibilité d'un rendez-vous, ni l'appartenance du médecin au réseau de l'assureur, ni son adéquation clinique au besoin de l'utilisateur. L'agent ne doit pas inventer de coordonnées ou de spécialités absentes des résultats.

**À consulter :** [`prompts/healthcare_provider.md`](../prompts/healthcare_provider.md), [`mcp_servers/healthcare.py`](../mcp_servers/healthcare.py).

## Medication : informations sur les médicaments (prévu)

**Statut.** Cet agent est une proposition pour la prochaine extension de MediNova. Il n'est pas encore déclaré dans `config/agents.yaml`, accessible par A2A ou connecté à des outils MCP. Les noms ci-dessous décrivent le contrat envisagé, pas des fonctions déjà disponibles.

**Objectif.** Répondre aux questions sur l'identité d'un médicament, ses informations médicales et ses données de coût en interrogeant des sources distinctes. Comme les autres spécialistes, il serait appelé par le concierge via A2A, puis accéderait à ses outils via MCP.

```text
Concierge ── A2A ──> Medication Agent
                         │
                        MCP
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
 get_medication()  search_medical_info()  get_cost_info()
          │              │              │
  PostgreSQL/API      RAG hybride     PostgreSQL/API
          │              │              │
  identité et forme   RCP et notice   prix et remboursement
```

| Outil MCP envisagé | Données recherchées | Source envisagée |
| --- | --- | --- |
| `get_medication()` | Nom, substance, codes CIS/CIP, dosage, forme et présentations | Base structurée PostgreSQL et/ou API |
| `search_medical_info()` | Indications, contre-indications, effets indésirables, précautions et interactions | RCP et notices indexés par une recherche hybride (texte et vecteurs) |
| `get_cost_info()` | Prix, remboursement et présentations concernées | Base structurée PostgreSQL et/ou API |

**Frontière à respecter.** L'identification d'un médicament, son information clinique et son coût doivent conserver leurs sources et leur contexte. Un prix ou un taux de remboursement ne doit pas être présenté comme la prise en charge effective par le contrat de l'utilisateur : cette question relève de `policy`. L'agent ne doit ni inventer une indication, ni prescrire un traitement personnalisé. Les sources exactes, leur mise à jour et les règles de rapprochement entre codes CIS/CIP, présentations, documents et tarifs restent à définir avant l'implémentation.

## Exemple : une question qui traverse plusieurs agents

Pour « Quelle est ma franchise, quels sont les traitements courants de la dépression et trouve-moi un psychiatre à Paris ? », le parcours attendu est le suivant. Il illustre le routage, sans garantir une réponse ou des résultats particuliers.

1. Le concierge sépare les trois besoins et appelle `ask_policy`, `ask_research` et `ask_healthcare_provider` avec des questions autonomes.
2. A2A transmet chaque question au serveur du spécialiste concerné.
3. Chaque spécialiste utilise son outil MCP : `search_policy` interroge le PDF, `web_search` renvoie des sources web et `list_doctors` filtre l'annuaire par ville et spécialité.
4. Les spécialistes renvoient leurs réponses textuelles au concierge, qui les rassemble en conservant leurs sources et leurs incertitudes. Il ne déduit pas que les médecins trouvés sont couverts par le contrat.

## Ajouter un spécialiste

La structure commune reste la même : **définition → prompt → modèle/runtime → outils MCP → exposition A2A → délégation par le concierge**. Pour un nouveau spécialiste interne :

1. Définir précisément son domaine, ses sources autorisées et ses limites. Créer `prompts/NOM.md` avec ces règles.
2. Créer ou réutiliser un serveur MCP pour ses sources. Déclarer le serveur et ses `allowed_tools` dans `config/agents.yaml`.
3. Ajouter `agents.NOM` dans ce même fichier avec une `description` utile au routage, `role: specialist`, un runtime et un modèle pris en charge, `prompt: NOM`, la liste explicite `tools` (même vide) et `mcp_servers`.
4. Ajouter `a2a_servers.NOM.port`, puis `NOM` à `agents.concierge.delegates`. Le lanceur générique `python -m a2a_servers.serve NOM` suffit ; aucun client ou serveur A2A propre à l'agent n'est nécessaire.
5. Ajouter son service, ses variables d'environnement, son adresse accessible et son contrôle de santé dans `docker-compose.yml`, puis le raccorder au backend. Vérifier le chargement de la définition, la carte A2A, un appel direct et une question au concierge qui exige ce nouveau domaine.

Le [guide d'architecture](architecture.md#add-a-specialist) donne un exemple de configuration et les limites des adaptateurs actuels. Une entrée YAML ne suffit pas à introduire un runtime, un fournisseur de modèle ou un type d'échange non encore pris en charge. Le générateur de titre de conversation utilise aussi un modèle et un prompt, mais **ce n'est pas un agent délégué** : il ne fait pas partie de ce parcours A2A/MCP.
