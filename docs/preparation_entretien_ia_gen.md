# Préparation d'entretien — ingénierie IA générative et agents

Cette fiche sert à **répondre à l'oral**, pas à réciter des définitions. Pour chaque question : définir le concept, expliquer le choix technique, puis donner une preuve ou une limite de MediNova. Les réponses ci-dessous sont des formulations courtes à adapter au poste et à l'interlocuteur.

**Fil conducteur (45 secondes).** « J'ai construit MediNova, une application de référence où un concierge traite la demande, délègue par A2A à des agents spécialisés et où ces agents accèdent à leurs outils par MCP. L'API, les conversations persistantes, les conteneurs, la CI et des traces de métadonnées existent. Je transforme maintenant cette application en socle réutilisable : évaluation configurable, comparaison des orchestrateurs, puis validation sur un second domaine. Je distingue ce que j'ai mesuré de ce qui reste à expérimenter. »

## 1. Les bases

**1. Qu'est-ce qu'un LLM ?** Un modèle probabiliste qui prédit des tokens à partir d'un contexte. Il peut produire une réponse convaincante sans disposer d'une preuve ; il faut donc contrôler ses sorties et, si nécessaire, les relier à des sources.

**2. Qu'est-ce qu'un agent IA ?** Un système qui utilise un modèle pour choisir des actions vers un objectif, observe leurs résultats et peut poursuivre ou terminer. Un simple appel au modèle qui reformule un texte n'est pas nécessairement un agent.

**3. Agent, assistant et workflow : quelle différence ?** « Assistant » décrit surtout l'interface ou le rôle vu par l'utilisateur. Un workflow fixe impose les étapes ; un agent dispose d'une marge de décision, par exemple pour sélectionner un outil. Je préfère un workflow déterministe si le parcours est connu : il est plus simple à tester et à exploiter.

**4. Qu'est-ce qu'un tool ?** Une capacité exécutable exposée avec un contrat d'entrée et de sortie : recherche, calcul, lecture de données ou action. Le modèle peut demander son appel, mais le code doit valider les paramètres, l'autorisation et les effets avant de l'exécuter. Un tool n'est ni un agent ni une source de données en soi.

**5. Quelles sont les cinq couches fonctionnelles d'un agent ?** Rôle/instructions, actions/outils, décision/planification, connaissance/mémoire, évaluation/feedback. Les séparer permet de modifier un prompt, un outil ou une source sans confondre leurs responsabilités et de mesurer l'effet de chaque changement.

## 2. Modèles, prompts et sorties

**6. Comment choisir un modèle ?** Je pars d'un jeu de tâches représentatif et de contraintes de confidentialité, latence, budget, langues et capacités d'appel d'outils. Je compare qualité et coût **par tâche réussie**, plutôt qu'un classement général de modèles.

**7. À quoi servent température et top-p ?** Ils contrôlent l'échantillonnage de la génération. Une valeur plus basse peut réduire la variabilité, sans garantir une réponse exacte ou reproductible ; j'enregistre les paramètres et répète les essais lorsque la variabilité compte.

**8. Qu'est-ce qu'un bon prompt système ?** Il définit le rôle, les limites, les outils autorisés, la manière de traiter l'incertitude et le format attendu. Il ne remplace ni une autorisation codée ni une validation de sortie. Les prompts doivent être versionnés avec la configuration du modèle.

**9. Pourquoi des sorties structurées et validées ?** Elles rendent les échanges entre composants vérifiables. Un schéma détecte une valeur manquante ou mal formée ; il ne prouve pas que le contenu est vrai. En cas d'échec de validation, je traite l'erreur explicitement plutôt que d'interpréter une réponse libre comme fiable.

## 3. MCP, outils et A2A

**10. Quel problème MCP résout-il ?** MCP standardise l'exposition de capacités d'un serveur à un client compatible : notamment outils, ressources et prompts. Dans MediNova, les agents utilisent actuellement des **outils MCP** ; cela n'implique pas que toutes les autres capacités MCP soient utilisées.

**11. MCP et A2A : quelle frontière ?** MCP relie un agent à des capacités/outils ; A2A relie le concierge à d'autres agents disposant de leurs propres responsabilités. Dans MediNova : utilisateur → concierge → A2A → spécialiste → MCP → outil/source.

**12. Comment sécuriser un outil ?** Schéma d'entrée, vérification d'identité et de droits, accès minimal à la source, délai, limite de volume, journalisation sans contenu sensible et réponse d'erreur contrôlée. Pour une action à effet externe, je prévois une autorisation explicite et, selon le risque, une validation humaine.

**13. Quel transport MCP choisir ?** Le transport dépend de la topologie : processus local pour un outil proche de l'agent, transport réseau pour un service séparé. La décision tient compte de l'authentification, des droits, de la latence, des pannes et de l'exploitation ; le protocole ne résout pas ces sujets à lui seul.

## 4. Orchestration multi-agent

**14. Quand ajouter un agent spécialisé ?** Quand une responsabilité distincte exige ses propres outils, données, règles ou cycle de déploiement et améliore un critère mesuré. Multiplier les agents pour découper artificiellement un prompt ajoute du routage, du coût et des possibilités de panne.

**15. Hub-and-spoke ou agents qui collaborent entre pairs ?** Le hub-and-spoke donne au concierge la coordination et une synthèse finale ; c'est la topologie actuelle de MediNova. Une collaboration entre pairs peut servir à d'autres tâches, mais complique la responsabilité, les permissions et le débogage.

**16. Qu'est-ce qu'un handoff ?** Le transfert d'une tâche et de son contexte à un autre agent, avec un résultat ou une erreur attendue en retour. Je teste le bon destinataire, les informations transmises, le délai et le comportement si l'agent appelé échoue.

**17. Comment décider si le multi-agent vaut la peine ?** Comparer au parcours simple sur les **mêmes cas** : justesse, routage, latence, coût, taux d'échec et facilité d'exploitation. MediNova a une architecture multi-agent fonctionnelle ; cette comparaison systématique reste à faire.

## 5. Raisonnement et boucles

**18. Que signifie ReAct ?** Alterner décision, action sur un outil et observation du résultat. C'est utile quand les étapes dépendent des données rencontrées ; je borne le nombre d'étapes et vérifie les résultats d'outils avant de poursuivre.

**19. Comment éviter une boucle sans fin ou inutile ?** Limites d'étapes, de durée et de dépense ; détection d'appels répétés sans progrès ; condition d'arrêt et réponse d'échec explicite. MediNova dispose de limites d'étapes et d'un délai A2A, mais la détection de stagnation et le budget de bout en bout restent à éprouver.

**20. Faut-il toujours demander au modèle de planifier ?** Non. Une planification explicite est une hypothèse à tester sur des tâches complexes. Si elle augmente tokens et latence sans améliorer le résultat, un flux plus simple convient mieux. L'évaluation porte sur les actions et les réponses observables, pas sur une chaîne de pensée interne.

## 6. RAG, recherche et mémoire

**21. Qu'est-ce que le RAG ?** Une génération alimentée par des éléments retrouvés dans des sources externes. La recherche et la réponse finale sont deux étapes distinctes à évaluer ; retrouver un passage pertinent ne garantit pas que la réponse le cite correctement.

**22. Recherche lexicale, vectorielle ou hybride ?** La lexicale retrouve des termes précis, la vectorielle rapproche des formulations sémantiques, l'hybride combine les signaux. Le choix dépend des questions et d'un corpus annoté. La recherche de politique MediNova sert de point de départ lexical ; un RAG hybride mesuré est encore prévu.

**23. Comment mesurer la recherche ?** Avec des questions et passages pertinents annotés : rappel@K, précision@K ou mesures de classement selon le cas. Je mesure séparément l'exactitude, l'ancrage et la qualité des citations de la réponse produite.

**24. Historique, mémoire et état du workflow : même chose ?** Non. L'historique conserve des tours de conversation, la connaissance regroupe les sources consultables et l'état du workflow garde les étapes d'une exécution ou d'une reprise. Leurs durées de vie et permissions diffèrent. MediNova possède un historique borné ; les autres formes ne doivent pas être supposées acquises.

## 7. Évaluation et feedback

**25. Qu'est-ce qu'une bonne baseline ?** Un jeu de cas versionné, représentatif et revu par le métier, des critères explicites, une exécution reproductible et un rapport des résultats **et des échecs**. Il faut enregistrer versions du code, prompt, modèle, paramètres, corpus et évaluateur avant de comparer deux variantes.

**26. Pourquoi les tests unitaires ne suffisent-ils pas ?** Ils vérifient des contrats déterministes. L'évaluation mesure aussi la qualité de réponses probabilistes sur des cas réels ou représentatifs. Les deux sont complémentaires ; un test vert ne prouve pas une réponse métier correcte.

**27. Comment évaluer un agent multi-outils ?** Mesurer réponse finale, choix d'agent, sélection et arguments d'outils, qualité des preuves, erreurs, latence, tokens et coût. Un agent peut donner la bonne réponse par hasard en ayant consulté la mauvaise source.

**28. Peut-on utiliser un LLM comme juge ?** Oui pour accélérer une évaluation fondée sur une rubrique précise, mais il peut se tromper ou favoriser certains styles. Je calibre ses notes contre des évaluations humaines, conserve les désaccords et ne lui confie pas seul les cas à fort enjeu.

**29. Comment le feedback améliore-t-il le système ?** Un échec autorisé devient un cas d'évaluation versionné ; on identifie la composante responsable, change une variable principale, compare à la baseline, puis décide de livrer ou de revenir en arrière. Les contenus client ne partent pas automatiquement vers un outil externe.

**30. Où en est MediNova sur ce point ?** Deux cas et un runner déterministe vérifient aujourd'hui routage, outils et fragments de réponse. Le contrat d'évaluation réutilisable, les rubriques métier approfondies, le coût par cas et le rapport de référence sont les prochains travaux ; ils ne sont pas encore livrés.

## 8. Déploiement et fiabilité

**31. Que faut-il livrer avec le code ?** Images, configuration et migrations versionnées, secrets gérés hors Git, tests de déploiement, métriques, sauvegarde/restauration et procédure de retour arrière. Docker Compose facilite le développement de MediNova, mais ne constitue pas à lui seul un déploiement client prêt pour la production.

**32. Comment traiter la panne d'un modèle ou d'un agent ?** Délais bornés, retries seulement quand ils sont sûrs, réponse partielle ou erreur explicite, et traçage du composant en cause. Pour une action à effet externe, l'idempotence empêche qu'un retry la reproduise involontairement.

**33. Que versionner pour reproduire une release IA ?** Code, dépendances, prompts, configuration, modèle et paramètres, versions des données/index, critères d'évaluation et résultats. Un modèle distant peut changer : noter son identifiant et les limites de reproductibilité observées.

## 9. Sécurité et gouvernance

**34. Quelle est la différence entre instruction au modèle et contrôle d'accès ?** Une instruction peut guider la réponse mais n'est pas une barrière de sécurité. Le serveur et les connecteurs doivent contrôler l'identité, les droits sur les outils et l'accès aux données de l'utilisateur avant chaque opération.

**35. Qu'est-ce qu'une injection de prompt ?** Une instruction malveillante placée dans une entrée ou une source non fiable pour détourner le comportement de l'agent. Je sépare données et instructions, limite les outils, vérifie les autorisations en code et teste des scénarios d'exfiltration et d'actions abusives.

**36. Comment isoler deux clients ?** Démarrer avec des instances, secrets, stockages, journaux et budgets séparés. L'isolation doit être testée jusqu'aux sources de données ; un identifiant client dans le prompt ne suffit pas. C'est une cible du framework, pas une garantie déjà démontrée par MediNova.

## 10. Observabilité et coûts

**37. Quelles traces conserver ?** Identifiant de requête, agents et outils appelés, durées, erreurs, modèle, tokens et versions utiles au diagnostic. MediNova envoie des **métadonnées** à Langfuse ; le contenu des conversations n'y est pas exporté par défaut.

**38. Que mesure le coût par tâche réussie ?** Dépense totale d'un ensemble d'essais divisée par les tâches réellement réussies, en précisant les prix, la date et les coûts inclus. Un modèle moins cher par token peut coûter davantage s'il échoue, répète des appels ou nécessite une revue humaine.

**39. Comment éviter une facture imprévue ?** Plafonds de tokens, étapes et appels, contrôle de concurrence, quotas par déploiement, alertes et budget exécutoire. Une alerte informe ; seule une limite appliquée par le système borne réellement la dépense.

## 11. Techniques avancées et recul critique

**40. Faut-il un Tree-of-Thought, une mémoire en graphe ou un « agent cognitif » ?** Pas par principe. Je pars d'un échec concret, formule une hypothèse, compare à la solution simple sur les mêmes cas et mesure qualité, latence, coût et risques. Si le gain n'est pas démontré, je conserve l'architecture la plus simple.

**41. Quelle est la décision la plus importante dans un projet agentique ?** Déterminer ce qui doit être **décidé par le modèle** et ce qui doit rester déterministe : autorisations, calculs fiables, critères de terminaison et effets externes. Cette frontière rend le système plus testable, explicable et exploitable.

## Exercice oral de fin

Prendre une question réelle de MediNova et l'expliquer en deux minutes : besoin utilisateur → routage par le concierge → appel A2A → outil MCP → source → réponse → trace → critère d'évaluation. Refaire l'exercice avec une panne d'outil. Terminer en nommant **une limite actuelle** et **la mesure** qui permettrait de choisir la prochaine amélioration.

## Sources et périmètre

- Micheal Lanham, *AI Agents in Action, Second Edition*, chapitres 1 à 10 : cadre pédagogique pour les thèmes et le vocabulaire. Cette fiche reformule les notions et n'est pas un résumé exhaustif du livre.
- [Architecture MediNova](architecture.md), [fonctionnement des agents](agents.md) et [roadmap du framework](roadmap_framework_ia_generative.md) : état du projet et travaux prévus. Vérifier ces documents et le code avant un entretien si le projet évolue.
