export default {
  // --- General ---
  cancel: 'Cancel',
  save: 'Save',
  delete: 'Delete',
  edit: 'Edit',
  add: 'Add',
  close: 'Close',
  search: 'Search',
  actions: 'Actions',
  status: 'Status',
  name: 'Name',
  firstName: 'First Name',
  lastName: 'Last Name',
  description: 'Description',
  date: 'Date',
  size: 'Size',
  fileSizeUnits: ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
  type: 'Type',
  acl: 'Access Control List',
  fileCount: 'Objects',
  unknown: 'Unknown',
  appDescription: 'RAG Management System',
  source: 'Source',
  lastVectorized: 'Last Vectorized',
  recordsPerPage: 'Records per page:',

  // --- Auth & Profile ---
  loginTitle: 'Vectra Admin',
  login: 'Login',
  logout: 'Logout',
  username: 'Username',
  password: 'Password',
  email: 'Email',
  signInToAccount: 'Sign in to your account',
  pleaseTypeUsername: 'Please type your username',
  pleaseTypeEmail: 'Please type your email',
  pleaseTypePassword: 'Please type your password',
  loginSuccessful: 'Login successful',
  loginFailed: 'Login failed. Please check your credentials.',
  adminLabel: 'ADMIN',
  heartbeatLabel: 'HEARTBEAT',
  roleAdmin: 'Admin',
  roleGuest: 'Guest',
  statusOnline: 'Online',
  statusOffline: 'Offline',
  statusStopped: 'Stopped',
  statusAnonymous: 'Anonymous',
  users: 'Users',
  addUser: 'Add User',
  editUser: 'Edit User',
  role: 'Role',
  statusInactive: 'Inactive',
  statusActive: 'Active',
  isActive: 'Is Active',
  newPasswordOptional: 'New Password (Optional)',
  confirmDeleteUser: 'Are you sure you want to delete user {email}?',
  userCreated: 'User created successfully',
  userUpdated: 'User updated successfully',
  userDeleted: 'User deleted successfully',
  failedToFetchUsers: 'Failed to fetch users',
  failedToCreateUser: 'Failed to create user',
  failedToUpdateUser: 'Failed to update user',
  failedToDeleteUser: 'Failed to delete user',
  invalidEmailArguments: 'Please enter a valid email address',
  emailAlreadyExists: 'This email is already used by another user',
  cannotDeactivateSelf: 'You cannot deactivate your own account',
  maxFileSize: 'Max size: {size}',
  removePhoto: 'Remove photo',
  dragToPosition: 'Drag to position',
  noUsersFound: 'No users found',
  addFirstUser: 'Add your first user to get started.',

  // --- Navigation & Menu ---
  menu: 'Menu',
  dashboard: 'Dashboard',
  analytics: 'Analytics',
  advancedAnalytics: 'Advanced Analytics',
  realTimeInsightsPerformance: 'Real-time insights and performance metrics',
  loadingAnalytics: 'Loading analytics',
  cacheHitRate: 'Cache Hit Rate',
  dailyLlmCost: 'Daily LLM Cost',
  topicDiversity: 'Topic Diversity',
  pipelineStepBreakdown: 'Pipeline Step Breakdown',
  trendingQuestions: 'Trending Questions',
  trendingQuestionsGlobal: 'Top Global Trends',
  costByAssistant: 'Cost by Assistant',
  knowledgeBaseFreshness: 'Knowledge Base Freshness',
  noCostData: 'No cost data',
  noDocuments: 'No documents',
  noTrendsYet: 'No trends yet',
  requests: 'requests',
  timeToFirstToken: 'Time to First Token (TTFT)',
  topics: 'topics',
  docs: 'docs',
  lastUpdate: 'Last update',
  noData: 'No data',
  myAssistants: 'My Assistants',
  knowledgeBase: 'Knowledge Base',
  settings: 'Settings',
  manageAppConfiguration: 'Manage application configuration',
  connectorTypeFolder: 'Local Folder',
  localProviderWarning:
    'Local vectorization runs on your CPU and is significantly slower than cloud providers. Please be patient.',
  generalInfo: 'General Information',
  connectionDetails: 'Connection Details',
  connectionSuccess: 'Connection successful',
  connectionFailed: 'Connection failed',
  testConnectionRequired: 'Please pass the connection test before proceeding',
  saveChanges: 'Save',
  general: 'General',
  aiEngine: 'AI Engine',
  embeddingEngine: 'Vectorization Engine',
  chatEngine: 'Chat Engine',
  system: 'System',
  interface: 'Interface',
  language: 'App Language',
  theme: 'Theme',
  restartRequiredInfo:
    'Changes to AI settings may require a restart or re-initialization of the worker.',
  embeddingWarning:
    'Changing embedding settings affects how documents are indexed. Existing vectors may need re-vectorization.',
  embeddingProvider: 'Embedding Provider',
  chatProvider: 'Chat Provider',
  apiKey: 'API Key',
  modelName: 'Vectorization Model',
  chatModel: 'Chat Model',
  parameters: 'Parameters',
  network: 'Network',
  networkName: 'Folder',
  settingsSaved: 'Settings saved successfully',
  noChanges: 'No changes to save',

  // Settings - AI & System
  geminiConfiguration: 'Gemini Configuration',
  openaiConfiguration: 'OpenAI Configuration',
  localConfiguration: 'Local Configuration',
  baseUrl: 'Base URL',
  baseUrlHint: 'e.g. http://localhost:11434',
  aiProvider: 'AI Provider',
  gemini: 'Google Gemini',
  geminiTagline: 'Best for Large Context',
  geminiDesc:
    'Excel at maintaining long conversations and analyzing multiple documents simultaneously thanks to its huge context window.',
  openai: 'OpenAI ChatGPT',
  openaiTagline: 'High Performance',
  openaiDesc:
    'Renowned for its logical reasoning and ability to follow complex instructions. Best for structured outputs and precise answers.',
  mistral: 'Mistral AI',
  mistralLocal: 'Mistral AI (Local via Ollama)',
  mistralLocalDesc:
    'Run advanced models locally on your machine via Ollama. Private and offline. Requires sufficient hardware resources.',
  ollamaConfiguration: 'Ollama Configuration',
  mistralConfiguration: 'Mistral Configuration',
  mistralDesc:
    'A powerful European LLM known for efficiency and open-weights performance. Balanced for reasoning and chat.',
  localEmbedding: 'BAAI (Local)',
  local: 'Local',
  localTagline: 'Private & Offline',
  localDesc:
    'Runs entirely on your machine. No data leaves your network. Requires powerful hardware.',
  recommended: 'Recommended',
  popular: 'Popular',
  public: 'Public', // Added
  private: 'Private',
  transcriptionModel: 'Audio Transcription Model',
  temperature: 'Temperature',
  topK: 'Top K',
  modelNameHint: 'e.g. models/text-embedding-004',
  chatModelHintGemini: 'e.g. gemini-1.5-flash, gemini-1.5-pro',
  chatModelHintOpenAI: 'e.g. gpt-4-turbo, gpt-4o',
  chatModelHint: 'Default model used for answering questions in chat',
  selectModel: 'Select a Model',
  searchModels: 'Search models...',
  inputPrice: 'Input',
  outputPrice: 'Output',
  perMillionTokens: 'per 1M tokens',
  noModelsFound: 'No models found',
  categoryFlagship: 'Flagship',
  categoryReasoning: 'Reasoning',
  categoryBalanced: 'Balanced',
  categoryEconomy: 'Economy',
  transcriptionModelHint: 'e.g. gemini-1.5-flash',
  httpProxy: 'HTTP Proxy',
  proxyHint: 'Leave empty if not used',
  themeAuto: 'Auto',
  themeDark: 'Dark',
  themeLight: 'Light',
  langEnglish: 'English',
  langFrench: 'Français',
  assistantNotVectorized: 'Assistant not vectorized. Chat is disabled.',
  vectorizeSourcesToEnableChat: 'Please vectorize the data sources to enable chat.',
  chatDisabledPlaceholder: 'Chat disabled - Assistant not vectorized',

  chat: 'Chat',
  systemOverview: 'System Overview & Real-time Metrics',
  selectAssistant: 'Select an Assistant',
  selectAssistantDesc: 'Choose an assistant to start chatting',
  startChatting: 'Start Chatting',
  noAssistantsForChat: 'No assistants available to chat with',
  createAssistantToChat: 'Create an assistant in the Assistants page to start chatting',
  connectedSources: 'Connected Sources',
  clickToChat: 'Click to start chatting',
  noDescription: 'No description',

  // --- Dashboard / Index ---
  backendApi: 'Backend API',
  application: 'Application',
  ingestionEngine: 'Ingestion Engine',
  worker: 'Vector Engine',
  statusActiveUpper: 'ACTIVE',
  statusStoppedUpper: 'STOPPED',
  statusOfflineUpper: 'OFFLINE',
  seenJustNow: 'Seen just now',
  noSignal: 'No signal',
  connected: 'Connected',
  storage: 'Storage',
  storageOfflineTitle: 'Storage Mount Broken',
  storageOfflineDesc:
    'Docker cannot access your data path. Please update VECTRA_DATA_PATH in your .env file (root folder) to a physical drive.',
  storageOnline: 'Storage Online',
  storageOffline: 'Storage Offline',
  storageFixTitle: 'How to Fix Storage',
  storageFixStep1: '1. Locate the .env file in the project root folder.',
  storageFixStep2: '2. Find the VECTRA_DATA_PATH variable.',
  storageFixStep3: '3. Change it to a physical path (e.g., C:/VectraData or /home/user/data).',
  storageFixStep4: '4. Restart the Docker containers.',
  storageFixPathLabel: 'Project Root Path:',
  cpuUsage: 'CPU Usage',
  memoryUsage: 'Memory Usage',
  totalQueries: 'Total Queries',
  processedSinceStartup: 'Processed since startup',
  systemLoadHistory: 'System Load History',
  kbSize: 'Knowledge Base Size',
  totalVectorsIndexed: 'Total Vectors Indexed',
  estMonthlyCost: 'Est. Monthly Cost',
  basedOnTokenUsage: 'Based on current token usage',
  estTimeSaved: 'Est. Time Saved',
  vsManualResearch: 'vs. Manual Research',
  live: 'LIVE',
  offline: 'OFFLINE',
  workerOnline: 'Worker Online',
  workerOffline: 'Worker Offline',
  cpuTotal: 'CPU Total',
  memoryTotal: 'Memory Total',

  // Dashboard - Pipeline Stats
  mainDashboard: 'Main Dashboard',
  loadingDashboard: 'Loading Dashboard',
  indexing: 'Indexing',
  usage30Days: 'Usage (30 Days)',
  activePipelines: 'Active Pipelines',
  totalConnectors: 'Total Connectors',
  systemStatus: 'System Status',
  healthy: 'Healthy',
  statusDegraded: 'Degraded',
  statusError: 'Error',
  latencyFast: 'Fast',
  latencyOk: 'OK',
  latencySlow: 'Slow',
  lastSync: 'Last Sync',
  never: 'Never',
  totalVectors: 'Total Vectors',
  totalTokens: 'Total Tokens',
  successRate: 'Success Rate',
  failedDocs: 'Failed Docs',
  sessions: 'Sessions',
  avgLatency: 'Avg. Latency (TTFT)',
  avgFeedback: 'Avg. Feedback',
  justNow: 'Just now',
  ago: 'ago',

  // --- Home ---
  sloganConnect: 'Connect.',
  sloganVectorize: 'Vectorize.',
  sloganChat: 'Chat.',
  actionConnect: 'Manage data sources',
  actionVectorize: 'Index & process knowledge base',
  actionChat: 'Interact with assistants',
  cardConnect: 'Connect',
  cardVectorize: 'Vectorize',
  cardChat: 'Chat',

  // --- Connectors (Knowledge Base) ---
  manageDataSources: 'Manage Data Sources',
  myDataSources: 'My Data Sources',
  availableConnectors: 'Available Data Sources',
  selectType: 'Select Type',
  stepIntelligence: 'Chat Engine',
  selectAIEngine: 'Select Answer Engine',
  configure: 'Configure',
  configureProvider: 'Configure provider settings',
  selectAIEngineDesc:
    'Choose the AI model that will formulate answers and reason about your data (not embedding).',
  selectConnectorTypeDesc: 'Choose the type of data source you want to connect.',
  searchConnectors: 'Search data sources...',
  clickToChange: 'Click to change',
  clickToBrowseConnectors: 'Click to browse data sources',
  tryAdjustingSearch: 'Try adjusting your search terms',
  sourcesSelected: 'data sources selected',
  noSourcesSelectedHint: 'No data sources selected',
  itemsSelected: 'selected',
  confirmSelection: 'Confirm Selection',
  performanceWarning: 'Performance Warning',
  mixedProvidersDesc:
    'You have selected data sources using different AI providers. This may trigger multiple concurrent API calls and reduce response speed.',

  // Vectorization Step
  selectVectorizationEngine: 'Vectorization Engine',
  selectVectorizationEngineDesc:
    'Choose the model that will convert your documents into mathematical vectors for search.',
  geminiEmbeddings: 'Gemini Embeddings',
  geminiEmbeddingsDesc: 'Model: text-embedding-004',
  modelLabel: 'Model', // Added
  openaiEmbeddings: 'OpenAI Embeddings',
  openaiEmbeddingsDesc: 'Model: text-embedding-3-small',
  localEmbeddings: 'Local Embeddings',
  localEmbeddingsDesc: 'Model: HuggingFace / Ollama',
  engineNotConfigured: 'Engine not configured (See Settings)',
  notConfigured: 'Not configured',
  rerankEngine: 'Rerank Engine',
  cohereRerankDesc: 'Recommended for highest precision.',
  localRerankDesc: 'Runs privately on your CPU using FastEmbed.',
  modelDeprecationWarning:
    'Warning: Cloud AI models may be deprecated over time. Ensure you select a stable model to avoid re-vectorization.',

  // --- Smart Extraction ---
  smartExtractionTitle: 'Intelligence & Context Extraction', // Added
  enableSmartExtraction: 'Enable Smart Metadata Extraction',
  aiContextEnhancement: 'AI-Powered Context Enhancement',
  smartExtractionIntro: 'For each document chunk, the AI will extract:',
  smartExtractionTitleLabel: 'Title',
  smartExtractionTitleDesc: 'Concise description',
  smartExtractionSummaryLabel: 'Summary',
  smartExtractionSummaryDesc: 'One-sentence essence',
  smartExtractionQuestionsLabel: 'Questions',
  smartExtractionQuestionsDesc: '3 strategic questions the text answers',
  smartExtractionTradeoff: 'Trade-off',
  smartExtractionTradeoffDesc:
    'Ingestion will be slower (~2-3s per chunk), but retrieval accuracy improves significantly.',

  // --- Retrieval Strategy ---
  retrievalStrategy: 'Retrieval Strategy',
  retrievalStrategyDesc: 'Configure how the assistant finds and ranks information.',
  enableReranking: 'Precision Boost (AI)',
  rerankerProvider: 'Reranker Provider',
  topKRetrieval: 'Retrieval Volume',
  topKRetrievalHint: 'Number of document fragments consulted.',
  topNRerank: 'Refined Volume',
  topNRerankHint: 'Number of highly relevant results kept.',
  similarityCutoff: 'Minimum Relevance',
  similarityCutoffHint: 'Filters out irrelevant results. Higher = Stricter.',
  configureDesc: 'Configure the specific settings for your data source.',
  retrievalVolumeAndRelevance: 'Retrieval Volume and Minimum Relevance',
  precisionBoost: 'Precision Boost',

  // Connector Drawer Tabs & Fields
  configuration: 'Configuration',
  indexation: 'Indexation',
  access: 'Access',
  indexationSettings: 'Indexation Settings',
  folderConfiguration: 'Folder Configuration',
  sharePointConfiguration: 'SharePoint Configuration',
  sqlConfiguration: 'SQL Configuration',
  fileConfiguration: 'File Configuration',
  fileUploadOnlyHint: 'File connectors are upload-only. No additional configuration needed.',
  cannotChangeAfterCreation: 'Cannot be changed after creation',
  generalInformation: 'General Information',
  advancedSettings: 'Advanced Settings',
  advancedIndexingSettings: 'Advanced Indexing Settings',
  advancedIndexingDesc: 'Fine-tune how your documents are split and processed.',
  chunkSize: 'Chunk Size (Characters)',
  chunkSizeHint:
    'Determines the size of text chunks. Larger chunks capture more context but may lose precision. (Default: 1024)',
  chunkOverlap: 'Chunk Overlap (Characters)',
  chunkOverlapHint:
    'Amount of text shared between adjacent chunks to maintain context continuity. (Default: 200)',

  back: 'Back',
  next: 'Next',
  noDataSources: 'No data sources connected',
  noConnectorsFound: 'No data sources found',
  addFirstSource: 'Add your first data source to get started.',
  selectConnector: 'Select a data source below to get started',
  selectConnectorType: 'Select a data source type',
  searchConnectorType: 'Search data source type...',
  connect: 'Connect',
  editConnector: 'Edit {type} data source',
  addConnector: 'Add {type} data source',
  testConnection: 'Test Connection',
  addFile: 'Add File',
  fileAlreadyExists: 'This file has already been added to this data source.',
  connectorNameHint: 'A unique name to identify this data source',
  connectorDescriptionHint: 'A description to help users identify this data source',

  // Specific Connector Fields
  sharePoint: 'Microsoft SharePoint',
  sharePointDesc:
    'Sync documents and sites from your organization. Good for HR policies, internal procedures and project documentation.',
  sql: 'SQL Database',
  sqlDesc:
    'Connect to Microsoft SQL Server, PostgreSQL or MySQL. Connect your structured databases. Allows AI to query business data like inventory, sales, or customer records.',
  vannaSql: 'Vanna SQL (AI)',
  vannaSqlDesc:
    'AI-powered SQL assistant (Vanna.ai). Automatically generates and executes SQL queries from natural language. No need to create views - just ask questions and get data.',
  folder: 'Local File',
  folderDesc:
    'Manually import files from your computer. Perfect for one-off analysis of contracts, reports, or offline documents.',
  csvFile: 'CSV File',
  csvFileDesc:
    'Manually import CSV files from your computer. Perfect for structured data analysis.',
  networkDesc:
    'Connect to a folder or network share to index files stored on local servers or NAS. Ideal for accessing historical archives and departmental network drives.',
  confluence: 'Confluence',
  confluenceDesc:
    'Sync pages and blogs from Atlassian Confluence. Perfect for technical documentation, project requirements, and team knowledge bases.',

  // Connector Configuration
  schedule: 'Schedule',
  schedule5m: 'Every 5 minutes',
  Day: 'Day',
  Sunday: 'Sunday',
  Monday: 'Monday',
  Tuesday: 'Tuesday',
  Wednesday: 'Wednesday',
  Thursday: 'Thursday',
  Friday: 'Friday',
  Saturday: 'Saturday',
  filePath: 'File Path',
  folderPath: 'Folder Path',
  labelSiteUrl: 'Site URL',
  labelTenantId: 'Tenant ID',
  labelClientSecret: 'Client Secret',
  labelHost: 'Host',
  labelHostSql: 'Host (SQL Server)',
  labelHostHint:
    'DNS name or IP address of the SQL Server (e.g. sql-prod-01.your-domain.com or 192.168.1.100)',
  labelPort: 'Port',
  labelPortHint: 'SQL Server connection port (default: 1433)',
  labelDatabase: 'Database Name',
  labelDatabaseName: 'Database Name',
  labelDatabaseHint: 'Exact name of the database to connect to (e.g. SalesProd, InventoryDB)',
  labelSchema: 'SQL Schema',
  labelSchemaHint: 'Name of the schema containing the views to scan (default: vectra)',
  labelUser: 'User',
  labelUserSql: 'SQL User',
  labelUserHint: 'SQL Server username with read privileges (db_datareader). Avoid admin accounts.',
  labelPassword: 'Password',
  labelPasswordHint: 'SQL Server account password. Credentials are encrypted and stored securely.',
  recursive: 'Recursive Scan',
  filePattern: 'File Pattern (e.g. *.pdf)',
  fieldRequired: 'Field is required',
  fileRequired: 'File is required',
  fileAlreadyUploaded: 'File already uploaded',
  connectorAcl: 'Access Control Labels',
  connectorAclHint:
    'Access Control Labels that determine which assistants have access to the documents of this data source',
  documentAcl: 'Access Control Labels',
  documentAclHint:
    'Access Control Labels that determine which assistants have access to this specific document',
  aclTagRequired: 'At least one access control label is required (e.g. "public")',
  csvIdColumnMissing: 'The CSV file must contain an "id" column.',
  csvIdColumnNotUnique: 'The "id" column in the CSV file must contain unique values.',
  csvValidationGenericError: 'An error occurred while validating the CSV file.',
  file_not_found: 'The file was not found.',
  validationError: 'Validation Error',

  // Vanna SQL Specific
  aiTraining: 'AI Training',
  databaseSchema: 'Database Schema (DDL)',
  vannaDdlHint: 'Paste your CREATE TABLE statements to train Vanna on your database structure',
  vannaDdlExample:
    'Ex: CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(255), email VARCHAR(255));',
  trainAI: 'Train AI',
  lastTrained: 'Last trained',
  trainingSuccess: 'Training successful',
  trainingFailed: 'Training failed',
  saveConnectorFirst: 'Please save the connector before training',

  // --- New Stepper Steps ---
  accessControl: 'Access Control',
  aclPublic: 'Organization Wide',
  aclPublicDesc: 'All assistants can access these documents.',
  aclRestricted: 'Restricted',
  aclRestrictedDesc:
    'Only assistants with specific Access Control Labels can access these documents.',
  defineAccessTags: 'Define Access Control Labels',

  syncSchedule: 'Sync Schedule',
  syncScheduleDesc: 'How often should we check for new content?',
  scheduleManual: 'Manual',
  scheduleManualDesc: 'Run sync manually when needed.',
  scheduleDaily: 'Daily',
  scheduleDailyDesc: 'Sync at midnight every day.',
  scheduleWeekly: 'Weekly',
  scheduleWeeklyDesc: 'Sync every Sunday at midnight.',
  scheduleMonthly: 'Monthly',
  scheduleMonthlyDesc: 'Sync on the 1st of every month.',
  Hourly: 'Hourly',
  'Every hour': 'Every hour',
  manualOnlyForLocalFiles: 'Only manual sync is available for file uploads.',

  // FolderPicker / FolderInput
  browseFolder: 'Browse Folder',
  manualInputRequired: 'Manual Input Required (Web Mode)',
  manualInputRequiredTitle: 'Manual Input Required',
  manualInputWebMode: 'Manual input required in Web Mode',
  manualInputPastePath: 'Manual input required in Web Mode. Please paste the path.',

  // Connector Actions & Status
  syncNow: 'Vectorize Now',
  forceSync: 'Force Re-vectorization',
  stopSync: 'Stop Vectorization',
  enableToSync: 'Enable data source to vectorize.',
  scheduledSyncOnly: 'Manual vectorization disabled because a schedule is active.',
  confirmDeletion: 'Confirm Deletion',
  confirmDeletionMessage: 'Are you sure you want to delete "{name}"? This action is irreversible.',
  confirm: 'Confirm',
  confirmPathChange: 'Confirm Directory Change',
  confirmPathChangeMessage:
    'Changing the folder directory will effectively delete all existing files and their vectors from this data source, as they will not exist in the new path. Are you sure you want to proceed? Consider creating a new data source instead.',
  confirmRecursiveDisable: 'Confirm Recursive Scan Disable',
  confirmRecursiveDisableMessage:
    'Disabling recursive scan will cause all files in subdirectories to be removed from this data source (and their vectors deleted). Are you sure?',
  sourceToggled: '{name} {status}',
  syncStarted: 'Vectorization started for {name}',
  forceSyncStarted: 'Force vectorization started',
  syncStopped: 'Vectorization stopped for {name}',
  connectorUpdated: '{name} updated',
  connectorCreated: '{name} created',
  connectorDeleted: '{name} deleted',
  failedToLoad: 'Failed to load data sources',
  failedToSave: 'Failed to save data source',
  failedToDelete: 'Failed to delete data source',
  failedToStopSync: 'Failed to stop vectorization',
  stop: 'Stop',
  stopRequested: 'Stop requested for {name}',
  failedToStop: 'Failed to stop document',
  failedToStartSync: 'Failed to start vectorization',
  refreshFiles: 'Refresh Objects',
  scanStarted: 'File scan started for {name}',
  failedToScan: 'Failed to trigger file scan',
  FILE_ALREADY_EXISTS: 'File already exists in this data source',

  // Connector Status Enums
  enabled: 'Enabled',
  disabled: 'Disabled',
  idle: 'Idle',
  vectorizing: 'Vectorizing',
  processing: 'Processing...',
  error: 'Error',
  paused: 'Paused',
  queued: 'Queued',
  neverSynced: 'Never vectorized',
  starting: 'Starting',
  syncing: 'Vectorizing',
  created: 'Created',
  dismiss: 'Dismiss',
  unknownSource: 'Unknown Source',

  // --- Documents ---
  manageDocuments: 'Manage Documents',
  loading: 'Loading...',
  documents: 'Documents',
  viewDocuments: 'View Documents',
  searchFile: 'Search file...',
  filename: 'Filename',
  tokens: 'Tokens',
  vectors: 'Vectors',
  contentUnavailable: 'Content unavailable.',
  viewOriginal: 'View original document',
  selectFile: 'Select File',
  unknownDocument: 'Structured Data',
  noDocumentsFound: 'No documents found',
  noDocumentsDesc: 'This data source has no documents yet.',
  documentDeleted: 'Document deleted successfully',
  documentAdded: 'Document added successfully',
  documentUpdated: 'Document updated successfully',
  editFile: 'Edit File',
  uploadingFile: 'Uploading file...',
  failedToUploadFile: 'Failed to upload file',

  // --- Avatar ---
  avatarImage: 'Avatar Image',
  avatarVerticalPosition: 'Avatar Vertical Position',
  saveToUploadAvatar: 'Please save assistant to upload an avatar',
  removeAvatar: 'Remove Avatar',
  uploadAvatar: 'Upload Avatar',
  previewMessage: 'Hello! This is how I will look.',
  uploadPhoto: 'Upload Photo',
  uploadAvatarHint: 'Upload an avatar image',
  botDefaultName: 'Bot',
  library: 'Library',
  viewAll: 'View All',
  presetLibrary: 'Preset Library',
  avatarUploaded: 'Avatar uploaded successfully',
  avatarUploadFailed: 'Failed to upload avatar',
  avatarRemoved: 'Avatar removed',
  avatarRemoveFailed: 'Failed to remove avatar',

  // --- Assistants ---
  myAssistantsDesc: 'Manage and chat with your AI assistants',
  createNew: 'Create New',
  noAssistants: 'No assistants yet',
  noAssistantsAvailable: 'No assistants available',
  createYourFirstAssistant: 'Create your first assistant',
  editAssistant: 'Edit Assistant',
  newAssistant: 'New Assistant',
  saveAssistant: 'Save',
  assistantUpdated: 'Assistant updated successfully',
  assistantCreated: 'Assistant created successfully',
  assistantDeleted: 'Assistant deleted',
  failedToSaveAssistant: 'Failed to save assistant',
  failedToDeleteAssistant: 'Failed to delete assistant',

  // Assistant Form
  identity: 'Identity',
  appearance: 'Appearance',
  background: 'Background',
  backgroundColor: 'Background Color',
  text: 'Text',
  textColor: 'Text Color',
  preview: 'Preview',
  presets: 'Presets',
  chooseColor: 'Choose Color',
  intelligence: 'Intelligence',
  model: 'Model',
  nameRequired: 'Name is required',
  systemInstructions: 'System Instructions',
  instructionsHint: 'Describe how the assistant should behave',
  instructionsRequired: 'Instructions are required',
  dataSources: 'Data Sources',
  selectDataSources: 'Select Data Sources',
  filteringId: 'Access Control Label',
  filteringIdHint: 'ID for access control (e.g. TenantID, GroupID, etc.)',
  filteringTagRequired: 'At least one label is required (e.g. "public")',
  accessControlList: 'Access Control List',
  accessControlDesc: 'based on the data sources selected above.',
  selectAclTags: 'Select ACL Tags',
  security: 'Security',
  userAuthentication: 'User Authentication',
  userAuthenticationHint: 'Enforce user authentication for this assistant.',

  // --- Advanced LLM Parameters ---
  advancedLlmParameters: 'Advanced LLM Parameters',
  advancedLlmParametersDesc: 'Fine-tune the model behavior with technical parameters.',
  configureAdvancedParams: 'Settings',
  amount: 'Amount', // Helper key if needed, or just use literal in hint
  assistantTemperature: 'Creativity (Temperature)',
  temperatureHint: '0.0 = Factual & precise (Best for RAG). 1.0 = Creative & unpredictable.',
  topP: 'Top P (Nucleus Sampling)',
  topPHint: 'Controls diversity. Low (0.1) = focused, High (0.9) = creative. (Default: 1.0)',
  maxOutputTokens: 'Max Length (Max Output Tokens)',
  maxOutputTokensHint: 'Limits response token count. e.g. 1024 for summaries, 8192 for reports.',
  frequencyPenalty: 'Word Repetition (Frequency Penalty)',
  frequencyPenaltyHint:
    'Prevents using the same words too often. Increase if text feels robotic. (Default: 0.0)',
  presencePenalty: 'Topic Diversity (Presence Penalty)',
  presencePenaltyHint:
    'Forces AI to cover new topics. Increase if AI repeats ideas. (Default: 0.0)',

  // --- Parameter Explanations ---
  tempTitle: '🌡️ Temperature (T)',
  tempSubtitle: 'The Creativity Slider',
  tempDesc:
    'Temperature controls the degree of randomness in word choice by modifying the probability distribution of tokens.',
  tempExpert:
    'Low (0.1 - 0.3): "The Rigid Expert". The AI almost always chooses the most likely word. Ideal for SQL generation or precise extraction. Factual and reproducible.',
  tempCollaborator:
    'Medium (0.7 - default): "The Collaborator". A good balance for fluid discussion without wandering too much.',
  tempPoet:
    'High (1.0 - 1.5): "The Hallucinated Poet". The AI takes risks and uses rare words. Great for brainstorming but risky for RAG.',
  topKTitle: '🎯 Top K',
  topKSubtitle: 'The Diversity Filter',
  topKDesc: 'Top K limits the "vocabulary" available for each generated word.',
  topKSmall:
    "Small K (e.g., 10): The AI is highly focused. It won't say anything weird, but sentences may feel repetitive.",
  topKLarge:
    'Large K (e.g., 100+): The AI has access to a much richer vocabulary. More natural, but higher chance of nonsense if temperature is high.',

  // Optimization
  instructionsOptimized: 'Instructions optimized!',
  failedToOptimize: 'Optimization failed',
  optimizeWithAi: 'Optimize with AI',

  // --- Chat & Interaction ---
  welcomeMessage: 'Hello! I am {name}.',
  howCanIHelp: 'How can I help you today?',
  typeMessage: 'Type your message...',
  newConversation: 'New Conversation',
  conversationReset: 'Conversation reset.',
  initializing: 'Connecting to AI...',
  communicationError: 'An error occurred while communicating with the assistant.',
  share: 'Share Link',
  linkCopied: 'Link copied to clipboard',
  talk: 'Talk',
  usedSources: 'Used Sources',
  noSourcesUsed: 'No sources used',
  sourcesLabel: 'Sources',
  assistantNotFound: 'Assistant not found or unavailable.',
  invalidAssistantId: 'Invalid Assistant ID',

  // --- Notifications ---
  notifications: 'Notifications',
  noNotifications: 'No notifications',
  dismissAll: 'Dismiss All',
  readAll: 'Mark all as read',
  clearAll: 'Clear All',
  debug: 'Debug',

  // --- Dialogs ---
  unsavedChanges: 'Unsaved Changes',
  unsavedChangesMessage: 'You have unsaved changes. Are you sure you want to close?',
  discard: 'Discard',
  keepEditing: 'Keep Editing',
  ingestionFailedForDoc: 'Processing failed for {name}',
  unknownError: 'Unknown error',

  // --- Errors ---
  pageNotFound: '404',
  oopsNothingHere: 'Oops. Nothing here...',
  goHome: 'Go Home',
  errors: {
    internal_error: 'An internal error occurred.',
    INVALID_CREDENTIALS: 'Invalid credentials. Please check your username and password.',
    technical_error: 'A technical error occurred.',
    entity_not_found: 'Resource not found.',
    duplicate_resource: 'Resource already exists.',
    invalid_state: 'Invalid operation for the current state.',
    forbidden: "You don't have permission to perform this action",
    unauthorized_action: 'You are not authorized to perform this action.',
    external_dependency_error: 'External service is unavailable.',
    internal_data_corruption: 'Data integrity error.',
    filesystem_error: 'File system operation failed.',
    invalid_csv_format: 'Invalid CSV format.',
    file_parsing_error: 'Failed to parse file.',
    unsupported_format: 'Unsupported file format.',
    doc_too_large: 'Document is too large (max 10MB).',
    csv_id_column_missing: 'CSV must contain an "id" column.',
    csv_id_column_not_unique: 'CSV "id" column must contain unique values.',
    invalid_csv_data: 'Failed to read CSV data.',
    path_not_found: 'The specified folder path does not exist.',
  },
  model_desc: {
    // ── Gemini Chat ──
    'gemini-3-pro-preview':
      'Our most powerful frontier model. Superior reasoning, coding, and complex task handling with massive context.',
    'gemini-2.5-pro':
      'Premium flagship model. Optimized for high-level reasoning and deep document analysis.',
    'gemini-3-flash-preview':
      'Next-gen efficiency (Preview). Ultra-fast responses with GPT-4 class intelligence.',
    'gemini-2.5-flash':
      'The perfect all-rounder. Fast, reliable, and capable for most production tasks.',
    'gemini-2.5-flash-lite':
      'High-efficiency 2.5 model. Optimized for speed and massive volume at low cost.',
    'gemini-2.0-flash':
      'Industry-leading speed. Incredible performance with near-instant responses.',
    'gemini-2.0-flash-lite':
      'Our most cost-effective model ever. Built for massive scale without sacrificing core logic.',
    'gemini-embedding-001':
      'Stable, legacy-compatible embedding model. Great for consistent results across all Google Cloud regions.',

    // ── OpenAI Chat ──
    'gpt-5.2':
      'The latest pinnacle of AI intelligence. It feels more "human" in its reasoning and can handle extremely complex instructions across vast amounts of text.',
    'gpt-5.2-pro':
      'The "Expert" model. If you need a virtual scientist, senior coder, or deep strategist, this is the most precise and capable model OpenAI offers.',
    'gpt-5.1':
      'A highly capable and reliable flagship model. It offers a premium experience with great stability for professional and creative writing.',
    'gpt-5':
      'The foundation of the new generation. A very smart all-rounder that handles almost any task with high intelligence and natural phrasing.',
    o1: 'The "Deep Thinker". Unlike other models, it "thinks" before it speaks. Best for complex logic, math problems, and scientific reasoning where accuracy is paramount.',
    o3: 'The next generation of reasoning. Faster and even more logical than its predecessors, it is a master of solving difficult puzzles and coding challenges.',
    'o3-mini':
      'A faster, more compact version of the reasoning models. Great when you need logic-heavy processing but want a quicker response time.',
    'o4-mini':
      'The most affordable logical thinker. It provides advanced reasoning capabilities at a fraction of the cost of the larger models.',
    'gpt-5-mini':
      'Smart, fast, and affordable. The best choice for most users who want the power of the latest generation for daily tasks without the high cost.',
    'gpt-4.1-mini':
      'A reliable and very fast model widely used for production. It is great for building apps that need quick, intelligent responses.',
    'gpt-4o-mini':
      'A classic cost-effective model. It is very fast and works well for simple interactions and data processing.',
    'gpt-5-nano':
      'The ultra-lightweight version. Almost instantaneous and extremely cheap. Best for very simple tasks or high-volume processing of basic data.',

    // ── Mistral Chat ──
    'mistral-large-latest':
      'Mistral’s heavy hitter. It is designed to compete with the smartest models in the world, excelling at complex reasoning and high-precision coding.',
    'mistral-medium-latest':
      'The "Goldilocks" model: smart enough for complex work but optimized for speed and cost. Great for professional business applications.',
    'mistral-small-latest':
      'Efficient and focused. It has a large memory for its size, making it ideal for routine tasks that involve reading several documents at once.',
    'open-mistral-nemo':
      'A specialized model developed with NVIDIA. It is impressively smart for its size and works especially well for technical and edge use cases.',
    'mistral-tiny':
      'The most basic Mistral model. Best for fast, simple tasks like identifying keywords or basic text categorization.',
    'ministral-3b-latest':
      'A tiny model designed to run on small devices. Very fast and focused on simple, direct instructions.',
    'ministral-8b-latest':
      'A balanced small model. It offers surprisingly good reasoning for its compact size, perfect for efficient local processing.',
    'ministral-14b-latest':
      'The largest of the small models. It can handle more complex logic than the 3b or 8b while remaining very fast.',
    'codestral-latest':
      'The "Coding Specialist". This model was specifically trained to write and debug code in over 80 programming languages.',
    'pixtral-large-latest':
      'A multimodal expert. Not only can it read text, but it can also "see" and analyze complex images, charts, and technical diagrams with high precision.',
    'pixtral-12b-2409':
      'A versatile model that can handle both text and images efficiently. Great for general vision tasks like describing what is in a photo.',
    'voxtral-latest':
      'The "Audio Expert". Specialized in understanding and processing spoken language and audio files directly.',
    'devstral-latest':
      'An experimental tool designed specifically for developers. It is optimized to act as an assistant for software engineering tasks.',
    'open-mistral-7b':
      'A classic and reliable model that started it all. Fast and effective for simple, direct conversations.',

    // ── Ollama Chat ──
    mistral:
      'A powerful local model that runs entirely on your own computer. It is very efficient, good at logic, and has excellent support for the French language.',

    // ── Embedding (Search & Organization) ──
    'models/text-embedding-004':
      "The current standard for search. It converts text into a mathematical format that allows the system to find documents based on their 'meaning' rather than just keywords.",
    'models/text-embedding-005':
      'The next-generation search model. Faster and more efficient at organizing large amounts of data for pinpoint retrieval.',
    'text-embedding-3-small':
      'OpenAI’s highly efficient search model. It provides great performance for general document search and organization.',
    'text-embedding-3-large':
      'The most powerful search model from OpenAI. It captures very subtle nuances in text, making it the best choice for high-accuracy research.',
    'bge-m3':
      'The ultimate multilingual search model. It can help find documents across over 100 different languages with high accuracy.',
    'nomic-embed-text':
      'A high-performance open-source search model. It has a massive memory for reading very long documents during the search process.',

    // ── Rerank (Refining Search Results) ──
    'BAAI/bge-reranker-base':
      'A local "quality checker". It takes your search results and re-runs them to ensure the most relevant ones are at the very top. Runs privately on your machine.',
    'BAAI/bge-reranker-v2-m3':
      'The latest generation local quality checker. It is more accurate and supports many languages, ensuring your search results are always relevant.',
    'rerank-v3.5':
      'The gold standard for search refinement. It is incredibly good at understanding the "intent" of your question to pick the perfect document from a list.',
    'rerank-multilingual-v3.0':
      'Optimized for international use. It refines search results across dozens of languages to ensure accuracy regardless of the document’s language.',
    'rerank-english-v3.0':
      'A specialized quality checker for English. It is very fast and precise when dealing exclusively with English content.',

    // ── Transcription (Speech to Text) ──
    'whisper-1':
      'The industry leader in converting speech to text. Extremely accurate at transcribing audio files into written documents.',
    whisper:
      'A reliable, local version of speech-to-text. It allows you to transcribe audio privately on your own computer without sending data to the cloud.',
  },
  model_desc_transcription: {
    'gemini-1.5-flash':
      'The champion of speed. Ideal for converting large amounts of audio to text quickly and at a lower cost.',
    'gemini-1.5-pro':
      'The expert choice for precision. Capable of faithfully transcribing complex, long, or multi-speaker recordings.',
    'whisper-1':
      'World-class voice specialist. Recognizes speech with incredible accuracy, even with heavy accents or background noise.',
    whisper:
      'Private and local transcription. Transcribes your files directly on your computer without ever sending data to the cloud.',
  },
  model_desc_extraction: {
    'gemini-1.5-flash': 'Quick and accurate for extracting key information from simple documents.',
    'gemini-2.0-flash':
      'Optimized for complex data extraction with an excellent speed-to-accuracy ratio.',
    'gpt-4o-mini':
      'Great compact model for understanding data structure and isolating important points.',
    mistral: 'Efficient local model for analyzing your documents privately.',
  },
  // --- Assistant Wizard ---
  wizard: {
    step1Title: 'Identity & Role',
    step1Caption: 'The Architect',
    step1Heading: 'Identity Definition',
    nameLabel: 'Name',
    nameHint: 'Give a unique name to your assistant (e.g. Marketing Assistant)',
    nameRequired: 'Name is required',
    targetLabel: 'Target Audience',
    targetHint: 'Who is this assistant for? (e.g. Junior Parts Clerks)',
    roleLabel: 'Role / Persona',
    roleHint:
      'Describe its role and expertise (e.g. Senior Auto Parts Expert with 20 years experience...)',

    step2Title: 'The Mission',
    step2Caption: 'The Brain',
    step2Heading: 'Objectives & Behavior',
    objectiveLabel: 'Main Objective',
    objectiveHint: 'What is the primary goal of the bot? What must it accomplish?',
    objectiveRequired: 'Objective is required',
    ragBehaviorLabel: 'RAG Behavior',
    ragStrict: "Strict (I don't know)",
    ragFlexible: 'Flexible (Deduction)',

    step3Title: 'Tone & Style',
    step3Caption: 'The Voice',
    step3Heading: 'Personality & Format',
    toneLabel: 'Tone',
    toneHint: 'What tone should it use?',
    languageLabel: 'Language',
    languageHint: 'Primary response language',
    formatLabel: 'Response Format',
    formatHint: 'Formatting instructions (e.g. Bullet points, bold prices, concise...)',

    step4Title: 'Guardrails',
    step4Caption: 'Safety',
    step4Heading: 'Safety & Restrictions',
    taboosLabel: 'Taboo Subjects',
    taboosHint: 'Type and press Enter to add forbidden topics (e.g. Politics, Religion)',
    securityRulesLabel: 'Security Rules',
    securityRulesHint: 'Strict rules to follow (e.g. Never invent a part number)',

    btnNext: 'Next',
    btnPrev: 'Previous',
    btnGenerate: 'Generate',
    stepPerformanceTitle: 'Performance',
    stepPerformanceHeading: 'Performance & Caching',
    stepPerformanceCaption: 'Optimize speed & costs',
  },

  performance: {
    enableCache: 'Enable Semantic Cache',
    similarityThreshold: 'Similarity Threshold',
    cacheTTL: 'Cache Duration (Seconds)',
    thresholdHelp: 'Higher score means query must be more identical to match.',
    ttlHelp: 'Time to live for cached responses.',
    cacheHelpResult:
      'If enabled, similar questions will instantly return the previous answer without querying the LLM.',
    timeUnits: {
      seconds: 's',
      minutes: 'min',
      hours: 'h',
      days: 'd',
    },
    dangerZone: 'Danger Zone',
    purgeCache: 'Purge Assistant Cache',
    purgeCacheHelp:
      'Forces the removal of all cached answers for this assistant. Use this if the AI is providing outdated information.',
    purgeConfirmTitle: 'Confirm Purge',
    purgeConfirmMessage:
      'Are you sure? This will force the assistant to re-generate answers for all future questions.',
    purgeSuccess: 'Cache purged successfully',
    purgeFailed: 'Failed to purge assistant cache',
  },

  // --- Common ---
  assistantWizard: 'Assistant Wizard',
  generateWithWizard: 'Generate with Wizard',
  stepGeneral: 'General Information',
  stepPersonality: 'Personality',
  stepKnowledge: 'Knowledge Base',
  stepGeneralDesc: 'Setup identity',
  stepIntelligenceDesc: 'Select model',
  stepPersonalityDesc: 'Define behavior',
  stepKnowledgeDesc: 'Link data sources',
  linkConnectorsDesc: 'Select which knowledge bases this assistant can access.',
  systemInstructionsHint: 'Define how the assistant behaves and answers.',
  createNewAssistant: 'Create New Assistant',
  createAssistant: 'Create Assistant',
  defaultSystemInstructions: 'You are a helpful assistant.',
  pipelineSteps: {
    title: 'Pipeline Steps',
    connection: 'AI Preparation',
    cache_lookup: 'Cache Lookup',
    cache_hit: 'Cache Hit: Answer restored',
    cache_miss: 'Cache Miss: Proceeding to search',
    history_loading: 'Loading Chat History',
    query_rewrite: 'Query Rewrite',
    vectorization: 'Vectorization',
    retrieval: 'Retrieval',
    reranking: 'Reranking',
    synthesis: 'Synthesis',
    assistant_persistence: 'Assistant message saved',
    cache_update: 'Cache Update',
    user_persistence: 'User message saved',
    trending: 'Trending',
    completed: 'Completed',
    failed: 'Failed',
    initialization: 'Chat Initialization',
    visualization_analysis: 'Visualization Analysis',
    ambiguity_guard: 'Contextual Query Guard',
    csv_schema_retrieval: 'Structured Data Retrieval',
    csv_synthesis: 'Product Profile Generation',
    facet_query: 'Faceted Filter Analysis',
    router: 'Agentic Router',
    router_processing: 'Context Preparation',
    router_reasoning: 'Generating Answer',
    router_retrieval: 'Retrieve Knowledge Base',
    router_selection: 'Tool Selection',
    sql_generation: 'Generate SQL Query',
    sql_schema_retrieval: 'Retrieve SQL Metadata',
    tool_execution: 'Execute AI Tool',
    query_execution: 'Query Execution',
    router_synthesis: 'Synthesize Answer',
    streaming: 'Finalizing Response',
  },
  stepDescriptions: {
    connection:
      'Establishing a secure connection with the AI providers and database services. This initial handshaking ensures the environment is ready for processing.',
    query_rewrite:
      'Refining your question to improve search results by adding missing context from the conversation. This step makes the query clearer for the AI retrieval engines.',
    cache_hit:
      'The exact answer was found in the semantic cache, saving time and cost. The response is instantly restored without needing a fresh AI generation.',
    cache_miss:
      'Reference answer was not found in the semantic cache. The system is proceeding with full analysis and data retrieval to construct a new answer.',
    router_processing:
      'Preparing the conversation context and initializing specialized AI tools. This setup ensures that the most appropriate model is selected for your query.',
    router_reasoning:
      'The AI is analyzing your request to determine the best approach. It evaluates whether it needs to search documents, query a database, or perform a direct task.',
    router_selection:
      'The intelligent router evaluates whether your question requires a document search (vector) or a precise database query (SQL). This choice ensures the highest accuracy for the final response.',
    sql_generation:
      'Translating your natural language question into a secure and optimized SQL query. This command will be executed directly on the connected database to extract exact figures.',
    sql_schema_retrieval:
      'Reading the structure of your SQL database, including table names and column types. This allows the AI to understand how to query your data accurately.',
    tool_execution:
      'Orchestrating and executing the specialized tool selected to handle your specific request. This step bridges the gap between your question and the data sources.',
    router_retrieval:
      'Searching the Knowledge Base for relevant resources, such as documents or available database views. This semantic match identifies the right context needed to answer your request.',
    router_synthesis:
      "Constructing the final answer by merging retrieved data with the model's linguistic capabilities. This ensures a natural, accurate, and context-aware response.",
    cache_lookup:
      'Ultra-fast lookup in short-term memory to check if this exact question has been answered recently. This optimization drastically reduces response time for common queries.',
    retrieval:
      'A semantic search algorithm is scanning your knowledge base to find the most relevant document fragments. This identifies the core information needed to answer.',
    reranking:
      'A specialized Cross-Encoder model performs a second-pass analysis to re-sort results by strict relevance. This eliminates noisy or irrelevant data fragments.',
    synthesis:
      'The AI reads the retrieved documents and formulates a clear, direct answer to your question. All information is verified against the sources with proper citations.',
    assistant_persistence:
      'Securely archiving the assistant answer in your conversation history. This persistence allows you to refer back to this exchange in future sessions.',
    trending:
      'Anonymizing and aggregating metadata from this question to fuel analytics dashboards. This helps identify popular topics and detect emerging trends.',
    vectorization:
      'Converting your text into multidimensional mathematical vectors. This mathematical representation enables semantic comparison with your entire knowledge base.',
    cache_update:
      'Updating the semantic cache with the newly generated response. This step ensures that future identical requests can be answered instantly.',
    visualization_analysis:
      'Intelligently analyzing the optimal presentation format for your data. The system automatically selects between tables, pie charts, bar charts, or line graphs.',
    initialization:
      'Initializing the conversational context and loading the assistant configuration. This verifies connectivity with all necessary AI and database providers.',
    streaming:
      'Streaming the response from the AI model in real-time. This tracks the generation of each token to provide precise speed and cost transparency.',
    ambiguity_guard:
      'Analyzing the query to detect vagueness and merging the conversational context into a formal request. This ensures the AI understands implicit references and complex temporal filters.',
    csv_schema_retrieval:
      'Targeted querying of structured data files by applying the specific criteria extracted from your question. This search precisely locates relevant entries within your CSV catalogs.',
    csv_synthesis:
      'Extracting and formatting technical specifications from the filtered product data. The system constructs a clear summary sheet, organizing key attributes for professional presentation.',
    facet_query:
      'Dimensional exploration of available attributes to suggest intelligent refinement options. This transforms a raw search into a guided navigation through relevant data categories.',
    router:
      'The central brain deciding which path to take (SQL, Vector, or Tools) based on the user request. This routing ensures the most efficient tool handles your specific question.',
    history_loading:
      'Retrieving previous messages to maintain conversation context. This allows the AI to refer back to what was discussed in previous turns.',
    user_persistence:
      'Saving your question to the conversation history to maintain context for future turns. This ensures continuity throughout your chat session.',
    completed:
      'Request processing finished successfully. All results have been gathered and are ready for review.',
  },
  conversationCleared: 'Conversation cleared',
  validate: {
    atLeastOneSource: 'Please select at least one knowledge base.',
  },
};
