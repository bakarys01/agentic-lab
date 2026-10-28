# Roadmap — framework d'IA générative déployable chez des clients

## Ambition et périmètre

Construire un socle logiciel réutilisable pour livrer et exploiter des applications d'IA générative chez différents clients. MediNova est le premier déploiement de référence, pas un modèle métier imposé aux suivants. Le périmètre couvre les données et les outils, les prompts et les modèles, l'exécution, les agents si le cas d'usage le justifie, l'évaluation, le déploiement, l'observabilité, la sécurité, les coûts et l'amélioration continue. L'entraînement de modèles prédictifs classiques n'est pas un objectif de cette roadmap.

La [roadmap du laboratoire](roadmap.md) organise les expérimentations et comparaisons de technologies sur MediNova. Ce document décrit le **produit transversal** à en extraire et les conditions nécessaires pour le déployer chez un client. La [documentation d'architecture](architecture.md) décrit le code actuel ; une capacité visée ici ne doit pas être présentée comme déjà implémentée.

Le succès n'est pas « changer trois valeurs et lancer un chatbot ». Un nouveau client doit pouvoir être intégré au moyen de contrats explicites, d'adaptateurs et de configuration versionnés, puis obtenir une application évaluée, exploitable et isolée. Certaines sources ou règles métier demanderont toujours un travail d'intégration spécifique ; ce travail doit rester à la périphérie du socle.

## Contrat d'intégration d'un client

Le client fournit ou valide les éléments suivants avant le développement de son application :

| Entrée | Questions à résoudre et livrable attendu |
| --- | --- |
| Cas d'usage et utilisateurs | Tâches autorisées, utilisateurs visés, canaux, limites de l'assistant et cas nécessitant un humain. |
| Données | Sources, propriétaires, fraîcheur, qualité, classification, droits de lecture, politique de conservation et exemples exploitables. Une source accessible n'est pas forcément autorisée pour chaque utilisateur. |
| Outils et actions | API et systèmes à connecter, identité technique, permissions minimales, actions en lecture ou en écriture, validation humaine requise. |
| Règles métier | Terminologie, décisions permises, sources faisant autorité, règles de priorité, exceptions et réponses attendues en cas d'incertitude. |
| Définition d'une bonne réponse | Cas représentatifs, critères vérifiables, erreurs inacceptables, seuils de qualité, exigences de citation ou de justification, relecture par des experts métier. |
| Contraintes d'exploitation | Hébergement, résidence des données, identité, audit, disponibilité, latence, volumes, budget, rétention et procédure d'incident. |

Le résultat de l'intégration est un **profil client versionné** : configuration des capacités, références vers les sources et les secrets, politiques d'accès, jeu d'évaluation, seuils d'acceptation et paramètres de déploiement. Les secrets et les données sensibles restent dans les systèmes appropriés, hors du profil commité. La configuration seule ne peut pas inventer un connecteur ou une politique qui n'existe pas ; les extensions utilisent des interfaces testées.

## Frontière du socle commun

| Module commun | Responsabilité stable | Partie propre au client |
| --- | --- | --- |
| Ingestion et accès aux données | Contrats des connecteurs, validation, provenance, version des corpus, indexation ou requêtes contrôlées. | Sources, schémas, droits, fréquence de mise à jour, choix des passages faisant autorité. |
| Outils | Schéma d'entrée/sortie, identité, autorisation indépendante du modèle, délais, reprise et journal d'audit. MCP est une option de transport. | API, permissions et actions réellement exposées. |
| Exécution | API, identité de la requête, état, orchestration, budgets, erreurs et reprise. A2A est une option pour des agents distribués, pas une obligation pour tous les cas. | Workflow, agents spécialisés et étapes d'approbation. |
| Modèles et prompts | Contrats des adaptateurs, configuration explicite, versions, limites et stratégie de repli testée. | Fournisseurs autorisés, prompts métier et contraintes sur les données transmises. |
| Évaluation | Format des jeux de cas, exécuteur, mesure de qualité, latence, coût et régressions, conservation des résultats. | Cas réels autorisés, rubriques métier, seuils de mise en production et validation humaine. |
| Observabilité et exploitation | Traces, métriques, alertes, journaux, déploiement, sauvegarde, retour arrière et suivi des dépenses. | Politique de télémétrie, destination, durée de conservation, objectifs de service et budget. |

Les contrats sont plus importants que le choix d'une bibliothèque. Un adaptateur de modèle, de stockage, d'outil ou de télémétrie peut évoluer sans changer les cas d'évaluation ni les règles métier. On n'ajoute une nouvelle abstraction qu'après avoir rencontré un deuxième besoin concret ou un changement réellement difficile.

### Place de LangGraph dans la cible

**Décision envisagée :** utiliser LangGraph pour l'orchestration du concierge de MediNova, à la place de sa boucle actuelle fondée sur smolagents. Le workflow décrirait explicitement l'analyse de la demande, le choix des spécialistes, leurs appels, la synthèse et les chemins d'erreur. Son état et ses éventuelles interruptions pourront servir aux parcours qui exigent une reprise ou une validation humaine. Ce changement concerne la couche d'exécution : A2A reste la communication avec les spécialistes et MCP leur accès aux outils. Les agents spécialisés LangChain et les données ne sont pas remplacés automatiquement.

LangGraph est le candidat retenu pour ce premier workflow du socle, **pas une dépendance imposée à chaque cas client**. Un parcours simple et fixe peut utiliser une exécution plus légère. Une frontière d'exécution minimale doit permettre de comparer les deux orchestrateurs sur les mêmes entrées, sorties et critères, sans lier les futurs profils clients à l'API d'un framework. La migration ne sera effectuée qu'après la baseline MediNova ; qualité, routage, latence, coût, reprise et erreurs devront être comparés avant de retirer smolagents du déploiement de référence. Les contrats client plus larges seront définis après cette comparaison.

## Chaîne d'outils de bout en bout et alternatives

Cette matrice, vérifiée sur les documentations des éditeurs le 26 octobre 2026, indique un **point de départ**, pas une liste de logiciels à installer simultanément. « Actuel » signifie présent dans MediNova ; « cible » ou « candidat » signifie encore à concevoir, intégrer et vérifier. Les alternatives seront comparées sur les mêmes cas et contraintes client. Leurs fonctionnalités, coûts, licences et modalités d'hébergement seront revérifiés au moment de l'adoption.

| Couche | Point de départ et état | Alternatives à étudier | Critère de choix |
| --- | --- | --- | --- |
| Profil client, contrats et configuration | Pydantic, YAML et Git **actuels**, à étendre avec un schéma de profil client. | JSON Schema pour échanger des contrats hors Python ; configuration stockée en base si des changements en cours d'exécution deviennent nécessaires. | Validation au démarrage, versionnement, revue des changements, absence de secrets dans Git. |
| Ingestion documentaire | Scripts et PyMuPDF **actuels** pour les sources MediNova ; pipeline d'ingestion versionné **cible**. | [Unstructured](https://docs.unstructured.io/) pour des formats documentaires variés ; [LlamaIndex ingestion](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/) si ses connecteurs couvrent les sources retenues. | Qualité d'extraction, provenance, mises à jour, droits documentaires et coût d'exploitation. |
| Stockage et recherche | PostgreSQL et psycopg **actuels** pour les médicaments ; recherche textuelle et [pgvector](https://github.com/pgvector/pgvector) **candidats** pour un RAG mesuré. | [Qdrant](https://qdrant.tech/documentation/) ou [Weaviate](https://docs.weaviate.io/weaviate/search/hybrid) si l'échelle, les filtres ou la recherche hybride justifient un service dédié ; OpenSearch si le besoin principal est la recherche et l'analyse textuelle. | Rappel/pertinence sur corpus évalué, filtrage des droits, simplicité, latence et coût. Ne pas ajouter de vecteurs si la recherche structurée ou lexicale suffit. |
| Outils métier et communication | MCP pour les outils et A2A pour les spécialistes **actuels**. | Appels internes typés pour un workflow local simple ; API HTTP/gRPC pour les intégrations dont le contrat ne bénéficie pas de MCP ou d'A2A. | Interopérabilité réelle, contrôle des permissions, coûts réseau et diagnostic ; aucun protocole n'est imposé à tout client. |
| Orchestration | smolagents pour le concierge et LangChain pour les spécialistes **actuels** ; LangGraph **cible** pour le concierge. | [Haystack pipelines/agents](https://docs.haystack.deepset.ai/docs/3.3/choosing-between-pipelines-and-agents) pour un parcours de recherche plus prévisible ; [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/handoffs/) ou [CrewAI Flows](https://docs.crewai.com/core-concepts/Agents) à comparer pour des besoins adaptés. | Qualité, contrôle du flux, reprise, approbation humaine, portabilité, latence et coût sur la même évaluation. |
| Modèles, prompts et accès fournisseur | Adaptateurs OpenAI/Hugging Face et prompts versionnés **actuels**. | Autres fournisseurs via adaptateurs ; [vLLM](https://docs.vllm.ai/) pour servir un modèle ouvert ; [LiteLLM](https://docs.litellm.ai/docs/proxy/users) comme passerelle si routage, quotas ou budgets multi-modèles sont nécessaires. | Qualité métier, règles de transfert des données, disponibilité, coût total, compatibilité avec les outils et complexité. Une passerelle n'est pas requise pour deux fournisseurs déjà maîtrisés. |
| API et interface | FastAPI, Pydantic et frontend JavaScript **actuels**. | Une autre interface ou un SDK client derrière une API stable ; React/Next.js seulement si l'évolution de l'interface le justifie. | Accessibilité, intégration au système client, maintenance, authentification et expérience utilisateur. |
| Évaluation et expérimentation | Jeux de cas et runner locaux **en cours** ; Langfuse **actuel pour la télémétrie**, pas encore source de vérité des scores. | [MLflow GenAI](https://mlflow.org/docs/latest/genai/datasets), [W&B Weave](https://docs.wandb.ai/weave) ou LangSmith pour comparer expériences, revues et déploiement. | Garder données, rubriques et résultats exportables ; comparer revues humaines, confidentialité, reproductibilité et coût. |
| Télémétrie et exploitation | Traces Langfuse limitées aux métadonnées **actuelles** ; instrumentation [OpenTelemetry](https://opentelemetry.io/docs/concepts/observability-primer/) plus complète **cible**. | MLflow, LangSmith ou Phoenix pour l'analyse IA ; Prometheus/Grafana ou solutions cloud pour métriques et alertes d'infrastructure. | Chronologie utile, alertes, rétention, séparation client, contrôle du contenu exporté et effort opérationnel. |
| Livraison et hébergement | Images Docker, Compose et GitHub Actions **actuels** ; [Terraform](https://developer.hashicorp.com/terraform/intro) **cible** pour l'infrastructure versionnée. | ECS/Fargate, [Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run) ou Azure Container Apps selon le client ; Kubernetes seulement si ses besoins justifient son exploitation. | Isolation, réseau privé, état durable, disponibilité, reprise, compétences de l'équipe et coût. Compose reste la référence locale, pas la cible de production universelle. |
| Identité, secrets et politiques | Authentification locale MediNova et variables d'environnement **actuelles**, insuffisantes comme solution client générale. | Fournisseur d'identité compatible OIDC du client ou Keycloak ; gestionnaire de secrets du cloud ou [Vault](https://developer.hashicorp.com/vault/docs). | Intégration IAM, privilèges minimaux, rotation, audit, résidence et rétention des données. |

Les budgets d'exécution, la limitation des appels, l'autorisation des outils, la protection des données, les évaluations et les alertes traversent toutes les couches. Un outil peut fournir une partie de ces fonctions, mais leur présence dans sa documentation ne prouve pas qu'elles sont correctement configurées dans notre déploiement. Les expérimentations ajoutent un candidat à la fois et mesurent son effet avant de modifier le choix de départ.

## Choix de déploiement initial

Le premier objectif est une **instance dédiée par client** : configuration, stockage, clés, comptes de service, journaux et budgets séparés. Le code et les contrats sont communs ; l'environnement d'exécution et les données ne le sont pas. Cette frontière doit être démontrée par des tests et un examen des accès, pas déduite du nom d'un conteneur ou d'un identifiant client.

Une plateforme multi-clients mutualisée serait une étape ultérieure, seulement si son intérêt opérationnel compense la complexité supplémentaire : isolation logique de bout en bout, contrôle des ressources partagées, autorisations, quotas, migrations et facturation par client. Le mode dédié reste possible pour un client dont les contraintes l'exigent.

## Plan de réalisation et preuves de sortie

Les phases ci-dessous sont **à réaliser** pour le framework. MediNova fournit certains composants de départ (agents configurés, MCP, A2A, Compose, tests et traces), mais ne satisfait pas à lui seul les critères de sortie. Les protections élémentaires des données et des accès s'appliquent dès le début ; la phase 5 établit les garanties supplémentaires exigées pour un pilote client. Les phases 1 et 2 prouvent le fonctionnement et la migration de MediNova, la phase 4 éprouve la réutilisation, et la phase 5 prouve l'exploitabilité chez un client.

### 1. Établir la baseline MediNova

Commencer par rendre l'évaluation réutilisable sans refondre tout le framework : définir un contrat minimal pour interroger l'application évaluée, charger des cas et des seuils propres à un déploiement, appliquer des critères extensibles et produire un résultat indépendant de MediNova et de l'outil de télémétrie. Brancher le concierge actuel sur ce contrat ; vérifier que les cas existants continuent de fonctionner sans logique métier codée dans le moteur commun.

Enrichir ensuite les deux cas actuels avec des questions simples, mixtes, des échecs et des réponses nécessitant des sources. Faire revoir les critères métier ; mesurer qualité des réponses et des preuves, routage, erreurs, latence, tokens et coût par requête. Séparer tests déterministes, évaluation hors ligne et trafic réel. Versionner cas, rubriques, corpus, prompts, modèles et paramètres ; conserver les échecs et la variabilité entre répétitions.

**Preuve :** contrat d'évaluation utilisé par MediNova, tests montrant que le moteur ne dépend pas de ses agents ou de ses règles métier, rapport de référence reproductible et limites connues. La réutilisation réelle sera vérifiée sur le second domaine en phase 4. Sans cette mesure, une refonte du socle ne prouve aucune amélioration.

### 2. Comparer LangGraph au concierge actuel

Implémenter le workflow du concierge avec LangGraph derrière une frontière d'exécution minimale, en conservant ses appels A2A aux spécialistes et leurs outils MCP. Exécuter la même suite d'évaluation que pour smolagents ; mesurer qualité, routage, latence, coût, reprise et gestion des erreurs. Ne basculer le déploiement de référence qu'après examen des régressions et des bénéfices constatés.

**Preuve :** rapport comparatif reproductible, tests des contrats d'entrée/sortie, décision motivée de conserver ou de remplacer smolagents et possibilité de revenir à la version précédente.

### 3. Extraire le socle minimal réutilisable

Séparer progressivement le cœur technique des prompts, données, outils et règles propres à MediNova. Définir des contrats validés pour le profil client, les connecteurs, l'exécution et les permissions ; consolider le contrat d'évaluation amorcé en phase 1 à partir des besoins constatés. Garder MediNova comme première implémentation ; documenter ce qui se configure et ce qui demande un adaptateur testé. Éviter une réécriture générale et des abstractions sans deuxième besoin concret.

**Preuve :** MediNova fonctionne avec les contrats extraits et les mêmes évaluations ; une configuration invalide échoue clairement ; les éléments métier ne sont plus requis par le cœur commun.

### 4. Éprouver les contrats sur un second domaine réduit

Choisir un cas d'usage d'un **autre domaine**, petit et local, avec d'autres données, outils et critères de réussite. L'intégrer par les contrats et les adaptateurs prévus, sans dupliquer le cœur. Mesurer le travail spécifique et noter toute modification du socle qu'exige ce cas. Il s'agit d'un test de modularité, **pas encore d'un déploiement client**.

**Preuve :** les deux cas utilisent le même cœur avec configurations, sources et évaluations distinctes. Chaque changement du cœur est justifié, testé sur les deux cas et documenté comme apprentissage sur les contrats.

### 5. Sécuriser et exploiter un pilote client

Préparer une instance dédiée avec images et configurations reproductibles, CI/CD, environnements séparés, secrets, migrations, sauvegardes/restauration, supervision et retour arrière. Faire appliquer par le code les autorisations sur les outils **et sur les données de chaque utilisateur**, indépendamment des instructions au modèle ; tester les accès croisés, les injections de prompt et les actions abusives. Prévoir une approbation pour les actions à effet externe, ainsi que des limites de concurrence, délais, retries bornés, quotas, budgets et procédures d'incident. Définir rétention, suppression, audit et périmètre des données envoyées aux fournisseurs et à la télémétrie.

**Preuve :** création d'un environnement depuis les artefacts versionnés, droits vérifiés jusqu'aux connecteurs, scénarios d'abus refusés, test de charge ciblé, incident simulé, restauration et retour arrière documentés. Aucun contenu client n'est exporté sans décision explicite. La réussite de la phase 4 seule ne satisfait pas ces critères.

### 6. Améliorer en continu

Faire remonter les échecs et retours autorisés dans un jeu d'évaluation maintenu. Tester chaque modification de données, prompt, modèle, outil ou workflow contre la version en service ; comparer qualité, sécurité, latence et coût avant promotion. Garder l'historique des décisions et des versions pour expliquer un résultat et revenir à une version précédente.

**Preuve :** une modification pilotée par un échec observé, évaluée sur les deux cas d'usage, livrée sur le pilote sans régression acceptée et réversible.

## Conditions d'acceptation d'un déploiement client

Un déploiement ne devient pas « prêt client » parce que l'interface fonctionne. Il faut une validation métier des cas critiques, des droits sur les données vérifiés, des actions bornées, des métriques et alertes utiles, une estimation des coûts et un runbook couvrant panne, restauration et retour arrière. Les seuils précis sont fixés avec le client selon son risque ; le socle impose que ces décisions existent et soient testables.

## Décisions à prendre au moment de l'implémentation

- Définir la première interface de profil client à partir des besoins réels de MediNova et du second cas, sans prétendre que `config/agents.yaml` est déjà une configuration multi-client.
- Choisir le deuxième cas d'usage pour éprouver la transférabilité des contrats plutôt que pour démontrer un agent de plus.
- Choisir les adaptateurs et l'infrastructure après mesure des exigences : un outil existant peut fournir une capacité du socle s'il respecte les contrats de sécurité, portabilité et exploitation.
- Décider du mode d'hébergement et des fournisseurs modèle pour chaque client selon ses données et contraintes ; ne pas promettre une portabilité parfaite entre services différents.

Cette roadmap guide la transformation de MediNova en premier déploiement d'un produit réutilisable. Elle ne décrit ni un framework déjà achevé ni une certification de sécurité ou de conformité.

## Références de conception

Ces produits et guides illustrent des capacités existantes ; ils ne constituent pas un choix de dépendances pour Agentic Lab :

- [Dify Workspaces](https://dify-docs.docs7.io/en/self-host/use-dify/workspace/readme) : regroupement des applications, connaissances, modèles et membres dans un espace de travail.
- [LangGraph et LangChain](https://docs.langchain.com/oss/python/learn) : workflows explicites pour les parcours nécessitant davantage de contrôle que la boucle d'agent standard.
- [LangSmith Assistants](https://docs.langchain.com/langsmith/configuration-cloud) : séparation entre un graphe déployé et la configuration versionnée de ses assistants.
- [Haystack Production Usage](https://docs.haystack.deepset.ai/docs/production-usage) : évaluation et traçage des pipelines avant et après déploiement.
- [AWS, plateforme d'IA générative multi-tenant](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/multi-tenant-generative-ai-platform-scenario.html) : isolation, quotas et attribution des coûts par client.
- [OWASP, Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) : permissions et autonomie excessives des agents dotés d'outils.
