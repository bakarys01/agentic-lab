# CACEIS — simulation d'entretien technique AI-Native Developer Python

Simulation ciblée sur la mission **Développeur Python — IT Innovation / AI Factory**. Chaque question est suivie d'une réponse formulée pour l'oral. Les réalisations décrites s'appuient sur le CV et sur le complément d'entretien BNP fourni ; les éléments propres à la mission BNP ne sont pas repris comme des faits sur CACEIS. Aucun résultat chiffré, incident précis ni usage personnel d'un assistant de code n'est établi par ces documents : cette fiche n'en invente pas. La [fiche générale](preparation_entretien_ia_gen.md) approfondit les concepts GenAI.

## Ouverture : parcours et méthode

### 1. Présentez-vous et dites-nous ce qui vous qualifie pour ce poste.

**Réponse.** « Je suis ingénieur IA et Data, avec un parcours qui va du ML classique à la GenAI et à leur mise en production. Chez Tradein, j'ai travaillé sur la fraude et les impayés avec des API de scoring. Chez Lisi Aerospace, j'ai industrialisé des pipelines et modèles sur AWS SageMaker, avec CI/CD et surveillance du drift. Plus récemment, j'ai travaillé sur des assistants RAG et multi-agents, leurs outils, leur ingestion documentaire et leur évaluation chez Base Claude Bernard et Sanofi. Ce poste combine Python, développement rapide assisté par IA et responsabilité de la qualité en production : c'est le point commun de ces expériences. »

### 2. Un métier vous demande un assistant IA. Quelle est votre première action ?

**Réponse.** « Je commence par préciser la tâche, les utilisateurs, les données autorisées et le coût d'une mauvaise réponse. Je demande des exemples de questions et les réponses acceptables ou inacceptables. Je définis une mesure de succès, y compris les refus et les cas limites. Ensuite seulement, je compare une recherche classique, un workflow avec LLM, un RAG ou un agent. Un assistant n'a pas besoin d'être agentique si le parcours est fixe. »

### 3. Donnez un exemple de collaboration entre métier, Data Science et ingénierie.

**Réponse.** « Sur l'assistant médical de Base Claude Bernard, le sujet couvrait à la fois l'architecture Data/IA, les outils d'accès à l'information et l'industrialisation. Mon rôle de lead impliquait d'articuler le besoin des professionnels de santé avec les choix de recherche documentaire, les données structurées et les contraintes de déploiement. Je séparerais dans la discussion ce que le métier valide — pertinence et sécurité de la réponse — de ce que l'ingénierie vérifie — données, droits, latence, tests et exploitation. »

## Réalisations : démontrer ma contribution en production

Pour chaque projet, ma réponse suit le même fil : **problème réel → ce que j'ai personnellement conçu ou implémenté → raison du choix → mise en production → mesure et surveillance → limite ou incident**. Je distingue toujours ma contribution de celle de l'équipe. Si un chiffre ou un incident précis n'est pas disponible, je ne le remplace pas par une affirmation invérifiable : j'explique ce que nous mesurions, ce que j'ai observé et ce que je vérifierais dans les traces ou rapports du projet.

### 4. Chez Sanofi, sur quoi avez-vous personnellement travaillé dans SILC Agent ?

**Réponse.** « SILC Agent exploitait des connaissances internes, notamment issues de SharePoint, dans une architecture RAG amenée à évoluer vers des agents. Ma contribution principale portait sur trois axes. D'abord, j'ai conçu et développé la gestion du cycle de vie des bases vectorielles Pinecone : création, mise à jour, renommage et suppression, en lien avec l'ingestion. Ensuite, j'ai conçu l'évaluation LLM avec W&B Weave. Enfin, j'ai contribué à l'évolution vers AWS Bedrock AgentCore et Strands pour l'orchestration et le tool calling. Le besoin était de faire évoluer les connaissances et les capacités sans perdre la traçabilité ni la maîtrise des changements dans un environnement GxP. Je distingue ces contributions de la plateforme construite par l'ensemble de l'équipe. »

### 5. Que signifie concrètement “gérer le cycle de vie” d'un index Pinecone ?

**Réponse.** « Un index RAG ne doit pas rester figé après une ingestion initiale. J'ai développé les opérations qui permettaient de créer, mettre à jour, renommer et supprimer les bases vectorielles, puis je les ai reliées au pipeline d'ingestion. L'enjeu était la cohérence entre les documents sources et les connaissances réellement interrogeables. Lors d'une modification ou d'une suppression de source, il faut savoir quelle représentation est concernée et éviter de continuer à servir une version obsolète. C'est un sujet d'exploitation et de gouvernance de données autant qu'un sujet de recherche sémantique. »

### 6. Comment avez-vous rendu l'évaluation LLM exploitable chez Sanofi, au-delà d'une démo ?

**Réponse.** « J'ai travaillé sur un cadre d'évaluation W&B Weave qui associait des cas de test, des résultats et des traces aux versions de la solution. L'intérêt de séparer l'offline et l'online était de pouvoir comparer un changement avant sa diffusion, puis de surveiller ce qui se passe sur des requêtes réelles. Un LLM-as-a-Judge pouvait aider à apprécier certaines réponses, mais je ne le traiterais pas comme une vérité terrain : ses critères doivent être explicités et confrontés à des validations humaines. L'industrialisation tient à cette répétabilité, à la traçabilité et à la possibilité de repérer une régression après un changement d'index, de prompt ou de modèle. »

### 7. Pourquoi avoir contribué à l'évolution vers Bedrock AgentCore et Strands ?

**Réponse.** « La plateforme commençait à cumuler recherche documentaire, outils et tâches de nature différente. L'évolution vers Strands visait à structurer l'orchestration, le tool calling et les échanges entre agents ; AgentCore s'inscrivait dans l'industrialisation de ce runtime dans l'écosystème AWS. J'ai contribué à cette évolution, pas à la conception exclusive de toute la plateforme. Avant d'ajouter des agents, je regarderais toujours si un workflow explicite couvre le besoin avec moins de complexité. Le passage vers un runtime Python conteneurisé facilitait aussi l'intégration avec les composants Data, RAG et évaluation utilisés par l'équipe. »

### 8. Chez Base Claude Bernard, qu'avez-vous conçu vous-même dans l'architecture multi-agent ?

**Réponse.** « En tant que lead Data & IA, j'ai porté les choix d'architecture et participé à l'implémentation des composants structurants. J'ai conçu un concierge qui orientait les demandes vers des agents spécialisés, notamment médicament, vaccination, biologie médicale et recommandations. Chaque agent utilisait des outils métier exposés par MCP : selon la question, l'outil pouvait accéder à PostgreSQL, au RAG ou à une API. J'ai choisi cette séparation parce que les sources et les règles différaient selon le domaine ; je ne voulais pas confier indistinctement tous les accès à un seul agent. J'ai également coordonné les sujets Data, Engineering et métier, sans développer seul l'ensemble de la plateforme. »

### 9. Concrètement, comment avez-vous construit l'ingestion documentaire et la recherche chez Base Claude Bernard ?

**Réponse.** « J'ai conçu un pipeline Prefect pour ingérer plusieurs sources, normaliser les documents, les découper, enrichir leurs métadonnées, puis produire les représentations dense et sparse indexées dans Qdrant. J'ai prévu le versionnement et les mises à jour incrémentales : une correction documentaire devait pouvoir se refléter dans l'index sans reconstruire aveuglément toute la chaîne. À la requête, la recherche hybride avec BGE-M3 et SPLADE produisait des candidats, ensuite réordonnés par reranking. Je séparais la mesure du retrieval — par exemple précision et rappel sur des questions annotées — de la fidélité de la réponse finale aux passages retrouvés. C'est ainsi que l'on peut savoir si une mauvaise réponse vient de l'index, de la recherche ou du modèle. »

### 10. Comment mainteniez-vous les données à jour et les pipelines exploitables ?

**Réponse.** « Les sources médicales n'avaient pas toutes le même rythme de mise à jour. J'ai travaillé sur des pipelines Prefect capables d'orchestrer l'ingestion, de suivre les exécutions et de traiter les ajouts, modifications et suppressions sans reconstruire systématiquement tout l'index. Le versionnement et les métadonnées permettaient de rattacher une réponse à une source et à son état. En cas d'échec d'une étape, il fallait pouvoir identifier le lot concerné et reprendre proprement plutôt que laisser un index partiellement mis à jour sans visibilité. »

### 11. Comment saviez-vous que cet assistant médical fonctionnait en conditions réelles ?

**Réponse.** « Je ne m'appuyais pas seulement sur quelques questions de démonstration. Nous suivions plusieurs niveaux : le routage vers le bon agent, les appels d'outils, la qualité du retrieval, la fidélité aux sources, puis les performances et la traçabilité de bout en bout. Le déploiement conteneurisé, la CI/CD et le serving GPU permettaient de traiter aussi les contraintes d'exploitation. Je distingue cependant “déployé” de “qualité clinique démontrée” : pour une affirmation de ce niveau, il faudrait citer le protocole de validation métier, son échantillon et ses résultats. »

### 12. Pourquoi vLLM et RunAI dans cette expérience ?

**Réponse.** « Les modèles open source étaient servis sur une infrastructure GPU on-premise. vLLM répondait au besoin d'inférence avec une attention particulière au débit et à l'utilisation de la mémoire GPU ; RunAI servait à gérer et partager ces ressources au niveau de l'infrastructure. Ce choix demandait une surveillance de la saturation, des erreurs et de la latence, en plus de la qualité des réponses. Je présenterais les mesures effectives du projet avant d'affirmer un gain de performance ou de coût par rapport à une autre solution. »

### 13. Chez Lisi Aerospace, qu'avez-vous réellement mis en production côté MLOps ?

**Réponse.** « J'ai travaillé sur l'industrialisation de modèles dans SageMaker : pipelines de données avec Glue, PySpark, Airflow et S3 ; tests et CI/CD GitLab ; déploiement automatisé ; Model Registry ; suivi du drift et alerting. Ce que j'apporte n'est pas seulement un entraînement de modèle : c'est une chaîne qui rend la version servie identifiable et les changements observables. J'ai également développé ou exposé des services Data/ML via API REST, Lambda et API Gateway, avec authentification Cognito. En entretien, je peux suivre une version précise depuis ses données d'entrée jusqu'au service appelé par l'utilisateur, puis expliquer comment un signal de drift est examiné avant de décider une action. »

### 14. Comment reliez-vous les pipelines Data aux modèles servis chez Lisi ?

**Réponse.** « S3 jouait le rôle de Data Lake ; Glue et PySpark préparaient les données ; Airflow orchestrait les dépendances et les traitements. Je travaillais aussi sur les contrôles de qualité en amont. Les modèles passaient ensuite par la validation, le versionnement dans SageMaker Model Registry et le déploiement. Cette chaîne permettait de diagnostiquer un problème de prédiction en remontant à la version du modèle et à la donnée qui l'alimentait, plutôt que de regarder uniquement l'API d'inférence. »

### 15. Donnez un exemple d'arbitrage technique que vous avez dû faire, plutôt qu'une liste d'outils.

**Réponse.** « Sur la recherche documentaire médicale, le choix n'était pas simplement “mettre Qdrant”. Une recherche lexicale peut mieux retrouver un terme exact ou un code ; une recherche dense peut retrouver une formulation proche ; le reranking améliore le tri des candidats mais ajoute de la latence. J'ai donc conçu une recherche hybride et une évaluation du retrieval pour vérifier ce que chaque étape apportait. L'arbitrage devait tenir compte à la fois de la pertinence et du temps de réponse. Je ne prétendrais pas à un gain chiffré sans ressortir le rapport de comparaison correspondant. »

### 16. Racontez un incident de production que vous avez personnellement diagnostiqué et corrigé.

**Réponse.** « Je peux décrire la méthode que j'applique : partir du symptôme et de son impact, identifier la version concernée, suivre logs et traces, isoler la couche fautive, corriger ou revenir à une version sûre, puis ajouter un test ou une alerte pour éviter la répétition. Mais je ne vais pas attribuer à Sanofi, Base Claude Bernard ou Lisi un incident précis que mon CV ne documente pas. Pour répondre complètement à cette question en entretien, je dois choisir un incident réel que j'ai vécu et pouvoir en expliquer la chronologie, mon intervention exacte et le résultat observé. »

### 17. Que présenteriez-vous comme preuve que vos travaux ont dépassé le stade du PoC ?

**Réponse.** « Je montrerais, selon le projet, le chemin de livraison et d'exploitation. Chez Lisi : modèles versionnés dans SageMaker, tests, CI/CD, API, monitoring du drift et alertes. Chez Base Claude Bernard : ingestion incrémentale, index et outils exploités par l'assistant, conteneurs, CI/CD, serving GPU et mesures de retrieval et de réponse. Chez Sanofi : évaluations répétables, traçabilité, déploiement multi-environnements et documentation dans un contexte GxP. Ces éléments prouvent un travail d'industrialisation ; je préciserais encore les volumes, SLA, résultats de qualité et responsabilités opérationnelles avant de revendiquer un niveau de service donné. »

## Python, API et qualité du code

### 18. Comment concevez-vous une API Python de scoring ou d'inférence ?

**Réponse.** « Je définis un contrat d'entrée/sortie versionné, valide les données à la frontière, distingue les erreurs client, les indisponibilités temporaires et les erreurs serveur, puis protège l'accès selon le cas d'usage. Je sépare la couche HTTP de la logique d'inférence et de l'accès aux données pour tester chaque partie. J'ajoute délais, limites de charge, health checks et métriques. Chez Tradein, les modèles de fraude et d'impayés étaient exposés via FastAPI ; chez Lisi, j'ai également travaillé sur des services Data/ML exposés par API. »

### 19. Quelles différences entre tests unitaires, intégration et bout en bout dans une application IA ?

**Réponse.** « Un test unitaire vérifie une règle déterministe, une validation ou une transformation sans dépendance externe. Un test d'intégration vérifie le contrat entre API, base, outil, modèle simulé ou service externe. Un test de bout en bout suit un scénario utilisateur réel, depuis la requête jusqu'au résultat. Pour un LLM, je ne teste pas une phrase exacte si plusieurs formulations sont valides : je teste les contraintes, les faits attendus et les erreurs critiques. J'ajoute un jeu d'évaluation pour la qualité statistique, qui répond à une autre question que la suite de tests logiciels. »

### 20. Une PR générée par un agent de code passe les tests. L'acceptez-vous ?

**Réponse.** « Pas sur ce seul critère. Je relis le diff, les hypothèses, les migrations et dépendances, les chemins d'erreur, l'autorisation et les cas que les tests ne couvrent pas. Je vérifie que les tests sont pertinents et ne reproduisent pas simplement l'implémentation générée. Je compare la solution au besoin initial et demande une correction ciblée si le code est fragile. Le développeur garde la responsabilité du changement. »

### 21. Que signifient pour vous “vibe coding” et “agentic coding” ?

**Réponse.** « Vibe coding est un terme informel pour une production de code largement pilotée par prompts, parfois acceptée sans compréhension ni revue suffisantes. Agentic coding désigne plutôt un outil capable d'explorer le dépôt, modifier le code, lancer des commandes et itérer. Ce ne sont pas des opposés : un agent autonome peut aussi produire du code accepté à l'aveugle. Dans une équipe de production, je cadre la tâche, borne les permissions, relis les changements et valide le résultat par des tests et une revue. »

### 22. Comment demanderiez-vous à un coding agent d'ajouter un endpoint ?

**Réponse.** « Je lui donne le contrat HTTP, les schémas, les règles d'authentification, les exemples valides et invalides, les fichiers concernés et les critères d'acceptation. Je lui demande d'inspecter les conventions du dépôt avant de modifier, d'ajouter les tests pertinents, puis de me fournir le diff et les commandes de vérification. Je garde les secrets hors du prompt et j'examine toute dépendance ou action externe proposée. »

### 23. Quels outils d'assistance au code maîtrisez-vous réellement ?

**Réponse.** « Je distingue les capacités générales — complétion, génération ciblée, exploration autonome du dépôt, exécution de tests — des outils précis. Mon niveau sur Copilot, Cursor, Claude Code ou ChatGPT dépend de ma pratique effective. Je peux démontrer mon processus sur une modification concrète : cadrage, génération, inspection du diff, test, correction et revue. Je préfère être exact sur l'outil utilisé plutôt que revendiquer une expertise identique sur les quatre. »

## ML, MLOps et déploiement

### 24. Expliquez une mise en production ML de bout en bout à partir de votre expérience.

**Réponse.** « Chez Lisi Aerospace, j'ai travaillé sur la chaîne Data/ML avec AWS Glue, PySpark, Airflow et S3, puis sur l'industrialisation de modèles SageMaker. La séquence est : contrôler la donnée, entraîner et évaluer contre une référence, enregistrer le modèle et ses dépendances, exécuter tests et CI/CD, déployer une version identifiable, puis surveiller le drift et les incidents. Le point décisif est de pouvoir relier une prédiction à la version du code, du modèle et des données, et de savoir revenir en arrière. »

### 25. Quelle différence entre data drift, concept drift et baisse de performance ?

**Réponse.** « Le data drift est un changement de distribution des entrées par rapport à la référence. Le concept drift est un changement de la relation entre entrées et cible. Une baisse de performance est constatée lorsque des labels ou un signal métier permettent de mesurer la qualité des prédictions. Un drift ne prouve pas à lui seul que le modèle est devenu mauvais ; inversement, on peut perdre en qualité sans qu'un indicateur simple de drift le détecte. Je combine contrôles de données, métriques métier et seuils d'alerte adaptés au délai d'obtention des labels. »

### 26. Comment évalueriez-vous un modèle de fraude ?

**Réponse.** « Je sépare entraînement et test dans le temps pour limiter les fuites d'information. Je regarde rappel et précision de la classe fraude, matrice de confusion, calibration si les scores guident une décision et performance par segment pertinent. Le seuil dépend du coût des faux positifs — dossiers légitimes bloqués — et des faux négatifs — fraudes manquées. Chez Tradein, j'ai travaillé sur des modèles de fraude et d'impayés ; je ne présenterais pas une accuracy globale comme preuve suffisante sur une classe rare. »

### 27. Comment versionner et promouvoir un modèle ?

**Réponse.** « J'enregistre l'artefact, le code, les dépendances, les paramètres, la définition des données et le rapport d'évaluation. Une nouvelle version passe des contrôles automatisés et des critères métier définis avant sa promotion. Le déploiement progressif et le retour arrière dépendent de l'infrastructure, mais la version servie doit toujours être identifiable. Mon expérience chez Lisi inclut SageMaker, Model Registry, CI/CD et monitoring ; je peux expliquer la chaîne que j'y ai mise en œuvre sans attribuer au projet des mécanismes non documentés dans mon CV. »

### 28. Comment déployer un LLM open source et quels risques surveiller ?

**Réponse.** « Je dimensionne le modèle et la capacité GPU selon la charge, le contexte, la latence et le débit attendus. Je mesure temps au premier token, débit, mémoire, saturation, taux d'erreur et coût par requête utile. Je prévois limites de concurrence et de contexte, health checks et stratégie en cas d'indisponibilité. Chez Base Claude Bernard, le serving utilisait vLLM sur une infrastructure GPU on-premise gérée avec RunAI. Le choix on-premise peut répondre à des contraintes d'exploitation ou de données, mais je ne suppose pas que ce soit toujours moins cher que le cloud. »

### 29. Une version est déployée mais la qualité se dégrade. Que faites-vous ?

**Réponse.** « Je vérifie d'abord la réalité et l'étendue du signal : version en service, type de requêtes touchées, données entrantes, changements d'index ou de prompt, pannes de dépendances. Si l'impact est important, je reviens à la dernière version validée ou limite le trafic. Je conserve les traces nécessaires, reproduis sur des cas représentatifs et corrige la cause. Je ne réentraîne ni ne change de modèle avant d'avoir localisé le défaut. »

## GenAI, RAG et agents

### 30. Pourquoi choisir un RAG plutôt qu'un fine-tuning ?

**Réponse.** « Si la réponse dépend de documents actualisés ou de droits d'accès, le RAG permet de chercher l'information au moment de la requête et de citer les sources. Le fine-tuning adapte le comportement du modèle à partir d'exemples, mais ne garantit ni fraîcheur ni provenance des faits. Je commence par mesurer où l'échec se produit : recherche, contexte fourni ou génération. Les deux techniques peuvent se combiner si les besoins le justifient. »

### 31. Décrivez un pipeline RAG robuste, de l'ingestion à la réponse.

**Réponse.** « J'ingère les sources avec leur provenance et leurs droits, nettoie et découpe les documents, ajoute des métadonnées, indexe puis versionne l'index. À la requête, j'applique les filtres d'accès, recherche des passages pertinents, éventuellement rerank, puis génère une réponse fondée sur ce contexte en conservant les références. Je mesure séparément la qualité de recherche et celle de la réponse. Chez Base Claude Bernard, j'ai travaillé sur une ingestion Prefect multi-sources, des mises à jour incrémentales et une recherche hybride dense/sparse dans Qdrant avec reranking. »

### 32. Pourquoi combiner recherche lexicale, vectorielle et reranking ?

**Réponse.** « La recherche lexicale capte bien des termes exacts, codes et noms propres ; la vectorielle retrouve des formulations proches malgré des mots différents. Le reranking réordonne un ensemble limité de candidats avec un signal souvent plus précis, mais ajoute de la latence et du coût. Je compare chaque étape sur des questions annotées, notamment les cas où l'une des méthodes manque le bon document. L'architecture hybride n'est justifiée que si elle améliore la qualité à un coût acceptable. »

### 33. Comment mesurez-vous un RAG ?

**Réponse.** « Je construis un jeu de questions avec documents ou faits de référence. Pour le retrieval, je mesure par exemple recall@k et, si les annotations le permettent, precision@k ; je contrôle aussi les droits d'accès. Pour la réponse, j'évalue exactitude, appui sur les sources, citations et comportement lorsqu'aucune source fiable n'est disponible. Un LLM-as-a-judge peut aider à couvrir plus de cas, mais je confronte ses notes à des jugements humains et suis ses désaccords. Chez Sanofi, mon CV mentionne un framework d'évaluation W&B Weave avec évaluations offline/online et LLM-as-a-Judge. »

### 34. Quand choisir un workflow, un agent unique ou plusieurs agents ?

**Réponse.** « Je prends la solution la plus simple qui satisfait le besoin mesuré. Un workflow explicite convient si les étapes sont prévisibles. Un agent unique est utile si le choix d'outil dépend de demandes variées. Plusieurs agents peuvent aider lorsque les responsabilités, données ou permissions sont réellement distinctes, mais ajoutent routage, handoffs, latence et modes de panne. Je compare les trois sur les mêmes cas avant de justifier la complexité multi-agent. »

### 35. À quoi servent MCP et A2A, et quelle est la différence ?

**Réponse.** « MCP standardise l'accès d'un agent à des capacités comme des outils ou des ressources. A2A organise l'échange entre agents exposés comme services. Dans MediNova, le concierge délègue à des agents spécialisés via A2A ; ces agents utilisent des outils accessibles via MCP. Cela sépare les responsabilités, mais les protocoles ne règlent pas à eux seuls les droits, la qualité des réponses ou les pannes. »

### 36. Un agent spécialisé ne répond pas. Que renvoyez-vous à l'utilisateur ?

**Réponse.** « Je fixe un timeout et un budget de retries sûrs. Je conserve le résultat des autres agents et marque explicitement la partie manquante. Si le cas d'usage le permet, je fournis une réponse partielle avec une limite claire ; sinon je renvoie une erreur exploitable ou demande une reprise. Je ne transforme jamais une absence de résultat en fait inventé. Je trace l'agent, l'outil, le statut et la durée pour diagnostiquer l'échec. »

### 37. Que tracer et que ne pas envoyer à un service d'observabilité ?

**Réponse.** « Je trace identifiants techniques, versions, agents et outils utilisés, statuts, durées, tokens et coût estimé, avec des corrélations entre services. Je minimise les données personnelles et le contenu métier exporté ; la politique de conservation et l'accès aux traces doivent être définis. Dans MediNova, l'intégration Langfuse a été conçue pour transmettre des métadonnées plutôt que le texte des conversations. Une trace montre le déroulement ; elle ne prouve pas que la réponse est correcte. »

## Sécurité, architecture et arbitrages

### 38. Un document récupéré ordonne au modèle d'ignorer ses instructions. Que faites-vous ?

**Réponse.** « Je traite le document comme une donnée non fiable, pas comme une instruction privilégiée. Les autorisations sont vérifiées par l'application et par l'outil au moment de l'action ; elles ne reposent pas sur le prompt. Je limite les permissions et les sorties externes, puis teste ce scénario comme une injection de prompt. Si une réponse cite le document, je vérifie que ses assertions restent ancrées dans le contenu autorisé. »

### 39. Comment feriez-vous cohabiter plusieurs clients ou métiers sur une même plateforme IA ?

**Réponse.** « Je sépare configuration, secrets, stockage, index, journaux, budgets et jeux d'évaluation. Les filtres d'accès doivent s'appliquer avant la recherche et au niveau des outils, pas seulement dans la génération. Une instance dédiée par client simplifie la preuve d'isolation ; une plateforme mutualisée peut optimiser le coût mais demande des contrôles de séparation plus stricts. Je teste explicitement les accès croisés et les sauvegardes. »

### 40. Comment optimisez-vous qualité, latence et coût d'un service GenAI ?

**Réponse.** « Je définis un seuil de qualité et un budget par tâche réussie, puis mesure la latence de bout en bout et par étape. Si le goulot est le retrieval, je travaille l'index et le reranking ; si c'est le modèle, je regarde contexte, choix du modèle, batching ou nombre d'appels. J'évite les outils et handoffs inutiles. Chaque optimisation repasse sur le même jeu d'évaluation : une baisse de coût qui augmente les erreurs métier n'est pas un gain. »

### 41. Comment documentez-vous une solution pour qu'une autre équipe puisse la maintenir ?

**Réponse.** « Je documente le besoin et les critères de qualité, les contrats API et outils, la provenance des données, les versions des modèles/prompts/index, les décisions d'architecture et leurs alternatives, puis les procédures de déploiement, surveillance et retour arrière. Les exemples d'appels et les erreurs attendues doivent être exécutables ou vérifiables. La documentation utile répond à “comment modifier sans casser” et “que faire si cela échoue”, pas seulement à “comment lancer une démo”. »

## Échange technique en anglais

### 42. “Tell us about a production ML system you worked on.”

**Answer.** “At Lisi Aerospace, I worked on ML industrialization on AWS SageMaker. The work covered data pipelines, automated testing and CI/CD, model versioning, deployment, and drift monitoring. The key engineering challenge was to make each release reproducible and observable, rather than treating the model artifact as the whole product. I would evaluate a new version against a baseline, deploy an identifiable version, and monitor both data changes and business performance.”

### 43. “How do you use coding agents without losing engineering control?”

**Answer.** “I break the task into a clear contract, constraints, and acceptance criteria. I let the assistant inspect and propose changes within a limited scope, then review the diff, run relevant tests, and check error handling, security, and maintainability. I do not equate a passing test suite with correctness. The agent accelerates implementation; the team owns the design and the production risk.”

### 44. “Why would you use multiple agents instead of a simpler workflow?”

**Answer.** “I would use multiple agents only if the specialization brings a measurable benefit, such as distinct tools, permissions, or independent tasks. I would compare it with a deterministic workflow on the same evaluation set, including quality, latency, cost, and failure modes. If the simpler design performs as well, I would keep the simpler design.”

## Questions à poser au recruteur

1. Quels sont les deux ou trois cas d'usage IA prioritaires et comment mesurez-vous aujourd'hui leur succès ?
2. Quelles sont les contraintes sur les données, l'hébergement, les modèles et l'utilisation des assistants de code ?
3. Qui valide la qualité métier, les risques et la mise en production d'une nouvelle version ?
4. Quelle chaîne MLOps et quelles pratiques de tests/documentation existent déjà dans l'AI Factory ?
5. Qu'attendez-vous concrètement de la personne recrutée pendant les trois premiers mois ?

## Sources

- CV fourni : `sidibe_bakary_latest_cv.pdf`, deux pages. Les expériences citées proviennent du CV ; les réponses techniques sont des formulations proposées pour l'entretien, pas des résultats chiffrés attestés par le document.
- Complément d'entretien fourni : `BNP_Complement_Final_mis_a_jour.docx`. Il précise les contributions et choix techniques chez Sanofi, Base Claude Bernard et Lisi Aerospace. Ses affirmations propres à la mission BNP Paribas ne sont pas transposées à CACEIS.
- Description de la mission CACEIS fournie dans la conversation. Aucune hypothèse sur la stack interne ou les règles propres à CACEIS n'est présentée comme un fait.
- [Préparation technique générale](preparation_entretien_ia_gen.md) pour approfondir les définitions et compromis GenAI.
