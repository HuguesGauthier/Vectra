export default {
  // --- Général ---
  cancel: 'Annuler',
  save: 'Enregistrer',
  delete: 'Supprimer',
  edit: 'Modifier',
  add: 'Ajouter',
  close: 'Fermer',
  search: 'Recherche',
  actions: 'Actions',
  yes: 'Oui',
  no: 'Non',
  healthy: 'Sain',
  statusDegraded: 'Dégradé',
  statusError: 'Erreur',
  latencyFast: 'Rapide',
  latencyOk: 'Correct',
  latencySlow: 'Lent',
  lastSync: 'Dernière synchro',
  status: 'Statut',
  name: 'Nom',
  firstName: 'Prénom',
  lastName: 'Nom',
  description: 'Description',
  date: 'Date',
  size: 'Taille',
  fileSizeUnits: ['o', 'Ko', 'Mo', 'Go', 'To', 'Po', 'Eo', 'Zo', 'Yo'],
  type: 'Type',
  acl: "Liste de contrôle d'accès",
  fileCount: 'Objets',
  unknown: 'Inconnu',
  appDescription: 'Système de gestion RAG',
  source: 'Source',
  lastVectorized: 'Dernière vectorisation',
  recordsPerPage: 'Lignes par page :',
  excerpt: 'extrait',
  excerpts: 'extraits',
  file: 'fichier',
  files: 'fichiers',
  page: 'Page',
  from: 'depuis',
  rows: 'lignes',
  columns: 'colonnes',
  dataPreview: 'Aperçu des données',
  openFile: 'Ouvrir le fichier',

  // --- Authentification & Profil ---
  loginTitle: 'Vectra Admin',
  login: 'Connexion',
  logout: 'Déconnexion',
  username: "Nom d'utilisateur",
  password: 'Mot de passe',
  email: 'Courriel',
  signInToAccount: 'Connectez-vous à votre compte',
  pleaseTypeUsername: "Veuillez entrer votre nom d'utilisateur",
  pleaseTypeEmail: 'Veuillez entrer votre courriel',
  pleaseTypePassword: 'Veuillez entrer votre mot de passe',
  loginSuccessful: 'Connexion réussie',
  loginFailed: 'Échec de connexion. Vérifiez vos identifiants.',
  adminLabel: 'ADMIN',
  heartbeatLabel: 'PULSATION',
  roleAdmin: 'Administrateur',
  roleGuest: 'Invité',
  statusOnline: 'En ligne',
  statusOffline: 'Hors ligne',
  statusStopped: 'Arrêté',
  statusAnonymous: 'Anonyme',
  users: 'Utilisateurs',
  addUser: 'Ajouter un utilisateur',
  editUser: 'Modifier un utilisateur',
  role: 'Rôle',
  statusInactive: 'Inactif',
  statusActive: 'Actif',
  isActive: 'Est actif',
  newPasswordOptional: 'Nouveau mot de passe (Optionnel)',
  confirmDeleteUser: "Êtes-vous sûr de vouloir supprimer l'utilisateur {email} ?",
  userCreated: 'Utilisateur créé avec succès',
  userUpdated: 'Utilisateur mis à jour avec succès',
  userDeleted: 'Utilisateur supprimé avec succès',
  failedToFetchUsers: 'Échec de la récupération des utilisateurs',
  failedToCreateUser: "Échec de la création de l'utilisateur",
  failedToUpdateUser: "Échec de la mise à jour de l'utilisateur",
  failedToDeleteUser: "Échec de la suppression de l'utilisateur",
  invalidEmailArguments: 'Veuillez entrer une adresse courriel valide',
  emailAlreadyExists: 'Cet email est déjà utilisé par un autre utilisateur',
  cannotDeactivateSelf: 'Vous ne pouvez pas désactiver votre propre compte',
  maxFileSize: 'Taille max: {size}',
  removePhoto: 'Retirer la photo',
  dragToPosition: 'Glissez pour positionner',
  dragToPositionSlider: 'Curseur de position verticale',
  noUsersFound: 'Aucun utilisateur trouvé',
  addFirstUser: 'Ajoutez votre premier utilisateur pour commencer.',

  // --- Navigation & Menu ---
  menu: 'Menu',
  dashboard: 'Tableau de bord',
  analytics: 'Analytique',
  advancedAnalytics: 'Analytique Avancée',
  realTimeInsightsPerformance: 'Aperçu temps réel et métriques de performance',
  loadingAnalytics: "Chargement de l'analytique",
  cacheHitRate: 'Taux de succès du cache',
  dailyLlmCost: 'Coût quotidien LLM',
  topicDiversity: 'Diversité des sujets',
  pipelineStepBreakdown: 'Décomposition par étape',
  trendingQuestions: 'Questions tendances',
  costByAssistant: 'Coût par assistant',
  knowledgeBaseFreshness: 'Fraîcheur de la base de connaissances',
  noCostData: 'Aucune donnée de coût',
  noDocuments: 'Aucun document',
  noTrendsYet: 'Aucune tendance pour le moment',
  timeToFirstToken: 'Temps au premier jeton (TTFT)',
  topics: 'sujets',
  docs: 'docs',
  lastUpdate: 'Dernière mise à jour',
  noData: 'Aucune donnée',
  myAssistants: 'Mes assistants',
  knowledgeBase: 'Base de connaissances',
  settings: 'Paramètres',
  manageAppConfiguration: "Gérer la configuration de l'application",
  saveChanges: 'Enregistrer',
  general: 'Général',
  aiEngine: 'Moteur IA',
  embeddingEngine: 'Moteur de Vectorisation',
  chatEngine: 'Moteur de Discussion',
  system: 'Système',
  interface: 'Interface',
  language: "Langue de l'application",
  theme: 'Thème',
  restartRequiredInfo:
    'Les modifications des paramètres IA peuvent nécessiter un redémarrage ou une réinitialisation du worker.',
  embeddingWarning:
    "Modifier les paramètres d'embedding affecte l'indexation des documents. Les vecteurs existants peuvent nécessiter une re-vectorisation.",
  embeddingProvider: "Fournisseur d'embeddings",
  chatProvider: 'Fournisseur de discussion',
  apiKey: 'Clé API',
  modelName: 'Modèle de vectorisation',
  chatModel: 'Modèle de discussion',
  parameters: 'Paramètres',
  network: 'Réseau',
  networkName: 'Dossier',
  settingsSaved: 'Paramètres enregistrés avec succès',
  noChanges: 'Aucune modification à enregistrer',

  // Settings - AI & System
  geminiConfiguration: 'Configuration Gemini',
  openaiConfiguration: 'Configuration OpenAI',
  localConfiguration: 'Configuration Locale',
  baseUrl: 'URL de base',
  baseUrlHint: 'ex. http://localhost:11434',
  aiProvider: 'Fournisseur IA',
  gemini: 'Google Gemini',
  geminiTagline: 'Idéal pour grand context',
  geminiDesc:
    'Excelle pour maintenir de longues conversations et analyser plusieurs documents simultanément grâce à sa fenêtre de contexte massive.',
  openai: 'OpenAI ChatGPT',
  openaiTagline: 'Haute Performance',
  openaiDesc:
    'Reconnu pour son raisonnement logique et sa capacité à suivre des instructions complexes. Idéal pour des réponses précises et structurées.',
  mistral: 'Mistral AI',
  mistralTagline: "L'IA européenne performante",
  mistralLocal: 'Mistral AI (Local via Ollama)',
  mistralLocalDesc:
    'Exécutez des modèles avancés localement via Ollama. Privé et hors ligne. Nécessite des ressources matérielles suffisantes.',
  ollamaConfiguration: 'Configuration Ollama',
  ollama: 'Ollama (Local)',
  ollamaTagline: 'Exécutez des modèles localement',
  ollamaDesc:
    'La solution de référence pour faire tourner des LLM sur votre propre matériel. Privé, sécurisé et totalement hors-ligne.',
  mistralConfiguration: 'Configuration Mistral',
  mistralDesc:
    'Un LLM européen puissant reconnu pour son efficacité. Équilibré pour le raisonnement et le chat.',
  anthropicConfiguration: 'Configuration Anthropic',
  anthropic: 'Anthropic Claude',
  anthropicTagline: "L'IA sécurisée et fiable",
  anthropicDesc: "Des modèles d'IA avancés axés sur la sécurité, le raisonnement et la fiabilité.",
  localEmbedding: 'BAAI (Local)',
  local: 'Local',
  localTagline: 'Privé & Hors-ligne',
  localDesc:
    "S'exécute entièrement sur votre machine. Aucune donnée ne quitte votre réseau. Nécessite du matériel puissant.",
  recommended: 'Recommandé',
  popular: 'Populaire',
  public: 'Public', // Added
  private: 'Privé',
  transcriptionModel: 'Modèle de transcription audio',
  temperature: 'Température',
  topK: 'Top K',
  modelNameHint: 'ex. models/text-embedding-004',
  chatModelHintGemini: 'ex. gemini-1.5-flash, gemini-1.5-pro',
  chatModelHintOpenAI: 'ex. gpt-4-turbo, gpt-4o',
  chatModelHint: 'Modèle par défaut utilisé pour répondre aux questions',
  selectModel: 'Sélectionner un modèle',
  searchModels: 'Rechercher un modèle...',
  inputPrice: 'Entrée',
  outputPrice: 'Sortie',
  perMillionTokens: 'par 1M tokens',
  noModelsFound: 'Aucun modèle trouvé',
  categoryFlagship: 'Premium',
  categoryReasoning: 'Raisonnement',
  categoryBalanced: 'Équilibré',
  categoryEconomy: 'Économique',
  transcriptionModelHint: 'ex. gemini-1.5-flash',
  httpProxy: 'Proxy HTTP',
  proxyHint: 'Laisser vide si inutilisé',
  themeAuto: 'Auto',
  themeDark: 'Sombre',
  themeLight: 'Clair',
  langEnglish: 'Anglais',
  langFrench: 'Français',
  assistantNotVectorized: 'Assistant non vectorisé. Le chat est désactivé.',
  vectorizeSourcesToEnableChat: 'Veuillez vectoriser les sources de données pour activer le chat.',
  chatDisabledPlaceholder: 'Chat désactive - Assistant non vectorisé',

  chat: 'Discussion',
  systemOverview: "Vue d'ensemble système & Métriques temps réel",
  selectAssistant: 'Sélectionner un assistant',
  selectAssistantDesc: 'Choisissez un assistant pour commencer à discuter',
  startChatting: 'Commencer à discuter',
  noAssistantsForChat: 'Aucun assistant disponible pour discuter',
  createAssistantToChat: 'Créez un assistant dans la page Assistants pour commencer à discuter',
  connectedSources: 'Sources connectées',
  clickToChat: 'Cliquer pour discuter',
  noDescription: 'Aucune description',

  // --- Tableau de bord / Index ---
  backendApi: 'API Backend',
  application: 'Application',
  ingestionEngine: "Moteur d'ingestion",
  worker: 'Moteur Vectoriel',
  statusActiveUpper: 'ACTIF',
  statusStoppedUpper: 'ARRÊTÉ',
  statusOfflineUpper: 'HORS LIGNE',
  seenJustNow: "Vu à l'instant",
  noSignal: 'Aucun signal',
  localProviderWarning:
    'La vectorisation locale utilise votre processeur et est beaucoup plus lente que les fournisseurs cloud. Veuillez patienter.',
  connected: 'Connecté',
  storage: 'Stockage',
  storageOfflineTitle: 'Point de montage rompu',
  storageOfflineDesc:
    'Docker ne peut pas accéder à vos données. Veuillez modifier VECTRA_DATA_PATH dans votre fichier .env (racine du projet).',
  storageOnline: 'Stockage en ligne',
  storageOffline: 'Stockage hors ligne',
  storageFixTitle: 'Comment réparer le stockage',
  storageFixStep1: '1. Localisez le fichier .env à la racine du projet.',
  storageFixStep2: '2. Trouvez la variable VECTRA_DATA_PATH.',
  storageFixStep3: '3. Remplacez-la par un chemin physique (ex: C:/VectraData ou /home/user/data).',
  storageFixStep4: '4. Redémarrez les containers Docker.',
  storageFixPathLabel: 'Chemin racine du projet :',
  cpuUsage: 'Utilisation CPU',
  memoryUsage: 'Utilisation Mémoire',
  totalQueries: 'Requêtes Totales',
  processedSinceStartup: 'Traitées depuis le démarrage',
  systemLoadHistory: 'Historique de charge système',
  kbSize: 'Taille Base de Connaissances',
  totalVectorsIndexed: 'Total Vecteurs Indexés',
  totalVectors: 'Total Vecteurs',
  totalTokens: 'Total Jetons',
  sessions: 'Sessions',
  avgLatency: 'Latence Moy. (TTFT)',
  avgFeedback: 'Score Moy.',
  estMonthlyCost: 'Coût Mensuel Est.',
  basedOnTokenUsage: "Basé sur l'utilisation actuelle des jetons",
  estTimeSaved: 'Temps Économisé Est.',
  vsManualResearch: 'vs. Recherche Manuelle',
  live: 'EN LIGNE',
  offline: 'HORS LIGNE',
  workerOnline: 'Worker En Ligne',
  workerOffline: 'Worker Hors Ligne',
  cpuTotal: 'CPU Total',
  memoryTotal: 'Mémoire Totale',

  // Dashboard - Pipeline Stats
  mainDashboard: 'Tableau de bord',
  loadingDashboard: 'Chargement du tableau de bord',
  indexing: 'Indexation',
  usage30Days: 'Utilisation (30 jours)',
  activePipelines: 'Pipelines actifs',
  totalConnectors: 'Total Connecteurs',
  systemStatus: 'État du système',
  never: 'Jamais',
  successRate: 'Taux de succès',
  failedDocs: 'Documents échoués',
  justNow: "À l'instant",
  ago: 'écoulés',

  // --- Accueil ---
  sloganConnect: 'Connecter.',
  sloganVectorize: 'Vectoriser.',
  sloganChat: 'Clavarder.',
  actionConnect: 'Gérer les sources de données',
  actionVectorize: 'Indexer et traiter la base de connaissances',
  actionChat: 'Interagir avec les assistants',
  cardConnect: 'Connecter',
  cardVectorize: 'Vectoriser',
  cardChat: 'Clavarder',
  trendingQuestionsGlobal: 'Tendances Globales',
  requests: 'demandes',

  // --- Connecteurs (Base de connaissances) ---
  manageDataSources:
    "Alimentez votre IA avec le savoir de l'entreprise. Plus vous connectez de données ici, plus vos assistants deviennent intelligents et précis.",
  myDataSources: 'Mes sources de données',
  availableConnectors: 'Sources de données disponibles',
  selectType: 'Choisir le type',
  stepIntelligence: 'Moteur de Réponse',
  selectAIEngine: 'Sélectionner le moteur de réponse',
  configure: 'Configurer',
  configureProvider: 'Configurer les paramètres du fournisseur',
  selectAIEngineDesc:
    "Choisissez le modèle d'IA qui formulera les réponses et raisonnera sur vos données (ce n'est pas le moteur de vectorisation).",
  selectConnectorTypeDesc: 'Choisissez le type de source de données que vous souhaitez connecter.',
  searchConnectors: 'Rechercher des sources de données...',
  clickToChange: 'Cliquer pour changer',
  clickToBrowseConnectors: 'Cliquer pour parcourir les sources',
  tryAdjustingSearch: 'Essayez de modifier vos termes de recherche',
  sourcesSelected: 'sources sélectionnées',
  noSourcesSelectedHint: 'Aucune source sélectionnée',
  itemsSelected: 'sélectionné(s)',
  confirmSelection: 'Confirmer la sélection',
  performanceWarning: 'Attention Performance',
  mixedProvidersDesc:
    "Vous avez sélectionné des sources de données provenant de différents fournisseurs d'IA. Cela nécessite des requêtes séparées pour chaque fournisseur, ce qui peut ralentir le temps de réponse de l'assistant. Pour une performance optimale, essayez d'utiliser des sources de données vectorisées avec le même fournisseur.",

  // Vectorization Step
  selectVectorizationEngine: 'Moteur de vectorisation',
  selectVectorizationEngineDesc:
    'Choisissez le modèle qui convertira vos documents en vecteurs mathématiques pour la recherche.',
  geminiEmbeddings: 'Embeddings Gemini',
  geminiEmbeddingsDesc: 'Model: text-embedding-004',
  modelLabel: 'Modèle', // Added
  openaiEmbeddings: 'Embeddings OpenAI',
  openaiEmbeddingsDesc: 'Model: text-embedding-3-small',
  localEmbeddings: 'Embeddings Locaux',
  localEmbeddingsDesc: 'Privé & Sécurisé',
  engineNotConfigured: 'Moteur non configuré (Voir Paramètres)',
  notConfigured: 'Non configuré',
  rerankEngine: 'Moteur de Pertinence',
  cohereTagline: 'Précision supérieure',
  cohereDesc: "Fournisseur de modèles d'IA spécialisé dans la pertinence et le reranking pour une précision de recherche inégalée.",
  cohereRerankDesc: 'Recommandé pour la plus haute précision.',
  localRerankDesc: "S'exécute localement sur votre processeur avec FastEmbed.",
  modelDeprecationWarning:
    'Attention : Les modèles IA cloud peuvent être obsolètes avec le temps. Assurez-vous de choisir un modèle stable pour éviter de devoir re-vectoriser.',

  // --- Extraction Intelligente ---
  smartExtractionTitle: 'Intelligence & Extraction de Contexte', // Added
  enableSmartExtraction: "Activer l'extraction intelligente de métadonnées",
  aiContextEnhancement: 'Amélioration du contexte par IA',
  smartExtractionIntro: "Pour chaque segment de document, l'IA extraira :",
  smartExtractionTitleLabel: 'Titre',
  smartExtractionTitleDesc: 'Description concise',
  smartExtractionSummaryLabel: 'Résumé',
  smartExtractionSummaryDesc: "L'essence en une phrase",
  smartExtractionQuestionsLabel: 'Questions',
  smartExtractionQuestionsDesc: '3 questions stratégiques auxquelles le texte répond',
  smartExtractionTradeoff: 'Compromis',
  smartExtractionTradeoffDesc:
    "L'ingestion sera plus lente (~2-3s par segment), mais la précision de la recherche s'améliore considérablement.",

  // --- Stratégie de Récupération ---
  retrievalStrategy: 'Stratégie de Récupération',
  retrievalStrategyDesc: "Configurez comment l'assistant trouve et classe les informations.",
  retrievalVolumeAndRelevance: 'Volume de Récupération & Pertinence',
  precisionBoost: 'Boost de Précision',
  enableReranking: 'Boost de Précision (IA)',
  rerankerProvider: 'Fournisseur de Pertinence',
  topKRetrieval: 'Volume de récupération',
  topKRetrievalHint: 'Nombre de fragments de documents consultés.',
  topNRerank: 'Volume raffiné',
  topNRerankHint: 'Nombre de résultats très pertinents conservés.',
  similarityCutoff: 'Pertinence Minimale',
  similarityCutoffHint: 'Filtre les résultats non pertinents. Plus élevé = Plus strict.',
  configureDesc: 'Configurer les paramètres spécifiques pour votre source de données.',

  // Connector Drawer Tabs & Fields
  configuration: 'Configuration',
  indexation: 'Indexation',
  access: 'Accès',
  indexationSettings: "Paramètres d'indexation",
  folderConfiguration: 'Configuration du dossier',
  sharePointConfiguration: 'Configuration SharePoint',
  sqlConfiguration: 'Configuration SQL',
  fileConfiguration: 'Configuration de fichier',
  fileUploadOnlyHint:
    'Les connecteurs de fichiers sont en upload uniquement. Aucune configuration supplémentaire nécessaire.',
  cannotChangeAfterCreation: 'Ne peut pas être modifié après création',
  generalInformation: 'Informations générales',
  generalInfo: 'Informations générales',
  connectionDetails: 'Détails de la connexion',
  connectionSuccess: 'Connexion réussie',
  connectionFailed: 'Échec de la connexion',
  testConnectionRequired: 'Veuillez réussir le test de connexion avant de continuer',
  advancedSettings: 'Paramètres avancés',
  advancedIndexingSettings: "Paramètres d'indexation avancés",
  advancedIndexingDesc: 'Ajustez la manière dont vos documents sont découpés et traités.',
  chunkSize: 'Taille des morceaux (Caractères)',
  chunkSizeHint:
    'Définit la taille de chaque morceau. Des morceaux plus grands capturent plus de contexte mais peuvent perdre en précision. (Défaut : 1024)',
  chunkOverlap: 'Chevauchement (Caractères)',
  chunkOverlapHint:
    'Quantité de texte partagée entre des morceaux adjacents pour maintenir la continuité du contexte. (Défaut : 200)',

  back: 'Retour',
  next: 'Suivant',
  noDataSources: 'Aucune source de données connectée',
  noConnectorsFound: 'Aucune source de données trouvé',
  addFirstSource: 'Ajoutez votre première source de données pour commencer.',
  selectConnector: 'Sélectionnez une source de données ci-dessous pour commencer',
  selectConnectorType: 'Sélectionnez un type de source de données',
  searchConnectorType: 'Rechercher un type de source de données...',
  connect: 'Connecter',
  editConnector: 'Modifier la source de données {type}',
  addConnector: 'Ajouter la source de données {type}',
  testConnection: 'Tester la connexion',
  addFile: 'Ajouter un fichier',
  fileAlreadyExists: 'Ce fichier a déjà été ajouté à cette source de données.',
  connectorNameHint: 'Un nom unique pour identifier cette source de données',
  connectorDescriptionHint:
    'Une description pour aider les utilisateurs à identifier cette source de données',

  // Champs Connecteurs Spécifiques
  sharePoint: 'Microsoft SharePoint',
  sharePointDesc:
    "Synchronisez les documents et sites de l'entreprise. Idéal pour les politiques RH, les procédures internes et la documentation de projet.",
  sql: 'Base de données SQL',
  sqlDesc:
    "Connectez-vous aux bases de données Microsoft SQL Server, PostgreSQL ou MySQL. Connectez vos bases de données structurées. Permet à l'IA d'interroger vos données d'affaires comme l'inventaire, les ventes ou les fiches clients.",
  vannaSql: 'Vanna SQL (IA)',
  vannaSqlDesc:
    "Assistant SQL alimenté par l'IA (Vanna.ai). Génère et exécute automatiquement des requêtes SQL en langage naturel. Plus besoin de créer des vues - posez simplement vos questions et obtenez les données.",
  folder: 'Fichier local',
  folderDesc:
    "Importez manuellement des fichiers depuis votre poste. Parfait pour l'analyse rapide de contrats, de rapports ou de documents hors-ligne.",
  csvFile: 'Fichier CSV',
  csvFileDesc:
    "Importez manuellement des fichiers CSV depuis votre poste. Parfait pour l'analyse de données structurées.",
  networkDesc:
    'Connectez-vous à un dossier partagé, pour indexer les fichiers stockés sur vos serveurs locaux ou NAS. Idéal pour accéder aux archives historiques et aux lecteurs réseaux départementaux.',
  confluence: 'Confluence',
  confluenceDesc:
    "Synchronisez pages et blogs d'Atlassian Confluence. Parfait pour la documentation technique, les exigences de projet et les bases de connaissances d'équipe.",

  // Configuration Connecteur
  schedule: 'Planification',
  scheduleManual: 'Manuel',
  schedule5m: 'Toutes les 5 minutes',
  scheduleDaily: 'Quotidien',
  scheduleWeekly: 'Hebdomadaire',
  scheduleMonthly: 'Mensuel',
  filePath: 'Chemin du fichier',
  folderPath: 'Chemin du dossier',
  labelSiteUrl: 'URL du site',
  labelTenantId: 'ID du locataire',
  labelClientSecret: 'Secret client',
  labelHost: 'Hôte',
  labelHostSql: 'Hôte (Serveur SQL)',
  labelHostHint:
    'Nom DNS ou adresse IP du serveur SQL Server (ex: sql-prod-01.votre-domaine.com ou 192.168.1.100)',
  labelPort: 'Port',
  labelPortHint: 'Port de connexion SQL Server (par défaut: 1433)',
  labelDatabase: 'Nom de la base',
  labelDatabaseName: 'Nom de la base de données',
  labelDatabaseHint: 'Nom exact de la base de données à connecter (ex: VentesProd, InventaireDB)',
  labelSchema: 'Schéma SQL',
  labelSchemaHint: 'Nom du schéma contenant les vues à scanner (par défaut: vectra)',
  labelUser: 'Utilisateur',
  labelUserSql: 'Utilisateur SQL',
  labelUserHint:
    "Nom d'utilisateur SQL Server avec privilèges de lecture (db_datareader). Évitez les comptes administrateurs.",
  labelPassword: 'Mot de passe',
  labelPasswordHint:
    'Mot de passe du compte SQL Server. Les informations sont chiffrées et stockées de manière sécurisée.',
  recursive: 'Scan récursif',
  filePattern: 'Motif de fichier (ex. *.pdf)',
  fieldRequired: 'Champ requis',
  connectorAcl: "Étiquettes de contrôle d'accès",
  connectorAclHint:
    "Étiquettes de contrôle d'accès qui déterminent quels assistants ont accès aux documents de cette source de données",
  documentAcl: "Étiquettes de contrôle d'accès",
  documentAclHint:
    "Étiquettes de contrôle d'accès qui déterminent quels assistants ont accès à ce document spécifique",
  aclTagRequired: "Au moins une étiquette de contrôle d'accès est requise",
  csvIdColumnMissing: "Le fichier CSV doit contenir une colonne 'id'.",
  csvIdColumnNotUnique: "La colonne 'id' du fichier CSV doit contenir des valeurs uniques.",
  csvValidationGenericError: 'Une erreur est survenue lors de la validation du fichier CSV.',
  file_not_found: 'Le fichier est introuvable.',
  validationError: 'Erreur de validation',

  // Vanna SQL Specific
  aiTraining: 'Entraînement IA',
  databaseSchema: 'Schéma de base de données (DDL)',
  vannaDdlHint:
    'Collez vos instructions CREATE TABLE pour entraîner Vanna sur votre structure de base de données',
  vannaDdlExample:
    'Ex: CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255), email VARCHAR(255));',
  trainAI: "Entraîner l'IA",
  lastTrained: 'Dernier entraînement',
  trainingSuccess: 'Entraînement réussi',
  trainingFailed: "Échec de l'entraînement",
  saveConnectorFirst: "Veuillez enregistrer le connecteur avant l'entraînement",

  // --- New Stepper Steps ---
  accessControl: "Contrôle d'accès",
  aclPublic: 'Organisation entière',
  aclPublicDesc: 'Tous les assistants peuvent accéder à ces documents.',
  aclRestricted: 'Restreint',
  aclRestrictedDesc:
    "Seuls les assistants avec des étiquettes de contrôle d'accès spécifiques peuvent accéder à ces documents.",
  defineAccessTags: "Définir les étiquettes de contrôle d'accès",

  syncSchedule: 'Planification de la synchronisation',
  syncScheduleDesc: 'À quelle fréquence devons-nous vérifier le nouveau contenu ?',
  scheduleManualDesc: 'Lancer la synchro manuellement au besoin.',
  scheduleDailyDesc: 'Synchro tous les jours à minuit.',
  scheduleWeeklyDesc: 'Synchro tous les dimanches à minuit.',
  scheduleMonthlyDesc: 'Synchro le 1er de chaque mois.',
  manualOnlyForLocalFiles:
    'Seule la synchronisation manuelle est disponible pour les fichiers locaux.',

  // FolderPicker / FolderInput
  browseFolder: 'Parcourir le dossier',
  manualInputRequired: 'Saisie manuelle requise (Mode Web)',
  manualInputRequiredTitle: 'Saisie manuelle requise',
  manualInputWebMode: 'Saisie manuelle requise en mode Web',
  manualInputPastePath: 'Saisie manuelle requise en mode Web. Veuillez coller le chemin.',

  // Actions & Statut Connecteur
  syncNow: 'Vectoriser maintenant',
  forceSync: 'Forcer la re-vectorisation',
  stopSync: 'Arrêter la vectorisation',
  enableToSync: 'Activez la source de données pour vectoriser.',
  scheduledSyncOnly: 'Vectorisation manuelle désactivée car une planification est active.',
  confirmDeletion: 'Confirmer la suppression',
  confirmDeletionMessage:
    'Êtes-vous sûr de vouloir supprimer "{name}" ? Cette action est irréversible.',
  confirm: 'Confirmer',
  confirmPathChange: 'Confirmer le changement de répertoire',
  confirmPathChangeMessage:
    "Changer le répertoire du dossier supprimera effectivement tous les fichiers existants et leurs vecteurs de cette source de données, car ils n'existeront pas dans le nouveau chemin. Êtes-vous sûr de vouloir continuer ? Envisagez plutôt de créer une nouvelle source de données.",
  confirmRecursiveDisable: 'Confirmer la désactivation récursive',
  confirmRecursiveDisableMessage:
    'Désactiver le scan récursif entraînera la suppression de tous les fichiers (et de leurs vecteurs) situés dans les sous-dossiers. Êtes-vous sûr ?',
  sourceToggled: '{name} {status}',
  syncStarted: 'Vectorisation démarrée pour {name}',
  forceSyncStarted: 'Vectorisation forcée démarrée',
  syncStopped: 'Vectorisation arrêtée pour {name}',
  connectorUpdated: '{name} mis à jour',
  connectorCreated: '{name} créé',
  connectorDeleted: '{name} supprimé',
  failedToLoad: 'Échec du chargement des sources de données',
  failedToSave: "Échec de l'enregistrement de la source de données",
  failedToDelete: 'Échec de la suppression de la source de données',
  failedToStopSync: "Échec de l'arrêt de la vectorisation",
  stop: 'Arrêter',
  stopRequested: 'Arrêt demandé pour {name}',
  failedToStop: "Échec de l'arrêt du document",
  failedToStartSync: 'Échec du démarrage de la vectorisation',
  refreshFiles: 'Rafraîchir les objets',
  scanStarted: 'Scan des fichiers démarré pour {name}',
  failedToScan: 'Échec du lancement du scan',
  FILE_ALREADY_EXISTS: 'Le fichier existe déjà dans cette source de données',

  // Enums Statut Connecteur
  enabled: 'Activé',
  disabled: 'Désactivé',
  idle: 'En attente',
  vectorizing: 'Vectorisation',
  processing: 'Traitement en cours...',
  error: 'Erreur',
  paused: 'En pause',
  queued: 'En file',
  neverSynced: 'Jamais vectorisé',
  starting: 'Démarrage',
  syncing: 'Vectorisation',
  created: 'Créé',
  dismiss: 'Ignorer',
  unknownSource: 'Source inconnue',

  // --- Documents ---
  manageDocuments: 'Gérer les documents',
  loading: 'Chargement...',
  documents: 'Documents',
  viewDocuments: 'Voir les documents',
  searchFile: 'Rechercher un fichier...',
  filename: 'Nom de fichier',
  tokens: 'Jetons',
  vectors: 'Vecteurs',
  contentUnavailable: 'Contenu indisponible.',
  viewOriginal: 'Voir le document original',
  selectFile: 'Sélectionner un fichier',
  unknownDocument: 'Données structurées',
  noDocumentsFound: 'Aucun document trouvé',
  noDocumentsDesc: "Cette source n'a pas encore de documents.",
  documentDeleted: 'Document supprimé avec succès',
  documentAdded: 'Document ajouté avec succès',
  uploadingFile: 'Téléchargement du fichier...',
  failedToUploadFile: 'Échec du téléchargement du fichier',

  // --- Avatar ---
  avatarImage: 'Image de profil',
  avatarVerticalPosition: "Position verticale de l'image",
  saveToUploadAvatar: "Veuillez enregistrer l'assistant pour uploader une image",
  removeAvatar: "Supprimer l'image",
  uploadAvatar: 'Uploader une image',
  previewMessage: 'Bonjour ! Voici à quoi je ressemblerai.',
  documentUpdated: 'Document mis à jour avec succès',
  editFile: 'Modifier le fichier',
  uploadPhoto: 'Téléverser une photo',
  uploadAvatarHint: 'Téléverser une image',
  botDefaultName: 'Bot',
  library: 'Bibliothèque',
  viewAll: 'Voir tout',
  presetLibrary: 'Bibliothèque de préréglages',
  avatarUploaded: 'Avatar téléversé avec succès',
  avatarUploadFailed: "Échec du téléversement de l'avatar",
  avatarRemoved: 'Avatar supprimé',
  avatarRemoveFailed: "Échec de la suppression de l'avatar",

  // --- Assistants ---
  myAssistantsDesc: 'Gérez et discutez avec vos assistants IA',
  createNew: 'Créer un nouveau',
  noAssistants: 'Aucun assistant pour le moment',
  noAssistantsAvailable: 'Aucun assistant disponible',
  createYourFirstAssistant: 'Créez votre premier assistant',
  editAssistant: "Modifier l'assistant",
  newAssistant: 'Nouvel assistant',
  saveAssistant: 'Enregistrer',
  assistantUpdated: 'Assistant mis à jour avec succès',
  assistantCreated: 'Assistant créé avec succès',
  assistantDeleted: 'Assistant supprimé',
  failedToSaveAssistant: "Échec de l'enregistrement de l'assistant",
  failedToDeleteAssistant: "Échec de la suppression de l'assistant",

  // Formulaire Assistant
  identity: 'Identité',
  appearance: 'Apparence',
  background: 'Arrière-plan',
  backgroundColor: 'Couleur de fond',
  text: 'Texte',
  textColor: 'Couleur du texte',
  preview: 'Aperçu',
  presets: 'Préréglages',
  chooseColor: 'Choisir une couleur',
  intelligence: 'Intelligence',
  model: 'Modèle',
  nameRequired: 'Le nom est requis',
  systemInstructions: 'Instructions système',
  instructionsHint: "Décrivez comment l'assistant doit se comporter",
  instructionsRequired: 'Les instructions sont requises',
  dataSources: 'Sources de données',
  selectDataSources: 'Sélectionner des sources de données',
  filteringId: "Étiquette de contrôle d'accès",
  filteringIdHint: "ID pour le contrôle d'accès (ex: TenantID, GroupID, etc.)",
  filteringTagRequired: 'Au moins une étiquette est requise (ex: "public")',
  accessControlList: "Liste de contrôle d'accès",
  accessControlDesc: 'basées sur les sources de données sélectionnées ci-dessus.',
  selectAclTags: 'Sélectionner des étiquettes ACL',
  security: 'Sécurité',
  userAuthentication: 'Authentification utilisateur',
  userAuthenticationHint: "Forcer l'authentification utilisateur pour cet assistant.",

  // --- Paramètres LLM Avancés ---
  advancedLlmParameters: 'Paramètres LLM Avancés',
  advancedLlmParametersDesc: 'Ajustez le comportement du modèle avec des paramètres techniques.',
  configureAdvancedParams: 'Paramètres',
  assistantTemperature: 'Créativité (Temperature)',
  temperatureHint: '0.0 = Factuel et précis (Idéal pour RAG). 1.0 = Créatif et imprévisible.',
  topP: 'Top P (Diversité)',
  topPHint: 'Contrôle la diversité. Bas (0.1) = concentré, Haut (0.9) = créatif. (Défaut : 1.0)',
  maxOutputTokens: 'Longueur maximale (Max Output Tokens)',
  maxOutputTokensHint:
    'Limite la longueur de la réponse. ex: 1024 pour résumés, 8192 pour rapports.',
  frequencyPenalty: 'Répétition des mots (Frequency Penalty)',
  frequencyPenaltyHint:
    "Empêche l'IA d'utiliser trop souvent les mêmes mots. Augmentez si le texte semble robotique. (Défaut : 0.0)",
  presencePenalty: 'Diversité des sujets (Presence Penalty)',
  presencePenaltyHint:
    "Force l'IA à aborder de nouveaux points. Augmentez si l'IA tourne en rond. (Défaut : 0.0)",

  // --- Parameter Explanations ---
  tempTitle: '🌡️ La Température (T)',
  tempSubtitle: 'Le curseur de créativité',
  tempDesc:
    'La température contrôle le degré de hasard dans le choix des mots. Elle modifie la distribution de probabilité des tokens suivants.',
  tempExpert:
    "Basse (0.1 - 0.3) : \"L'Expert Rigide\". L'IA choisit presque toujours le mot le plus probable. C'est idéal pour la génération SQL ou l'extraction précise. C'est factuel et reproductible.",
  tempCollaborator:
    'Moyenne (0.7 - par défaut) : "Le Collaborateur". Un bon équilibre pour une discussion fluide sans trop s\'égarer.',
  tempPoet:
    'Haute (1.0 - 1.5) : "Le Poète Halluciné". L\'IA prend des risques, utilise des mots rares. Très bon pour le brainstorming, mais risqué pour le RAG.',
  topKTitle: '🎯 Le Top K',
  topKSubtitle: 'Le filtre de diversité',
  topKDesc: 'Le Top K limite le "vocabulaire" disponible pour chaque mot généré.',
  topKSmall:
    "Petit K (ex: 10) : L'IA est très focalisée. Elle ne dira jamais rien de bizarre, mais ses phrases peuvent sembler répétitives.",
  topKLarge:
    'Grand K (ex: 100+) : L\'IA a accès à un vocabulaire beaucoup plus riche. Plus naturel, mais plus de chances de "halluciner" si la température est haute.',

  // Optimisation
  instructionsOptimized: 'Instructions optimisées !',
  failedToOptimize: "Échec de l'optimisation",
  optimizeWithAi: "Optimiser avec l'IA",

  // --- Discussion & Interaction ---
  welcomeMessage: 'Bonjour ! Je suis {name}.',
  howCanIHelp: "Comment puis-je vous aider aujourd'hui?",
  typeMessage: 'Écrivez votre message...',
  newConversation: 'Nouvelle conversation',
  conversationReset: 'Conversation réinitialisée.',
  initializing: "Connexion à l'IA...",
  communicationError: "Une erreur est survenue lors de la communication avec l'assistant.",
  share: 'Partager le lien',
  linkCopied: 'Lien copié dans le presse-papier',
  talk: 'Parler',
  usedSources: 'Sources Utilisées',
  noSourcesUsed: 'Aucune source utilisée',
  sourcesLabel: 'Sources',
  assistantNotFound: 'Assistant introuvable ou indisponible.',
  invalidAssistantId: "ID d'assistant invalide",

  // --- Notifications ---
  notifications: 'Notifications',
  noNotifications: 'Aucune notification',
  dismissAll: 'Tout supprimer',
  readAll: 'Tout marquer comme lu',
  clearAll: 'Tout effacer',
  debug: 'Débogage',

  // --- Dialogues ---
  unsavedChanges: 'Modifications non enregistrées',
  unsavedChangesMessage:
    'Vous avez des modifications non enregistrées. Êtes-vous sûr de vouloir fermer ?',
  discard: 'Ignorer',
  keepEditing: 'Continuer à modifier',
  ingestionFailedForDoc: 'Traitement échoué pour {name}',
  unknownError: 'Erreur inconnue',

  // --- Erreurs ---
  pageNotFound: '404',
  oopsNothingHere: 'Oups. Rien ici...',
  goHome: "Retour à l'accueil",
  errors: {
    internal_error: 'Une erreur interne est survenue.',
    INVALID_CREDENTIALS:
      "Identifiants invalides. Veuillez vérifier votre nom d'utilisateur et mot de passe.",
    technical_error: 'Une erreur technique est survenue.',
    entity_not_found: 'Ressource introuvable.',
    duplicate_resource: 'Cette ressource existe déjà.',
    invalid_state: "Opération invalide pour l'état actuel.",
    forbidden: "Vous n'avez pas la permission d'effectuer cette action",
    unauthorized_action: "Vous n'êtes pas autorisé à effectuer cette action.",
    external_dependency_error: 'Service externe indisponible.',
    internal_data_corruption: "Erreur d'intégrité des données.",
    filesystem_error: "Échec de l'opération sur le système de fichiers.",
    invalid_csv_format: 'Format CSV invalide.',
    file_parsing_error: "Échec de l'analyse du fichier.",
    unsupported_format: 'Format de fichier non supporté.',
    doc_too_large: 'Le document est trop volumineux (max 10Mo).',
    csv_id_column_missing: "Le fichier CSV doit contenir une colonne 'id'.",
    csv_id_column_not_unique: "La colonne 'id' du fichier CSV doit contenir des valeurs uniques.",
    invalid_csv_data: 'Échec de la lecture des données CSV.',
    path_not_found: "Le chemin de dossier spécifié n'existe pas.",
  },
  model_desc: {
    // ── Gemini Chat ──
    'gemini-3-pro-preview':
      'Modèle de pointe ultra-intelligent (Preview). Excellence absolue en raisonnement, code et analyse de documents complexes.',
    'gemini-2.5-pro':
      "Modèle phare ultra-performant. Conçu pour le raisonnement de haut niveau et l'analyse documentaire approfondie.",
    'gemini-3-flash-preview':
      "L'efficacité de nouvelle génération (Preview). Réponses ultra-rapides avec l'intelligence de la classe GPT-4.",
    'gemini-2.5-flash':
      'Le modèle polyvalent par excellence. Rapide, fiable et performant pour la majorité des tâches de production.',
    'gemini-2.5-flash-lite':
      'Modèle 2.5 haute efficacité. Optimisé pour la vitesse et les volumes massifs à un coût extrêmement compétitif.',
    'gemini-2.0-flash':
      'Vitesse de pointe inégalée. Performances incroyables avec des réponses quasi instantanées.',
    'gemini-2.0-flash-lite':
      "Notre modèle le plus rentable à ce jour. Conçu pour une mise à l'échelle massive sans compromis sur la logique de base.",
    'gemini-embedding-001':
      'Modèle de vectorisation stable et compatible. Idéal pour des résultats cohérents sur toutes les régions Google Cloud.',

    // ── OpenAI Chat ──
    'gpt-5.2':
      'Le dernier sommet de l’intelligence artificielle. Son raisonnement semble plus "humain" et il peut gérer des instructions extrêmement complexes à travers de vastes volumes de texte.',
    'gpt-5.2-pro':
      'Le modèle "Expert". Si vous avez besoin d’un scientifique virtuel, d’un développeur senior ou d’un stratège approfondi, c’est le modèle le plus précis et le plus capable offert par OpenAI.',
    'gpt-5.1':
      'Un modèle phare hautement capable et fiable. Il offre une expérience premium avec une grande stabilité pour la rédaction professionnelle et créative.',
    'gpt-5':
      'La fondation de la nouvelle génération. Un modèle polyvalent très intelligent qui traite presque toutes les tâches avec une grande clarté et des formulations naturelles.',
    o1: 'Le "Penseur Profond". Contrairement aux autres modèles, il "réfléchit" avant de parler. Idéal pour la logique complexe, les problèmes mathématiques et le raisonnement scientifique où la précision est primordiale.',
    o3: 'La nouvelle génération de raisonnement. Plus rapide et encore plus logique que ses prédécesseurs, il est passé maître dans la résolution d’énigmes difficiles et de défis de programmation.',
    'o3-mini':
      'Une version plus rapide et compacte des modèles de raisonnement. Idéal lorsque vous avez besoin d’un traitement logique lourd mais souhaitez un temps de réponse plus court.',
    'o4-mini':
      'Le penseur logique le plus abordable. Il offre des capacités de raisonnement avancées à une fraction du coût des modèles plus grands.',
    'gpt-5-mini':
      'Intelligent, rapide et abordable. Le meilleur choix pour la plupart des utilisateurs qui souhaitent la puissance de la dernière génération pour les tâches quotidiennes sans le coût élevé.',
    'gpt-4.1-mini':
      'Un modèle fiable et très rapide largement utilisé en production. Il est idéal pour créer des applications nécessitant des réponses rapides et intelligentes.',
    'gpt-4o-mini':
      'Un modèle classique et rentable. Très rapide, il fonctionne bien pour les interactions simples et le traitement de données de base.',
    'gpt-5-nano':
      'La version ultra-légère. Presque instantanée et extrêmement bon marché. Idéal pour les tâches très simples ou le traitement à haut volume de données basiques.',

    // ── Mistral Chat ──
    'mistral-large-latest':
      'Le poids lourd de Mistral. Conçu pour rivaliser avec les modèles les plus intelligents au monde, il excelle dans le raisonnement complexe et le code de haute précision.',
    'mistral-medium-latest':
      'Le modèle "juste milieu" : assez intelligent pour le travail complexe mais optimisé pour la vitesse et le coût. Idéal pour les applications professionnelles.',
    'mistral-small-latest':
      'Efficace et concentré. Il possède une grande mémoire pour sa taille, ce qui le rend idéal pour les tâches routinières impliquant la lecture de plusieurs documents à la fois.',
    'open-mistral-nemo':
      'Un modèle spécialisé développé avec NVIDIA. Impressionnant de par son intelligence pour sa taille, il fonctionne particulièrement bien pour les cas d’usage techniques.',
    'mistral-tiny':
      'Le modèle Mistral le plus basique. Idéal pour les tâches rapides et simples comme l’identification de mots-clés ou le classement de texte basique.',
    'ministral-3b-latest':
      'Un modèle minuscule conçu pour fonctionner sur de petits appareils. Très rapide et concentré sur des instructions simples et directes.',
    'ministral-8b-latest':
      'Un petit modèle équilibré. Offre un raisonnement étonnamment bon pour sa taille compacte, parfait pour un traitement local efficace.',
    'ministral-14b-latest':
      'Le plus grand des petits modèles. Capable de gérer une logique plus complexe que les versions 3b ou 8b tout en restant très rapide.',
    'codestral-latest':
      'Le "Spécialiste du Code". Spécifiquement entraîné pour écrire et déboguer du code dans plus de 80 langages de programmation.',
    'pixtral-large-latest':
      'Un expert multimodal. Il peut non seulement lire du texte, mais aussi "voir" et analyser des images complexes, des graphiques et des diagrammes techniques avec une haute précision.',
    'pixtral-12b-2409':
      'Un modèle polyvalent capable de gérer efficacement le texte et les images. Idéal pour les tâches de vision générale comme la description de photos.',
    'voxtral-latest':
      'L’"Expert Audio". Spécialisé dans la compréhension et le traitement direct du langage parlé et des fichiers audio.',
    'devstral-latest':
      'Un outil expérimental conçu spécifiquement pour les développeurs. Optimisé pour agir comme assistant dans les tâches d’ingénierie logicielle.',
    'open-mistral-7b':
      'Un modèle classique et fiable qui a tout déclenché. Rapide et efficace pour les conversations simples et directes.',

    // ── Anthropic Chat ──
    'claude-3-opus-latest':
      "Notre modèle le plus puissant, conçu pour exceller dans tâches hautement complexes. Idéal pour quand vous avez besoin d'une intelligence maximale.",
    'claude-3-7-sonnet-latest':
      "L'équilibre parfait entre intelligence et rapidité. Excellent pour la majorité des tâches nécessitant un bon raisonnement.",
    'claude-3-5-haiku-latest':
      'Notre modèle le plus rapide et le plus compact. Parfait pour une exécution quasi instantanée de tâches simples.',

    // ── Ollama Chat ──
    mistral:
      'Un modèle local puissant qui fonctionne entièrement sur votre propre ordinateur. Très efficace, bon en logique et offrant un excellent support de la langue française.',

    // ── Embedding (Recherche & Organisation) ──
    'models/text-embedding-004':
      'Le standard actuel pour la recherche. Il convertit le texte en un format mathématique permettant au système de trouver des documents selon leur "sens" plutôt que de simples mots-clés.',
    'models/text-embedding-005':
      'Le modèle de recherche de nouvelle génération. Plus rapide et efficace pour organiser de grandes quantités de données pour une récupération ultra-précise.',
    'text-embedding-3-small':
      'Le modèle de recherche hautement efficace d’OpenAI. Offre d’excellentes performances pour la recherche documentaire générale.',
    'text-embedding-3-large':
      'Le modèle de recherche le plus puissant d’OpenAI. Capture les nuances les plus subtiles du texte, idéal pour les recherches de haute précision.',
    'bge-m3':
      'Le modèle de recherche multilingue par excellence. Permet de trouver des documents dans plus de 100 langues différentes avec une grande précision.',
    'nomic-embed-text':
      'Un modèle de recherche open-source haute performance. Dispose d’une mémoire massive pour lire de très longs documents pendant le processus de recherche.',

    // ── Rerank (Affinage des Résultats) ──
    'BAAI/bge-reranker-base':
      'Un "vérificateur de qualité" local. Il reprend vos résultats de recherche et les réanalyse pour garantir que les plus pertinents sont tout en haut. Fonctionne de manière privée sur votre machine.',
    'BAAI/bge-reranker-v2-m3':
      'Vérificateur de qualité local de dernière génération. Plus précis et multilingue, il garantit que vos résultats de recherche sont toujours pertinents.',
    'rerank-v3.5':
      'La référence absolue pour affiner les recherches. Incroyablement doué pour comprendre l’intention de votre question afin de choisir le document parfait dans une liste.',
    'rerank-multilingual-v3.0':
      'Optimisé pour l’international. Affine les résultats de recherche dans des dizaines de langues pour garantir la précision, quelle que soit la langue du document.',
    'rerank-english-v3.0':
      'Un vérificateur de qualité spécialisé pour l’anglais. Très rapide et précis pour le contenu exclusivement en anglais.',

    // ── Transcription (Parole vers Texte) ──
    'whisper-1':
      'Le leader du secteur pour convertir la parole en texte. Extrêmement précis pour transcrire des fichiers audio en documents écrits.',
    whisper:
      'Une version locale et fiable de la reconnaissance vocale. Permet de transcrire vos audios en toute confidentialité sur votre propre ordinateur sans envoyer de données sur internet.',
  },
  model_desc_transcription: {
    'gemini-1.5-flash':
      'Le champion de la rapidité. Idéal pour convertir rapidement de grandes quantités d’audio en texte à moindre coût.',
    'gemini-1.5-pro':
      'Le choix de la précision. Capable de transcrire fidèlement des enregistrements complexes, longs ou avec plusieurs interlocuteurs.',
    'whisper-1':
      'Spécialiste mondial de la voix. Reconnaît la parole avec une précision incroyable, même avec des accents marqués ou du bruit de fond.',
    whisper:
      'Transcription privée et locale. Transcrit vos fichiers directement sur votre ordinateur sans jamais envoyer vos données dans le cloud.',
  },
  model_desc_extraction: {
    'gemini-1.5-flash':
      'Rapide et précis pour extraire des informations clés de documents simples.',
    'gemini-2.0-flash':
      'Optimisé pour l’extraction de données complexes avec un excellent rapport vitesse/précision.',
    'gpt-4o-mini':
      'Modèle compact très performant pour comprendre la structure des données et isoler les points importants.',
    mistral: 'Modèle local efficace pour analyser vos documents en toute confidentialité.',
  },
  // --- Assistant Wizard ---
  wizard: {
    step1Title: 'Identité & Rôle',
    step1Caption: "L'Architecte",
    step1Heading: "Définition de l'identité",
    nameLabel: 'Nom',
    nameHint: 'Donnez un nom unique à votre assistant (ex: Assistant Marketing)',
    nameRequired: 'Le nom est requis',
    targetLabel: 'Cible',
    targetHint: "À qui s'adresse cet assistant ? (ex: Équipe de création de contenu)",
    roleLabel: 'Rôle / Persona',
    roleHint:
      "Décrivez son rôle et son expertise (ex: Rédacteur senior avec 10 ans d'expérience...)",

    step2Title: 'La Mission',
    step2Caption: 'Le Cerveau',
    step2Heading: 'Objectifs et Comportement',
    objectiveLabel: 'Objectif Principal',
    objectiveHint: 'Quel est le but premier du bot ? Que doit-il accomplir ?',
    objectiveRequired: "L'objectif est requis",
    ragBehaviorLabel: 'Comportement RAG',
    ragStrict: 'Strict (Je ne sais pas)',
    ragFlexible: 'Souple (Déduction)',

    step3Title: 'Ton & Style',
    step3Caption: 'La Voix',
    step3Heading: 'Personnalité et Format',
    toneLabel: 'Tonalité',
    toneHint: 'Quel ton doit-il employer ?',
    languageLabel: 'Langue',
    languageHint: 'Langue de réponse principale',
    formatLabel: 'Format de réponse',
    formatHint: 'Instructions de formatage (ex: Listes à puces, prix en gras, concis...)',

    step4Title: 'Garde-fous',
    step4Caption: 'La Sécurité',
    step4Heading: 'Sécurité et Restrictions',
    taboosLabel: 'Sujets Tabous',
    taboosHint:
      'Tapez et appuyez sur Entrée pour ajouter des sujets interdits (ex: Politique, Religion)',
    securityRulesLabel: 'Règles de Sécurité',
    securityRulesHint: 'Règles strictes à respecter (ex: Ne jamais inventer un numéro de pièce)',

    btnNext: 'Suivant',
    btnPrev: 'Précédent',
    btnGenerate: 'Générer',
    stepPerformanceTitle: 'Performance',
    stepPerformanceHeading: 'Performance & Caching',
    stepPerformanceCaption: 'Optimiser la vitesse et les coûts',
  },

  performance: {
    enableCache: 'Activer le Cache Sémantique',
    similarityThreshold: 'Seuil de Similarité',
    cacheTTL: 'Durée du cache (secondes)',
    thresholdHelp:
      'Plus le score est élevé, plus la question doit être identique pour utiliser le cache.',
    ttlHelp: 'Durée pendant laquelle une réponse reste valide en cache.',
    cacheHelpResult:
      'Si activé, les questions similaires recevront instantanément la réponse précédente sans interroger le LLM.',
    timeUnits: {
      seconds: 's',
      minutes: 'min',
      hours: 'h',
      days: 'j',
    },
    dangerZone: 'Zone de Danger',
    purgeCache: 'Purger le Cache',
    purgeCacheHelp:
      "Force la suppression de toutes les réponses en cache pour cet assistant. À utiliser si l'IA fournit des infos obsolètes.",
    purgeConfirmTitle: 'Confirmer la Purge',
    purgeConfirmMessage:
      "Êtes-vous sûr ? Cela obligera l'assistant à régénérer toutes les réponses futures.",
    purgeSuccess: 'Cache purgé avec succès',
    purgeFailed: "Échec de la purge du cache de l'assistant",
  },

  // --- Common ---
  assistantWizard: 'Assistant de création',
  generateWithWizard: 'Générer avec le Wizard',
  stepGeneral: 'Infos Générales',
  stepPersonality: 'Personnalité',
  stepKnowledge: 'Base de Connaissances',
  stepGeneralDesc: "Configurer l'identité",
  stepIntelligenceDesc: 'Choisir le modèle',
  stepPersonalityDesc: 'Définir le comportement',
  stepKnowledgeDesc: 'Lier les sources de données',
  linkConnectorsDesc: 'Sélectionnez quelles bases de connaissances cet assistant peut consulter.',
  systemInstructionsHint: "Définissez comment l'assistant se comporte et répond.",
  createNewAssistant: 'Créer un nouvel Assistant',
  createAssistant: "Créer l'Assistant",
  defaultSystemInstructions: 'Vous êtes un assistant utile.',
  pipelineSteps: {
    title: 'Étapes du Pipeline',
    connection: 'Initialisation de la session',
    cache_lookup: 'Vérification Cache',
    cache_hit: 'Réponse trouvée en cache',
    cache_miss: 'Recherche documentaire nécessaire',
    history_loading: 'Chargement de l’historique',
    vectorization: 'Vectorisation',
    retrieval: 'Recherche Documents',
    reranking: 'Ré-ordonnancement',
    synthesis: 'Rédaction de la réponse',
    assistant_persistence: 'Sauvegarde du message',
    cache_update: 'Mise à jour du cache',
    user_persistence: 'Enregistrement question',
    trending: 'Analytique',
    completed: 'Terminé',
    failed: 'Échoué',
    initialization: 'Initialisation du chat',
    visualization_analysis: 'Analyse Visuelle',
    ambiguity_guard: 'Garde-fou Contextuel',
    csv_schema_retrieval: 'Récupération Données',
    csv_synthesis: 'Génération de Fiches',
    facet_query: 'Analyse des Filtres',
    router: 'Routeur Intelligent',
    router_processing: 'Préparation Contexte',
    router_reasoning: 'Analyse Stratégique',
    router_retrieval: 'Recherche Documents',
    router_selection: 'Choix de l’Outil',
    query_rewrite: 'Optimisation Requête',
    sql_generation: 'Génération SQL',
    sql_schema_retrieval: 'Lecture Structure SQL',
    tool_execution: 'Exécution Outil',
    query_execution: 'Exécution Requête',
    router_synthesis: 'Synthèse Réponse',
    streaming: 'Finalisation',
  },
  stepDescriptions: {
    connection:
      "Établissement d'une connexion sécurisée avec les fournisseurs d'IA et les bases de données. Cette étape initiale garantit que l'environnement est prêt pour le traitement.",
    query_rewrite:
      'Reformulation de votre question pour améliorer les résultats de recherche en ajoutant le contexte manquant de la conversation. Cette étape rend la requête plus claire pour les moteurs de recherche IA.',
    cache_hit:
      "La réponse exacte a été trouvée dans le cache sémantique, économisant temps et coûts. La réponse est instantanément restaurée sans nécessiter une nouvelle génération par l'IA.",
    cache_miss:
      "La réponse de référence n'a pas été trouvée dans le cache sémantique. Le système procède à une analyse complète et à la récupération des données pour construire une nouvelle réponse.",
    router_processing:
      'Préparation du contexte de la conversation et initialisation des outils IA spécialisés. Cette configuration garantit que le modèle le plus approprié est sélectionné pour votre requête.',
    router_reasoning:
      "L'IA analyse votre demande pour déterminer la meilleure approche. Elle évalue si elle doit rechercher des documents, interroger une base de données ou effectuer une tâche directe.",
    router_selection:
      'Le routeur intelligent évalue si votre question nécessite une recherche documentaire (vectorielle) ou une requête de base de données précise (SQL). Ce choix garantit la plus haute précision pour la réponse finale.',
    sql_generation:
      'Traduction de votre question en langage naturel en une requête SQL sécurisée et optimisée. Cette commande sera exécutée directement sur la base de données connectée pour extraire des chiffres exacts.',
    sql_schema_retrieval:
      "Lecture de la structure de votre base de données SQL (tables, colonnes et relations). Cette étape est cruciale pour permettre à l'IA de générer des requêtes précises.",
    tool_execution:
      "Orchestration et exécution de l'outil spécialisé sélectionné pour répondre à votre besoin spécifique. Cette étape fait le pont entre votre question et les sources de données.",
    query_execution:
      'Exécution de la requête générée sur la base de données ou le système de fichiers pour extraire des données précises.',
    router_retrieval:
      'Recherche dans la Base de Connaissances pour identifier les ressources pertinentes, comme des documents ou des vues SQL disponibles. Cette correspondance sémantique fournit le contexte exact pour la réponse.',
    router_synthesis:
      'Construction de la réponse finale en fusionnant les données récupérées avec les capacités linguistiques du modèle. Cela garantit une réponse naturelle, précise et tenant compte du contexte.',
    cache_lookup:
      'Consultation ultra-rapide de la mémoire à court terme pour voir si cette question exacte a déjà reçu une réponse récemment. Cette optimisation réduit considérablement le temps de réponse pour les questions courantes.',
    retrieval:
      'Un algorithme de recherche sémantique parcourt votre base de connaissances pour trouver les fragments de documents les plus pertinents. Cela identifie les informations clés nécessaires pour répondre.',
    reranking:
      'Un modèle spécialisé analyse les résultats pour ne conserver que les informations les plus pertinentes.',
    synthesis: "L'IA rédige une réponse claire en s'appuyant uniquement sur les documents trouvés.",
    assistant_persistence:
      "Archivage sécurisé de la réponse de l'assistant dans votre historique de conversation. Cette persistance vous permet de vous référer à cet échange lors de sessions futures.",
    trending:
      'Anonymisation et agrégation des métadonnées de cette question pour alimenter les tableaux de bord analytiques. Cela aide à identifier les sujets populaires et à détecter les tendances émergentes.',
    vectorization:
      "Conversion de votre texte en vecteurs mathématiques multidimensionnels. Cette représentation mathématique permet une comparaison sémantique avec l'ensemble de votre base de connaissances.",
    cache_update:
      'Mise à jour du cache sémantique avec la nouvelle réponse générée. Cette étape garantit que les futures demandes identiques pourront recevoir une réponse instantanée.',
    visualization_analysis:
      'Analyse intelligente du format de présentation optimal pour vos données. Le système choisit automatiquement entre des tableaux, des graphiques circulaires, des barres ou des courbes.',
    initialization:
      "Initialisation du contexte de conversation et chargement de la configuration de l'assistant. Cela vérifie la connectivité avec tous les fournisseurs d'IA et de bases de données nécessaires.",
    streaming:
      "Transmission de la réponse du modèle d'IA en temps réel. Cette étape suit la génération de chaque jeton pour fournir une transparence précise sur la vitesse et les coûts.",
    ambiguity_guard:
      "Analyse de la requête pour détecter les imprécisions et fusionner le contexte de la conversation. Cette étape garantit que l'IA comprend les références implicites et les filtres temporels complexes.",
    csv_schema_retrieval:
      'Interrogation ciblée des fichiers de données structurés en appliquant les critères extraits de votre question. Cette recherche localise précisément les entrées pertinentes dans vos catalogues CSV.',
    csv_synthesis:
      'Extraction et mise en forme des spécificités techniques à partir des données filtrées. Le système construit une fiche de synthèse claire, organisant les attributs clés pour une lecture facilitée.',
    facet_query:
      "Exploration dimensionnelle des attributs disponibles pour suggérer des options d'affinage à l'utilisateur. Cela transforme une recherche brute en une navigation guidée par catégories pertinentes.",
    router:
      "Le cerveau central décidant quelle voie emprunter (SQL, Vecteur ou Outils) en fonction de la demande de l'utilisateur. Ce routage garantit que l'outil le plus efficace traite votre question spécifique.",
    history_loading:
      "Récupération des messages précédents pour maintenir le contexte de la conversation. Cela permet à l'IA de se souvenir de ce dont vous avez discuté lors des tours précédents.",
    user_persistence:
      "Sauvegarde de votre question dans l'historique de la conversation pour maintenir le contexte pour les tours futurs. Cela assure la continuité de l'échange.",
    completed:
      'Traitement de la demande terminé avec succès. Tous les résultats ont été collectés et sont prêts à être consultés.',
  },
  conversationCleared: 'Conversation effacée',
  validate: {
    atLeastOneSource: 'Veuillez sélectionner au moins une base de connaissances.',
  },
};
