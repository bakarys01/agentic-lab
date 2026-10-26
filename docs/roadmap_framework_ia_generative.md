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

## Choix de déploiement initial

Le premier objectif est une **instance dédiée par client** : configuration, stockage, clés, comptes de service, journaux et budgets séparés. Le code et les contrats sont communs ; l'environnement d'exécution et les données ne le sont pas. Cette frontière doit être démontrée par des tests et un examen des accès, pas déduite du nom d'un conteneur ou d'un identifiant client.

Une plateforme multi-clients mutualisée serait une étape ultérieure, seulement si son intérêt opérationnel compense la complexité supplémentaire : isolation logique de bout en bout, contrôle des ressources partagées, autorisations, quotas, migrations et facturation par client. Le mode dédié reste possible pour un client dont les contraintes l'exigent.

## Plan de réalisation et preuves de sortie

Les phases ci-dessous sont **à réaliser** pour le framework. MediNova fournit certains composants de départ (agents configurés, MCP, A2A, Compose, tests et traces), mais ne satisfait pas à lui seul les critères de sortie.

### 1. Mesurer le déploiement de référence

Stabiliser un jeu de cas MediNova revu, avec qualité des réponses et des sources, routage, erreurs, latence, tokens et coût par requête. Séparer tests déterministes, évaluation hors ligne et trafic réel. Versionner cas, rubriques, corpus, prompts, modèles et paramètres ; conserver les échecs et la variabilité entre répétitions.

**Preuve :** rapport de référence reproductible et limites connues. Sans cette mesure, une refonte du socle ne prouve aucune amélioration.

### 2. Formaliser les contrats du socle

Extraire progressivement les interfaces nécessaires pour profil client, sources, outils, modèles, workflow et résultats d'évaluation. Valider les configurations au démarrage. Conserver les adaptateurs MediNova comme première implémentation ; éviter une réécriture générale avant de connaître les besoins du second cas.

**Preuve :** contrats documentés, tests de compatibilité, erreurs de configuration explicites et MediNova fonctionnant toujours avec la même suite d'évaluation.

### 3. Construire un second déploiement de référence

Choisir un cas d'usage d'un **autre domaine**, avec d'autres données et critères de réussite. Faire passer son intégration par les contrats : nouveaux connecteurs ou règles aux points d'extension prévus, sans dupliquer le cœur. Comparer le coût d'intégration et relever chaque modification du socle exigée par ce deuxième client.

**Preuve :** deux applications déployées séparément à partir du même socle, chacune avec ses données, permissions et évaluations. Les changements du cœur sont justifiés et répercutés sur les deux.

### 4. Durcir la sécurité et la gouvernance

Faire appliquer l'autorisation des sources et outils par le code, indépendamment des instructions au modèle. Définir des identités de service à privilèges minimaux, protéger les secrets, valider les entrées/sorties, tester les injections de prompt et les appels d'outil abusifs. Les actions à effet externe ou difficilement réversibles ont une politique d'approbation. Définir rétention, suppression, audit et périmètre exact des données exportées en télémétrie.

**Preuve :** tests d'accès croisés refusés, scénarios d'abus exécutés, inventaire des données et revue des privilèges. Aucun contenu client n'est envoyé à un fournisseur ou outil d'observabilité sans décision explicite.

### 5. Industrialiser le déploiement et l'exploitation

Produire des images et configurations reproductibles, CI/CD, environnements séparés, gestion des secrets, migrations, sauvegardes/restauration, supervision et procédure de retour arrière. Définir limites de concurrence, délais, retries bornés et comportement en cas de panne du modèle, d'un outil ou d'une source. Prévoir des quotas et des budgets mesurés par déploiement ; une alerte seule ne constitue pas une limite de dépense.

**Preuve :** création d'un environnement client depuis les artefacts versionnés, déploiement d'une nouvelle version, test de charge ciblé, incident simulé, restauration et retour arrière documentés.

### 6. Améliorer en continu

Faire remonter les échecs et retours autorisés dans un jeu d'évaluation maintenu. Tester chaque modification de données, prompt, modèle, outil ou workflow contre la version en service ; comparer qualité, sécurité, latence et coût avant promotion. Garder l'historique des décisions et des versions pour expliquer un résultat et revenir à une version précédente.

**Preuve :** une modification pilotée par un échec observé, évaluée sur les deux déploiements, livrée sans régression acceptée et réversible.

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
- [LangSmith Assistants](https://docs.langchain.com/langsmith/configuration-cloud) : séparation entre un graphe déployé et la configuration versionnée de ses assistants.
- [Haystack Production Usage](https://docs.haystack.deepset.ai/docs/production-usage) : évaluation et traçage des pipelines avant et après déploiement.
- [AWS, plateforme d'IA générative multi-tenant](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/multi-tenant-generative-ai-platform-scenario.html) : isolation, quotas et attribution des coûts par client.
- [OWASP, Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) : permissions et autonomie excessives des agents dotés d'outils.
