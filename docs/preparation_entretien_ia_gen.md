# Préparation d'entretien — ingénierie IA générative et agents

Cette fiche prépare un **entretien technique senior en IA générative et systèmes agentiques**. Les réponses sont formulées pour l'oral : une définition, un mécanisme, un arbitrage et, quand c'est pertinent, une preuve ou une limite de MediNova. Elles ne prétendent ni couvrir toutes les variantes d'une question ni remplacer une démonstration technique.

> **Présentation du projet en 45 secondes.** « MediNova est une application de référence : un concierge analyse la demande et délègue par A2A à des agents spécialisés. Ces agents accèdent à leurs outils par MCP ; les données proviennent notamment d'un contrat d'assurance PDF, d'un annuaire de médecins et de PostgreSQL. L'application possède une API, des conversations persistantes, des conteneurs, des contrôles CI et une télémétrie configurable limitée aux métadonnées. Je travaille maintenant à rendre l'évaluation réutilisable, puis à comparer les orchestrateurs sur un même jeu de cas de référence avant d'extraire un socle applicable à d'autres domaines. »

**Règle d'entretien :** ne jamais présenter la roadmap comme un résultat acquis. Une décision senior se défend par ses contraintes, ses compromis, ses mesures et ses risques résiduels.

## 1. Les bases

### 1. Qu'est-ce qu'un LLM ?

**Réponse.** Un LLM (*large language model*, grand modèle de langage) estime une distribution sur le prochain token à partir du texte et des autres entrées qu'il reçoit, puis génère une séquence. L'apprentissage lui donne des capacités de langage et de raisonnement utiles, mais pas une garantie de vérité, de fraîcheur ni d'accès à des données privées. Les informations fournies avec la demande, les outils et les sources complètent les connaissances du modèle ; la validation et les droits d'accès restent du ressort de l'application.

**À défendre.** Je distingue une réponse fluide d'une réponse fondée. Pour une question sur la franchise d'un contrat d'assurance, je veux retrouver la clause consultée et vérifier le montant cité, plutôt que croire une formulation plausible.

### 2. Qu'est-ce qu'un agent IA ?

**Réponse.** Dans une application d'IA générative, un agent fondé sur un LLM est un système orienté vers un objectif : il reçoit une demande, choisit une action avec le modèle, exécute une capacité autorisée, examine le résultat, puis s'arrête ou poursuit. Le modèle n'est qu'une partie du système ; outils, état d'exécution, contraintes et condition d'arrêt comptent autant. Une génération unique, même sophistiquée, n'est pas automatiquement un agent. Le terme *agent* est plus large en IA et peut aussi désigner un système sans LLM.

**À défendre.** L'autonomie est graduelle : choisir parmi trois outils de lecture n'a pas le même risque que modifier une base ou envoyer un message. Je limite les actions possibles selon leur risque et les résultats des tests qui montrent que l'agent les utilise correctement.

### 3. Agent, assistant et workflow : quelle différence ?

**Réponse.** *Assistant* désigne surtout le produit ou le rôle offert à l'utilisateur ; il peut être construit avec un simple appel LLM, un workflow ou un agent. Un *workflow* décrit dans le code les étapes et transitions : « classer → rechercher → vérifier → répondre ». Un *agent* choisit une partie du chemin à l'exécution : quel outil utiliser, faut-il refaire une recherche, quand s'arrêter. Les approches peuvent se combiner : une étape d'un workflow peut laisser le choix d'un outil au modèle.

**Arbitrage senior.** Si le parcours est stable et les règles métier strictes, je privilégie un workflow explicite : plus prévisible, testable et facile à auditer. Je réserve la décision au modèle lorsque la variété des demandes rend les branches écrites à l'avance difficiles à maintenir. Le concierge MediNova utilise actuellement smolagents ; LangGraph est un **candidat à comparer** sur les mêmes cas, pas encore une migration accomplie.

### 4. Qu'est-ce qu'un outil (*tool*) ?

**Réponse.** C'est une fonction ou un service que l'agent peut appeler, avec un nom, une description et un format d'arguments et de résultat. Un outil peut lire, calculer ou agir : chercher une clause, consulter la fiche d'un médicament, estimer un coût, créer une réservation. Le modèle peut proposer un appel, mais le code décide si cet appel est autorisé et valide ses arguments.

**Distinction importante.** Un outil n'est pas la source elle-même : « rechercher la politique » est une capacité, le PDF est une source. Une réponse d'outil est une donnée potentiellement non fiable, jamais une nouvelle instruction système. Je classe les outils par effet : lecture seule, écriture réversible, action externe ou irréversible ; les protections augmentent avec l'effet.

### 5. Quelles sont les cinq couches fonctionnelles d'un agent ?

**Réponse.** C'est une grille de conception, pas l'ordre d'exécution imposé à chaque requête :

| Couche | Responsabilité | Question d'ingénierie |
| --- | --- | --- |
| **Rôle / persona** | Objectif, périmètre, comportement attendu, limites et ton, souvent dans les instructions. | L'agent sait-il ce qu'il doit faire, quand refuser et quand demander une intervention humaine ? |
| **Outils / actions** | Accès contrôlé aux capacités de lecture, calcul ou action. | Schémas, droits, effets, délais et erreurs sont-ils maîtrisés ? |
| **Raisonnement / planification** | Choix de la prochaine étape et de la condition d'arrêt ; plan explicite si nécessaire. | Quelle décision laisser au modèle et laquelle coder ? |
| **Connaissance / mémoire** | Sources métier, tours précédents de conversation et informations nécessaires à la reprise d'une tâche, avec provenance et durée de vie. | Quelle information est autorisée, fraîche, pertinente et traçable ? |
| **Évaluation / feedback** | Mesure de la qualité et des échecs ; retour vers tests, prompts, outils ou données. | Comment prouver qu'un changement améliore le système ? |

**À défendre.** Les couches interagissent : une recherche fournit un résultat qui influence la prochaine action ; l'évaluation peut révéler un problème d'outil plutôt que de prompt. MediNova possède des éléments dans chaque couche, mais son évaluation se limite encore à deux cas simples. Toutes les applications n'ont pas besoin des mécanismes les plus avancés de chaque couche.

## 2. Modèles, prompts et sorties

### 6. Comment choisir un modèle ?

**Réponse.** Je commence par les tâches, non par un classement général : langues, qualité métier, capacité d'appel d'outils et de sorties structurées, latence, confidentialité, disponibilité, prix et contraintes d'hébergement. Je fixe un jeu de cas, un prompt et une configuration, puis compare les modèles sur ces mêmes cas. Une moyenne peut masquer un échec critique : j'examine aussi les questions difficiles, les questions mixtes et le taux d'erreur.

**Arbitrage senior.** Le coût utile est celui d'une **tâche réussie**, en incluant les appels répétés et les interventions humaines nécessaires. Un modèle moins cher par token peut être plus coûteux au total. La validation sur MediNova ne prouve pas qu'il sera adapté à un autre secteur.

### 7. À quoi servent température, top-p et limite de tokens ?

**Réponse.** Température et top-p modifient la façon de sélectionner les tokens dans la distribution de sortie ; la limite de tokens borne la génération. Des réglages plus conservateurs peuvent réduire la variété des réponses, mais ne corrigent ni une source erronée ni une instruction ambiguë. Certaines API ou familles de modèles n'exposent pas exactement les mêmes paramètres : je vérifie le comportement réel du fournisseur.

**À défendre.** Pour comparer deux versions, j'enregistre ces valeurs, la version du modèle et le nombre de répétitions. « Température zéro » ne suffit pas à garantir des sorties strictement identiques dans tous les environnements.

### 8. Qu'est-ce qu'un bon prompt système ?

**Réponse.** Il fixe la mission, les limites, les critères de réponse, les outils disponibles et la conduite à tenir si une preuve manque. Il doit être assez précis pour guider le modèle, assez court pour être maintenable et testé sur des demandes autorisées, ambiguës et interdites. Les instructions de l'application ne doivent pas être confondues avec les textes récupérés par recherche, qui peuvent contenir des instructions malveillantes.

**Limite.** Une phrase « n'accède pas aux données des autres » n'est pas un contrôle d'accès. Les droits, le calcul et les actions sensibles doivent être vérifiés en code. Je versionne prompt et paramètres ensemble, puis mesure l'effet de leur changement.

### 9. Pourquoi des sorties structurées et validées ?

**Réponse.** Une sortie typée permet à un autre composant de distinguer un résultat, une incertitude et une erreur, puis de valider champs, types et contraintes. Cela réduit les interprétations fragiles d'un texte libre. Le schéma ne garantit toutefois pas la justesse sémantique : une date valide peut être fausse.

**Gestion d'échec.** Si la sortie est invalide, je peux demander au modèle de la reformater un nombre limité de fois ; si elle reste invalide, le système renvoie une erreur explicite, avec des traces sans données sensibles. Les contrats d'entrée/sortie servent aussi aux tests de compatibilité lors d'un changement de modèle ou d'orchestrateur.

## 3. MCP, outils et A2A

### 10. Quel problème MCP résout-il ?

**Réponse.** MCP (*Model Context Protocol*) standardise la manière dont une application cliente découvre et utilise des capacités fournies par un serveur. Les primitives principales comprennent les **outils** (actions invocables), les **ressources** (contenus consultables) et les **prompts** (modèles d'interaction). Le protocole réduit les adaptateurs spécifiques à chaque combinaison agent–outil ; il ne définit pas, à lui seul, une politique d'autorisation métier.

**Exemple.** Les spécialistes MediNova appellent aujourd'hui des outils MCP. Ce choix ne signifie ni que les ressources et prompts MCP sont implémentés, ni qu'une base de données devient automatiquement sûre parce qu'elle est derrière MCP.

### 11. MCP et A2A : quelle frontière ?

**Réponse.** Dans MediNova, MCP sert à appeler les outils d'un agent spécialisé ; A2A (*Agent2Agent*) sert au concierge à confier une sous-tâche à un autre agent, décrit notamment par sa carte d'agent et ses compétences. On peut aussi encapsuler un agent comme simple outil, mais une telle interface ne représente pas nécessairement les échanges et le suivi de tâches prévus par A2A.

**Exemple MediNova.** Utilisateur → concierge → A2A → spécialiste → MCP → outil → source. Le concierge peut demander au spécialiste de politique de répondre à une sous-question ; le spécialiste utilise ensuite son outil de recherche sur le PDF. Les deux frontières se testent séparément.

### 12. Comment sécuriser un outil ?

**Réponse.** Je valide les arguments à la frontière, vérifie l'identité et les droits **avant** l'accès à la donnée ou l'action, applique le moindre privilège, borne durée et volume, puis contrôle les erreurs et la journalisation. Je ne donne pas au modèle une permission générale simplement parce que la description d'un outil dit « lecture seule ».

**Cas sensible.** Une consultation et un virement ne portent pas le même risque. Pour un effet externe ou irréversible : confirmation ou approbation selon la politique, identité de l'auteur, clé d'idempotence et journal d'audit adapté. Un résultat d'outil est une donnée non fiable, même s'il vient d'un serveur que nous exploitons.

### 13. Quel transport MCP choisir ?

**Réponse.** Le transport est un choix de topologie : un sous-processus local via stdio est simple pour un agent et son outil déployés ensemble ; un transport réseau permet de partager ou isoler le service, au prix d'une identité, de droits réseau, de délais et d'une exploitation supplémentaires. Je mesure la latence et teste les déconnexions, au lieu de choisir « réseau » parce que cela paraît plus moderne.

**État du projet.** MediNova utilise des serveurs MCP en sous-processus stdio pour les outils spécialisés. A2A reste une communication réseau entre le concierge et les serveurs d'agents.

## 4. Orchestration multi-agent

### 14. Quand ajouter un agent spécialisé ?

**Réponse.** Quand il existe une responsabilité réellement distincte : expertise, données et permissions propres, outils spécifiques, besoin de déploiement indépendant ou évaluation séparée. Le spécialiste doit apporter une valeur mesurable, pas seulement un nom de plus dans l'architecture.

**Coût caché.** Chaque délégation peut ajouter latence réseau, tokens, transfert d'informations entre agents, risques de panne et difficulté de diagnostic. J'évalue donc si un outil à entrées/sorties définies ou une simple étape de workflow suffit. Dans MediNova, les agents politique et médicament ont des sources et outils différents ; c'est une raison concrète de les isoler.

### 15. Orchestration centralisée ou collaboration entre pairs ?

**Réponse.** Dans une topologie *hub-and-spoke*, le concierge reçoit la demande, choisit les spécialistes et synthétise : la responsabilité finale est claire. Une collaboration entre pairs laisse davantage de coordination aux agents eux-mêmes ; elle peut aider sur une tâche décomposable, mais rend plus complexes la propagation des droits, la terminaison et l'attribution des erreurs.

**Arbitrage.** Je ne change pas de topologie sur une préférence esthétique. Je teste un cas qui échoue avec la topologie actuelle, puis compare qualité, coût et charge opérationnelle de l'alternative.

### 16. Qu'est-ce qu'un handoff ?

**Réponse.** C'est le passage à un autre agent d'une sous-tâche, des informations nécessaires pour l'exécuter et du résultat attendu. Le contrat doit préciser ce qui est transmis, comment l'identité et les droits de l'utilisateur sont pris en compte, les délais, les erreurs et quel composant reprend la main. Transférer toute la conversation peut coûter cher et divulguer des données inutiles ; je privilégie les seules informations nécessaires à la sous-tâche.

**Test concret.** Demander une information mêlant assurance et médicament, puis vérifier les deux destinataires, les deux résultats, la synthèse et le comportement si l'un des serveurs A2A tombe.

### 17. Comment prouver que le multi-agent vaut la peine ?

**Réponse.** Construire une version de référence plus simple, puis comparer sur les **mêmes questions, données, modèles et critères** : exactitude, bonne sélection d'agent et d'outil, fidélité aux sources, latence médiane et 95e percentile, coût par réussite et taux d'échec. Inclure les questions nécessitant plusieurs spécialistes et les pannes, pas seulement des démonstrations qui réussissent.

**État du projet.** L'architecture multi-agent MediNova fonctionne, mais cette comparaison expérimentale n'a pas encore produit de rapport de référence. Je ne revendique donc pas un gain chiffré du multi-agent.

## 5. Raisonnement et boucles

### 18. Que signifie ReAct ?

**Réponse.** ReAct désigne une alternance entre raisonnement sur la prochaine action, exécution et observation du résultat, puis nouvelle décision. Ce schéma permet d'adapter la suite à un résultat d'outil inconnu à l'avance. Par exemple, si la recherche ne trouve aucune clause, l'agent peut reformuler sa recherche ou signaler l'absence de preuve au lieu d'inventer.

**Risque.** Sans arrêt explicite, cette boucle peut répéter les mêmes appels. Je borne étapes et délai, surveille les erreurs et traite les données d'outil comme des observations, pas comme des instructions privilégiées.

### 19. Comment éviter une boucle sans fin ou inutile ?

**Réponse.** Je fixe des limites sur le nombre d'étapes et d'appels, la durée totale et, si nécessaire, la dépense. J'ajoute des critères de progrès observables : même requête répétée, même erreur, absence de nouvelle information utile ou alternance sans résultat entre agents. Quand une limite est atteinte, le système retourne une réponse partielle signalée comme telle ou une erreur explicite plutôt que poursuivre indéfiniment.

**État du projet.** MediNova borne le nombre d'étapes des agents et les appels A2A ont un délai. La détection des répétitions sans progrès et un plafond de dépense appliqué à toute la requête restent à implémenter et à tester en situation de panne.

### 20. Faut-il toujours demander au modèle de planifier ?

**Réponse.** Non. Un plan explicite peut aider quand la tâche a plusieurs dépendances, branches ou actions coûteuses. Pour une recherche et une réponse simples, il ajoute parfois des tokens et de la latence sans gain. Je compare exécution directe, workflow codé et planification agentique sur les mêmes cas.

**Nuance senior.** La planification du modèle ne doit pas devenir une autorisation. Un plan qui propose d'accéder à une donnée interdite reste bloqué par le code. Je mesure les actions et résultats observables, pas une chaîne de pensée privée du modèle.

## 6. RAG, recherche et mémoire

### 21. Qu'est-ce que le RAG ?

**Réponse.** Le RAG (*retrieval-augmented generation*, génération augmentée par recherche) fournit au modèle des éléments issus d'une source externe au moment de répondre. Dans un pipeline documentaire, on prépare et indexe les documents, on recherche des passages pour la question, puis on génère une réponse fondée sur ces passages. Les données peuvent aussi venir d'une recherche lexicale ou structurée : une base vectorielle n'est pas indispensable pour fournir au modèle des informations retrouvées.

**Deux contrôles distincts.** Mesurer si la recherche retrouve le bon passage, puis si la réponse respecte et cite ce passage. Le RAG peut encore halluciner, mal interpréter une clause ou citer une source hors sujet.

### 22. Recherche lexicale, vectorielle ou hybride ?

**Réponse.** La lexicale favorise des correspondances de termes, utile pour identifiants, noms de médicaments ou clauses précises. La vectorielle récupère des textes proches en sens, utile si la question reformule le document. L'hybride combine les deux et peut être complété par un reranker ; chacun ajoute coût et paramètres à régler.

**Arbitrage.** Je construis d'abord un corpus et des questions annotées, puis compare rappel, classement, latence et coûts. La recherche de politique MediNova est un point de départ lexical. Le médicament est interrogé dans PostgreSQL : pour une substance ou un code précis, une requête structurée peut rester le meilleur choix. Un RAG hybride n'est pas encore démontré.

### 23. Comment mesurer la recherche et la fidélité aux sources ?

**Réponse.** Je fais annoter les passages ou enregistrements pertinents pour chaque question. Le rappel@K mesure la proportion des passages pertinents retrouvés parmi les K premiers résultats ; la précision@K mesure la proportion de résultats pertinents dans ces K résultats. Les métriques de classement tiennent aussi compte de leur position. La métrique choisie dépend du risque : manquer une clause critique n'a pas le même coût qu'afficher un passage supplémentaire.

**Après recherche.** J'évalue séparément exactitude de la réponse, fidélité aux passages utilisés, couverture des points demandés et pertinence des citations. J'enregistre version du corpus, extraction, découpage, index et droits d'accès pour rendre le résultat interprétable.

### 24. Historique, mémoire et état du workflow : même chose ?

**Réponse.** Non. L'historique contient les tours de conversation ; la connaissance regroupe documents et données métier ; la mémoire durable pourrait conserver des faits ou préférences autorisés ; l'état du workflow décrit les étapes d'une exécution et ce qu'il faut reprendre après incident. Ils n'ont ni la même durée de vie, ni les mêmes permissions, ni les mêmes besoins de stockage.

**Exemple.** MediNova persiste les conversations et en injecte une portion bornée dans le contexte. Cela ne veut pas dire qu'il possède déjà une mémoire sémantique ou un checkpoint de workflow. Une mémoire longue durée impose aussi correction, suppression et prévention des informations périmées.

## 7. Évaluation et feedback

### 25. Qu'est-ce qu'une bonne baseline d'évaluation ?

**Réponse.** Une *baseline* est un résultat de référence obtenu avec une version connue du système sur un jeu de cas versionné. Ce jeu représente les demandes normales, les questions nécessitant plusieurs spécialistes, les questions ambiguës, les demandes hors périmètre et les pannes. Il comprend des réponses ou preuves attendues, des critères revus par des experts métier et un rapport reproductible. Je sépare les tests déterministes des jugements de qualité et des observations sur les requêtes réelles des utilisateurs.

**Reproductibilité.** Je conserve versions du code, des dépendances, du prompt, du modèle, des paramètres, des sources et de l'index, ainsi que la grille de notation, la date et les répétitions. Je publie le nombre de cas, les échecs et la variabilité ; un seul score moyen sans ces informations peut être trompeur.

### 26. Pourquoi les tests unitaires ne suffisent-ils pas ?

**Réponse.** Ils prouvent qu'une fonction ou un contrat se comporte comme prévu pour des entrées connues : validation, routage, erreurs, droits. Une application LLM peut satisfaire tous ces tests tout en donnant une réponse fausse ou sans preuve. L'évaluation de qualité examine des tâches complètes, parfois avec annotation humaine, sans remplacer les tests de régression déterministes.

**Exemple.** Vérifier que l'outil de politique a été appelé ne prouve pas que la franchise extraite est la bonne. Inversement, une réponse juste ne prouve pas que le système a respecté les permissions.

### 27. Comment évaluer un agent multi-outils ?

**Réponse.** J'évalue plusieurs niveaux : réponse finale, routage, outils et arguments, qualité des éléments retrouvés, erreurs, durée, tokens et coût. Je distingue *processus correct, réponse incorrecte* et *réponse correcte par chance malgré un mauvais processus*. Les cas de panne et d'outil non disponible font partie du jeu.

**Exemple.** Une question combinant assurance et médicament devrait faire intervenir les spécialistes attendus, accéder aux bonnes sources, puis synthétiser sans attribuer au contrat une propriété du médicament. Les traces servent au diagnostic ; le jugement métier porte sur le résultat.

### 28. Peut-on utiliser un LLM comme juge ?

**Réponse.** Oui, si la grille de notation décrit des critères observables et si le modèle évaluateur reçoit les sources nécessaires. Il peut aider à noter la pertinence ou la fidélité aux sources sur de nombreux cas. Mais il peut préférer une réponse élégante à une réponse exacte, confondre absence de preuve et erreur ou varier d'un essai à l'autre.

**Contrôle.** Je calibre ses décisions sur un échantillon revu humainement, mesure les désaccords, versionne prompt et modèle du juge et réserve les décisions à haut risque à une validation adaptée. Un juge LLM n'est pas un substitut automatique à l'expert métier.

### 29. Comment exploiter le feedback sans polluer l'évaluation ?

**Réponse.** Une erreur observée, avec les droits nécessaires, devient un cas reproduisible : entrée, résultat attendu, preuve et catégorie d'échec. J'identifie la composante en cause, change une variable principale, puis compare aux cas existants avant de livrer. Le jeu de développement peut grandir ; je conserve aussi des cas de validation distincts pour éviter d'optimiser seulement les exemples connus.

**Confidentialité.** Les traces de production ne deviennent pas automatiquement un dataset. Il faut décider ce qui peut être conservé, anonymisé, exporté, annoté et supprimé selon le client.

### 30. Où en est MediNova sur l'évaluation ?

**Réponse.** Deux cas versionnés et un programme d'exécution de ces cas vérifient les agents appelés, les outils utilisés et la présence de certains faits dans la réponse ; des tests couvrent ces vérifications. C'est utile pour détecter certaines régressions, mais insuffisant pour conclure à une exactitude médicale ou à la qualité des sources.

**Prochaine preuve.** Définir un contrat d'évaluation réutilisable, enrichir les cas et les grilles de notation métier, mesurer les coûts et produire un rapport de référence. Les tests automatiques de GitHub Actions et les traces Langfuse ne remplacent pas ce rapport.

## 8. Déploiement et fiabilité

### 31. Que faut-il livrer avec le code pour un client ?

**Réponse.** Une version déployable comprend images et dépendances identifiées, configuration validée, secrets hors Git, migrations de base de données, vérification de santé, observabilité, sauvegardes et restauration testée, procédure de retour arrière et responsable de l'incident. Les données et droits du client doivent rester séparés.

**État du projet.** MediNova se lance en local avec Docker Compose et dispose de vérifications automatiques dans GitHub Actions. Cela facilite la reproduction de l'environnement de développement, mais ne démontre ni la haute disponibilité, ni la restauration après incident, ni l'isolation des données d'un client.

### 32. Comment traiter la panne d'un modèle ou d'un agent ?

**Réponse.** Définir un délai par appel et un délai total pour la requête, transmettre une erreur compréhensible et ne retenter que les opérations sûres un nombre limité de fois. Si un spécialiste échoue, l'application peut fournir une réponse partielle en signalant l'information manquante ou demander de réessayer ; elle ne doit pas masquer qu'une source manque. Je teste séparément les pannes du modèle, d'un agent A2A, d'un outil MCP et de la base de données.

**Idempotence.** Répéter la même opération ne doit pas produire un second effet non voulu. Une lecture répétée est souvent acceptable, mais une écriture ou un paiement ne doit pas être exécuté deux fois après un délai dépassé sans confirmation du résultat. Une clé d'idempotence et un état persistant permettent de reconnaître la même opération. La stratégie dépend du contrat de l'outil.

### 33. Que versionner pour reproduire une version déployée d'une application IA ?

**Réponse.** Pour reproduire une version livrée, je conserve code, dépendances, prompts, configuration des agents, modèle et paramètres de génération, versions des sources et de l'index de recherche, critères et jeux d'évaluation, ainsi que résultats et date de l'expérience. Je distingue les éléments que nous versionnons des modèles hébergés par un fournisseur qui peuvent évoluer sous le même nom.

**Décision de déploiement.** Je compare la nouvelle version à celle en service sur le même jeu de cas, vérifie les régressions par catégorie et conserve la possibilité de revenir à l'ancienne. Un score amélioré ne compense pas nécessairement une nouvelle fuite de données ou une hausse de coût hors budget.

## 9. Sécurité et gouvernance

### 34. Quelle est la différence entre instruction au modèle et contrôle d'accès ?

**Réponse.** Une instruction exprime le comportement souhaité ; elle peut être ignorée, mal comprise ou contredite par une entrée adversariale. Un contrôle d'accès est une décision exécutable prise à chaque frontière sensible : qui appelle, sur quelles données, avec quel outil et pour quelle opération. L'API, le serveur d'outil et la source doivent appliquer cette décision, même si le modèle demande autre chose.

**Exemple.** « Ne lis que mes contrats » dans le prompt ne remplace pas un filtre d'autorisation sur la requête documentaire. Je teste un utilisateur qui tente d'accéder au document d'un autre et vérifie le refus dans le code, pas seulement dans la réponse générée.

### 35. Qu'est-ce qu'une injection de prompt et comment la limiter ?

**Réponse.** C'est une tentative de faire passer une instruction présente dans des données non fiables — page web, document, résultat d'outil, message utilisateur — pour une instruction prioritaire. Exemple : une page récupérée demande à l'agent de révéler ses secrets ou d'appeler un outil interdit. La défense ne repose pas sur une formule magique dans le prompt.

**Mesures.** Séparer explicitement les sources des instructions, réduire les permissions, vérifier chaque action au point d'exécution, limiter les sorties vers l'extérieur et tester des scénarios adversariaux. Je surveille aussi les refus abusifs : une protection trop agressive peut empêcher une tâche légitime.

### 36. Comment isoler deux clients ?

**Réponse.** Le point de départ retenu pour le framework est une instance dédiée par client : stockage, secrets, comptes de service, configuration, journaux, jeux d'évaluation et budgets séparés. Je teste les accès croisés jusque dans les connecteurs et les sauvegardes ; une séparation nominale dans un prompt ou un identifiant ne prouve rien.

**Arbitrage senior.** Héberger plusieurs clients dans une même instance peut optimiser les coûts, mais exige un filtrage strict des données, des quotas séparés et des contrôles d'isolation dans chaque composant. Je ne choisis ce modèle qu'après avoir chiffré son intérêt et démontré l'isolation. MediNova n'a pas encore cette preuve client.

## 10. Observabilité et coûts

### 37. Quelles traces conserver et quelles métriques suivre ?

**Réponse.** Une trace relie les étapes d'une même requête : identifiant, agents et outils appelés, heures de début et durées mesurées, statut, modèle et tokens, éventuellement versions des sources **sans contenu sensible**. Les métriques agrégées répondent à d'autres questions : latence médiane et 95e percentile, taux d'échec, qualité par type de tâche, coût par réussite et charge des services. Je distingue une opération dont on mesure réellement la durée d'un enregistrement ajouté après coup pour comptabiliser les tokens.

**État du projet.** Quand la télémétrie est activée, MediNova exporte des métadonnées vers Langfuse, dont les appels A2A/MCP, leurs durées et la consommation de tokens. Le contenu des conversations n'est pas envoyé par défaut. Ces traces aident au diagnostic, mais ne remplacent ni les alertes opérationnelles, ni l'évaluation métier, ni le suivi du coût complet.

### 38. Que mesure le coût par tâche réussie ?

**Réponse.** Sur un ensemble défini, je divise le coût total par le nombre de tâches qui respectent les critères de réussite. J'annonce le périmètre : appels modèle, retries, outils payants, infrastructure, stockage et revue humaine selon l'expérience ; je date les tarifs utilisés. Je distingue coût par requête et coût par résultat utile.

**Exemple.** Un modèle qui coûte deux fois moins cher par appel mais réussit moitié moins souvent peut exiger davantage de retries ou d'interventions. Le choix dépend aussi de la latence et des erreurs critiques, pas du prix seul.

### 39. Comment éviter une facture imprévue ?

**Réponse.** Je combine limites appliquées par le système sur les tokens, étapes, appels d'outils, temps et concurrence ; quotas par client et budgets par période ; alertes avant la limite ; et comportement défini lorsque le plafond est atteint. Une alerte seule prévient, elle n'arrête pas une boucle. Je mesure la dépense réelle et vérifie comment le fournisseur facture les appels échoués ou interrompus.

**État du projet.** MediNova a des limites d'étapes et mesure des tokens ; les budgets de dépense par déploiement sont une cible de la roadmap, pas une capacité déjà validée.

## 11. Techniques avancées et recul critique

### 40. Faut-il un Tree-of-Thought, une mémoire en graphe ou un « agent cognitif » ?

**Réponse.** Ce sont des options de conception, pas des étapes obligatoires de maturité. Explorer plusieurs plans peut aider une tâche difficile mais accroît appels, tokens et latence ; une mémoire organisée en graphe peut représenter des relations entre entités mais ajoute stockage, gouvernance et maintenance. Les termes « cognitif » ou « métacognitif » doivent être traduits en comportements testables, comme la détection d'une boucle sans progrès ou la décision de demander l'intervention d'une personne.

**Arbitrage senior.** Je pars d'un échec mesuré, propose l'option la plus simple qui pourrait le corriger, puis compare qualité, coût, risques et exploitabilité. Si aucun gain net n'est démontré, je n'ajoute pas la technique.

### 41. Quelle est la décision la plus importante dans un projet agentique ?

**Réponse.** Définir ce que le modèle peut décider et ce que le système doit imposer. Le modèle est utile pour interpréter une demande, choisir parmi des capacités autorisées ou synthétiser des sources. Les permissions, calculs vérifiables, plafonds, effets externes et critères de promotion en production exigent des contrôles déterministes et auditables.

**Conclusion d'entretien.** La question n'est pas « combien d'agents ai-je ? », mais « quelle partie du problème exige une décision probabiliste, et comment puis-je prouver que l'ensemble reste correct, sûr et économiquement viable ? »

## 12. Comparaisons fréquentes en entretien

### 42. Quelle différence entre « vibe coding » et « agentic coding » ?

**Réponse.** « Vibe coding » est un terme informel : on décrit généralement une façon de produire du code en langage naturel en acceptant largement ce que l'IA génère, avec peu d'inspection de son fonctionnement. « Agentic coding » décrit plutôt une capacité ou un mode de travail : un agent de programmation explore le dépôt, modifie des fichiers, exécute des commandes et itère sur les résultats. Ce ne sont pas deux catégories opposées : utiliser un agent autonome sans relire ses changements peut aussi devenir du vibe coding.

**Arbitrage senior.** Je peux déléguer l'exécution, pas la responsabilité technique. Je précise l'objectif et les contraintes, examine le diff, vérifie les tests pertinents, la sécurité et les effets sur l'architecture avant d'accepter le résultat. L'autonomie de l'outil ne constitue pas une preuve de qualité.

### 43. RAG ou fine-tuning : comment choisir ?

**Réponse.** Le RAG récupère des informations depuis une source au moment de la requête et les fournit au modèle pour répondre. Il convient lorsque les faits changent, doivent être cités ou dépendent des droits d'accès. Le fine-tuning adapte les paramètres d'un modèle à partir d'exemples d'entraînement ; il peut améliorer un comportement, un format ou une tâche récurrente, mais ne garantit ni des faits à jour ni leur traçabilité. Les deux techniques peuvent se compléter.

**Arbitrage senior.** Je mesure d'abord où se situe l'erreur : document absent, recherche insuffisante, mauvaise utilisation du contexte ou génération incorrecte malgré un bon contexte. Le fine-tuning ne répare pas une source manquante ; ajouter une recherche ne corrige pas nécessairement un format de sortie instable. Pour MediNova, l'accès aux données de politique et de médicaments relève actuellement de la recherche et des outils, sans fine-tuning.

### 44. Prompt engineering ou fine-tuning : quand passer de l'un à l'autre ?

**Réponse.** Un prompt définit les instructions et, éventuellement, des exemples au moment de l'appel ; on peut le modifier et le versionner rapidement. Le fine-tuning demande un jeu d'exemples de qualité et une phase d'entraînement pour adapter le modèle. Je commence par préciser le contrat de sortie, tester plusieurs prompts et mesurer les erreurs sur un jeu de cas représentatif. Si un échec récurrent persiste et que des exemples fiables permettent de l'enseigner, je compare un modèle ajusté à la meilleure configuration sans ajustement.

**Critères.** Je regarde la qualité par catégorie, la robustesse hors des exemples d'entraînement, la latence, le coût total et la maintenance des données d'entraînement. Une amélioration sur la seule moyenne ne suffit pas si les erreurs critiques augmentent.

### 45. Quelle différence entre observabilité et évaluation ?

**Réponse.** L'observabilité montre ce qui s'est passé pendant l'exécution : agents et outils appelés, erreurs, latence, tokens et coût estimé. L'évaluation juge si le résultat satisfait des critères définis, par exemple exactitude des faits, pertinence des sources et respect d'une règle métier. Une requête sans erreur technique peut produire une mauvaise réponse ; une trace détaillée n'est donc pas un score de qualité.

**Arbitrage senior.** Je relie les cas évalués aux versions de prompts, modèles et sources, puis j'utilise les traces pour expliquer les échecs. En production, je suis séparément la santé du système et la qualité des réponses, avec une revue humaine pour les cas sensibles.

### 46. Quelle différence entre une preuve de concept et un service prêt pour un client ?

**Réponse.** Une preuve de concept démontre qu'un parcours peut fonctionner dans des conditions limitées. Un service client doit aussi tenir des objectifs de qualité mesurés, appliquer les droits d'accès, protéger et isoler les données, supporter les pannes, maîtriser les coûts et permettre la surveillance, la restauration et le retour arrière. La réussite d'une démonstration ne prouve pas ces propriétés.

**État du projet.** MediNova démontre déjà une chaîne multi-agent avec MCP, A2A, stockage et traces. Pour le déployer dans un autre secteur, il faudrait encore valider les sources et critères métier du client, l'isolation, les scénarios de panne et une baseline d'évaluation représentative.

## Exercice oral de fin

**Question de départ :** « Quel est mon deductible et quelle est la substance active de ce médicament ? »

1. Expliquer le routage vers les spécialistes politique et médicament, puis leur accès respectif à la source via MCP. Distinguer le fait extrait de la synthèse du concierge.
2. Expliquer la panne d'un spécialiste : délai, statut, réponse partielle possible et absence d'invention. Dire ce qui existe déjà dans le code et ce qui reste à tester.
3. Proposer un cas d'évaluation : agents/outils attendus, faits et sources à valider, cas d'erreur, latence et coût. Reconnaître que les deux cas actuels ne forment pas encore une baseline métier complète.
4. Conclure avec un arbitrage : garder plusieurs agents ou préférer un workflow plus direct ? Répondre par une comparaison sur les mêmes cas, pas par préférence de framework.

## Sources et périmètre

- Micheal Lanham, *AI Agents in Action, Second Edition*, chapitres 1 à 10 : cadre pédagogique pour les thèmes et le vocabulaire, notamment les couches d'agent (chapitre 1), MCP (3), orchestration (4), RAG et mémoire (6), évaluation (7), exploitation et sécurité (8). Cette fiche reformule les notions et n'est pas un résumé exhaustif du livre.
- [Architecture MediNova](architecture.md), [fonctionnement des agents](agents.md) et [roadmap du framework](roadmap_framework_ia_generative.md) : état du projet et travaux prévus. Vérifier ces documents et le code avant un entretien si le projet évolue.
- Spécifications officielles [MCP](https://modelcontextprotocol.io/specification), [A2A](https://a2a-protocol.org/dev/specification/) et [OpenTelemetry Trace API](https://opentelemetry.io/docs/specs/otel/trace/api/) : contrats et vocabulaire des protocoles ; vérifier la version implémentée par MediNova avant de revendiquer une capacité du standard.
- [OWASP LLM01 : Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) : risques, limites des défenses par prompt et principes de moindre privilège et de validation.
- [IBM : vibe coding](https://www.ibm.com/think/topics/vibe-coding), [Anthropic : évaluer les agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) et [Google Cloud : RAG ou fine-tuning](https://cloud.google.com/blog/products/ai-machine-learning/to-tune-or-not-to-tune-a-guide-to-leveraging-your-data-with-llms) : repères complémentaires pour les comparaisons de la section 12.
