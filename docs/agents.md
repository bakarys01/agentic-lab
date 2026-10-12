# MediNova : présenter les agents en entretien technique

Ce document est un fil conducteur pour expliquer **ce qui fonctionne aujourd'hui**, pourquoi l'architecture a été choisie et quelles en sont les limites. Il ne remplace pas le [guide d'architecture](architecture.md), qui contient les commandes, les contrats de configuration et la procédure détaillée pour ajouter un agent.

## Le projet en une minute

> MediNova est un assistant de santé modulaire. Un concierge reçoit la question de l'utilisateur, identifie les domaines concernés et délègue à des agents spécialisés. Les échanges entre agents passent par A2A ; les spécialistes accèdent à leurs outils et à leurs sources par MCP. Le concierge réunit les réponses en distinguant les faits du contrat d'assurance, les informations médicales générales et les résultats de l'annuaire. L'application propose une interface web, des comptes et des conversations persistantes.

**Pourquoi plusieurs agents ?** Les trois domaines n'ont ni les mêmes sources ni les mêmes règles de réponse. La séparation rend le routage explicite, limite chaque spécialiste aux outils utiles à son domaine et permet d'ajouter une capacité sans réécrire tout le concierge. Elle n'élimine pas les erreurs des modèles : la qualité des sources et la vérification des réponses restent essentielles.

## Suivre une requête de bout en bout

```text
Utilisateur → navigateur → backend/API → concierge
                                    │
                                    └─ A2A → spécialiste(s) → MCP → outil(s) → données
                                    ← réponses des spécialistes ←
Utilisateur ← réponse synthétisée par le concierge ← backend/API
```

1. Le backend authentifie l'utilisateur, retrouve sa conversation et transmet au concierge la nouvelle question avec un historique récent et borné.
2. Le concierge choisit un ou plusieurs spécialistes à partir de leurs descriptions et de son prompt. Il envoie à chacun une **question autonome** ; l'historique complet ne traverse pas A2A.
3. Chaque spécialiste reçoit la demande sur son service A2A, utilise les outils MCP autorisés pour son domaine, puis renvoie une réponse textuelle.
4. Le concierge synthétise ces réponses, conserve les sources et les incertitudes pertinentes ; le backend enregistre la réponse et les noms des spécialistes réellement appelés.

**Exemple à raconter.** Pour « Quelle est ma franchise, quels sont les traitements courants de la dépression et trouve-moi un psychiatre à Paris ? », le concierge peut appeler `policy`, `research` et `healthcare_provider`. Il doit présenter séparément la franchise trouvée dans le PDF, les informations médicales issues du web et les médecins présents dans l'annuaire. Il ne peut pas conclure qu'un médecin trouvé est couvert par l'assurance ou disponible pour un rendez-vous.

## Expliquer chaque agent sans se perdre dans le code

| Agent | Ce qu'il apporte | Outil MCP et source | Limite à connaître |
| --- | --- | --- | --- |
| **Concierge** | Oriente la question et rassemble les réponses. | Délégations `ask_*` via A2A ; aucun outil MCP propre. | Ne doit pas inventer une réponse de spécialiste ou croiser des résultats pour déduire une couverture. |
| **Policy** | Répond sur la couverture, la franchise, la coassurance et les exclusions du contrat chargé. | `search_policy` cherche des passages et numéros de page dans un PDF partagé. | Recherche textuelle non exhaustive ; le PDF n'est pas propre à chaque utilisateur. |
| **Research** | Fournit des informations médicales générales sur des pathologies et traitements. | `web_search` renvoie titres, URL et extraits de résultats web. | Les extraits ne prouvent pas la fiabilité clinique ; ce n'est pas un diagnostic. |
| **Healthcare provider** | Recherche des médecins par lieu et spécialité. | `list_doctors` filtre un annuaire JSON local. | Annuaire statique : aucune garantie de disponibilité, de pertinence clinique ou d'appartenance au réseau d'assurance. |

Le concierge fonctionne actuellement avec **smolagents** et un modèle OpenAI. Les trois spécialistes fonctionnent avec **LangChain** : `policy` et `research` utilisent le profil OpenAI par défaut ; `healthcare_provider` utilise un profil Hugging Face. Ces choix sont déclarés dans [`config/agents.yaml`](../config/agents.yaml). Les instructions de comportement sont dans les fichiers [`prompts/`](../prompts/) ; les adaptateurs qui construisent les agents sont dans [`agents/runtime.py`](../agents/runtime.py). Le champ `role` documente manager ou spécialiste, tandis que les délégations et le runtime déterminent concrètement le comportement.

## Défendre les choix techniques

**Pourquoi A2A ?** Le concierge et les spécialistes sont des services séparés. A2A fournit un échange agent-à-agent : le concierge découvre la carte du spécialiste, lui envoie une question et reçoit sa réponse. Les outils de délégation `ask_policy`, `ask_research` et `ask_healthcare_provider` sont générés à partir de la configuration ; leurs descriptions aident le modèle à choisir. Aujourd'hui, l'échange est textuel et de type requête/réponse, sans streaming ni persistance des tâches distantes.

**Pourquoi MCP ?** Les spécialistes ont besoin de capacités d'accès aux données, pas d'un couplage direct à chaque source dans leur logique. MCP expose `search_policy`, `web_search` et `list_doctors` de manière uniforme. La configuration sélectionne explicitement les outils de chaque agent avec `tools`, puis limite ceux que chaque serveur MCP peut exposer avec `allowed_tools`. Les serveurs MCP actuels utilisent `stdio` : ce sont des sous-processus lancés par le client MCP du spécialiste, pas des services HTTP supplémentaires.

**Pourquoi configuration et prompts séparés ?** Le YAML référence agents, modèles, profils d'exécution, délégations, outils, serveurs MCP et ports A2A ; les prompts définissent le comportement métier. Cela facilite l'ajout d'un spécialiste lorsque son runtime et son fournisseur de modèle sont déjà pris en charge. Le YAML seul ne peut pas créer un nouvel adaptateur ou rendre un agent externe entièrement configurable : ces cas demandent encore du code.

## Expliquer l'infrastructure

**En local**, `docker compose up -d --build` lance le backend et un service A2A pour chacun des trois spécialistes. Le navigateur, l'API et le concierge partagent le processus backend ; les spécialistes communiquent avec lui sur le réseau privé Compose. Le backend expose le port 8000 sur la machine. Chaque spécialiste lance à la demande son serveur MCP en sous-processus `stdio`, puis utilise sa source : PDF local, web ou annuaire JSON.

Le backend conserve comptes, sessions et conversations dans **SQLite** sur un volume Docker nommé, qui survit à `docker compose down`. Les clés des fournisseurs de modèles sont passées par variables d'environnement. Un fichier Compose HTTPS optionnel ajoute un proxy Caddy ; les services A2A ne sont pas destinés à être exposés publiquement. Le contrôle de santé vérifie surtout l'accessibilité des cartes A2A : il ne valide ni les identifiants de modèle, ni les outils MCP, ni la qualité d'une réponse réelle.

**Si on me demande comment ajouter un agent :** je définis d'abord son périmètre et son prompt ; je crée ou réutilise les outils MCP et leurs sources ; je déclare l'agent, son modèle, ses outils et son serveur A2A dans le YAML ; je l'ajoute aux `delegates` du concierge et aux services Compose ; enfin je vérifie un appel direct, puis une question qui doit provoquer sa délégation. Le [guide d'architecture](architecture.md#add-a-specialist) donne les étapes et un exemple de configuration.

## Évolution prévue : Medication Agent

Cet agent **n'est pas encore implémenté**. L'idée est de séparer trois besoins derrière MCP :

| Outil envisagé | Question traitée | Source envisagée |
| --- | --- | --- |
| `get_medication()` | Identifier nom, substance, codes CIS/CIP, dosage, forme et présentations. | PostgreSQL ou API de données structurées. |
| `search_medical_info()` | Retrouver indications, contre-indications, effets indésirables, précautions et interactions dans les RCP et notices. | Recherche hybride sur documents : texte et vecteurs. |
| `get_cost_info()` | Obtenir prix, remboursement et présentations concernées. | PostgreSQL ou API de données structurées. |

Le point technique important sera de **relier correctement** les identifiants du médicament, ses présentations, les documents médicaux et les tarifs, tout en conservant la provenance et la date des données. Un prix ou un taux de remboursement général ne prouvera pas la prise en charge effective du contrat de l'utilisateur : cette dernière relève de `policy`. Les sources exactes et leur rythme de mise à jour restent à choisir.

## Questions probables et réponses courtes

**« Que se passe-t-il si un agent se trompe ou ne répond pas ? »** Le concierge doit conserver l'incertitude ou signaler l'absence de résultat. La séparation des sources aide à localiser l'erreur, mais aucune garantie automatique de justesse médicale n'existe aujourd'hui. Il faut évaluer les réponses, surveiller les services et améliorer les sources.

**« Pourquoi ne pas donner tous les outils à un seul agent ? »** Le routage par domaine réduit les confusions entre contrat, information médicale et annuaire. Chaque spécialiste reçoit uniquement les outils déclarés pour son rôle. Le coût est une orchestration réseau supplémentaire, qu'il faut mesurer et surveiller.

**« Est-ce prêt pour la production ? »** C'est une application de référence fonctionnelle, avec authentification, persistance et services conteneurisés. Les limites à annoncer clairement sont les sources de démonstration, l'absence d'authentification applicative sur les services A2A, l'absence de streaming et de traçage distribué, ainsi que l'absence d'évaluation automatisée de la qualité médicale des réponses. Les services A2A doivent rester sur un réseau privé.
