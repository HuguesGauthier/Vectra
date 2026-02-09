export const ConnectorStatus = {
  CREATED: 'created',
  IDLE: 'idle',
  QUEUED: 'queued',
  SYNCING: 'syncing',
  ERROR: 'error',
  PAUSED: 'paused',
  // Legacy
  STARTING: 'starting',
  VECTORIZING: 'vectorizing',
} as const;

export const ConnectorType = {
  LOCAL_FILE: 'local_file',
  LOCAL_FOLDER: 'local_folder',
  WEB: 'web',
  CONFLUENCE: 'confluence',
  SHAREPOINT: 'sharepoint',
  SQL: 'sql',
} as const;

export type ConnectorType = (typeof ConnectorType)[keyof typeof ConnectorType];

export const ScheduleType = {
  MANUAL: 'manual',
  CRON: 'cron',
} as const;

export type ScheduleType = (typeof ScheduleType)[keyof typeof ScheduleType];

export type ConnectorStatus = (typeof ConnectorStatus)[keyof typeof ConnectorStatus];

export const DocStatus = {
  PENDING: 'pending',
  IDLE: 'idle',
  PROCESSING: 'processing',
  INDEXED: 'indexed',
  FAILED: 'failed',
  SKIPPED: 'skipped',
  UNSUPPORTED: 'unsupported',
  PAUSED: 'paused',
} as const;

export type DocStatus = (typeof DocStatus)[keyof typeof DocStatus];
