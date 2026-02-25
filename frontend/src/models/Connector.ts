import { Base } from './Base';
import { ConnectorStatus, ConnectorType, ScheduleType } from './enums';

export interface ConnectorSavePayload {
  type: string;
  data: Connector;
}

/**
 * Represents a data source connector configuration.
 * Maps directly to the backend Connector Pydantic model.
 */
export class Connector extends Base {
  /** Display name of the connector */
  name: string;
  /** Optional description */
  description: string | undefined;
  /** Cron expression for scheduled syncs */
  schedule_cron: string | undefined;
  /** Type identifier (e.g., 'sharepoint', 'sql', 'file') */
  connector_type: ConnectorType;
  /*
  I've fixed the ESLint error. Since configuration is a dynamic property that holds different data 
  depending on the connector type, using Record<string, any> is the correct approach. I added a 
  eslint-disable-next-line comment to KnowledgeBase.ts to suppress the linting rule for this 
  specific line, allowing the code to compile while maintaining the flexibility we need. 
  I also verified that FolderForm.vue is clean.
  */
  /** Dynamic configuration specific to the connector type */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  configuration: Record<string, any>;
  /** Whether the connector is active */
  is_enabled: boolean;
  /** UI helper for schedule type (manual, daily, weekly, monthly) */
  schedule_type: ScheduleType;

  /** Current synchronization status */
  status: ConnectorStatus;
  /** Error message if the last sync failed */
  last_error: string | undefined;
  /** Timestamp of the last successful sync */
  last_vectorized_at: string | undefined;

  // Chunking
  chunk_size: number;
  chunk_overlap: number;

  // Observability
  /** Total number of documents found */
  total_docs_count: number;
  /** Number of documents successfully indexed */
  indexed_docs_count: number;
  /** Number of documents that failed processing */
  failed_docs_count: number;
  /** Start time of the last sync operation */
  last_sync_start_at: string | undefined;
  /** End time of the last sync operation */
  last_sync_end_at: string | undefined;

  // Transient (for progress bars)
  sync_current?: number;
  sync_total?: number;

  /**
   * Creates a new Connector instance.
   * @param {Partial<Connector>} data - Initial data to populate the connector.
   */
  constructor(data: Partial<Connector> = {}) {
    super(data);
    this.name = data.name || '';
    this.description = data.description;
    this.schedule_cron = data.schedule_cron;
    this.connector_type = data.connector_type || ConnectorType.LOCAL_FILE;
    this.configuration = data.configuration || {};
    this.is_enabled = data.is_enabled ?? true;
    this.schedule_type = data.schedule_type || ScheduleType.MANUAL;

    this.status = data.status || ConnectorStatus.IDLE;
    this.last_error = data.last_error;
    this.last_vectorized_at = data.last_vectorized_at;

    this.total_docs_count = data.total_docs_count || 0;
    this.indexed_docs_count = data.indexed_docs_count || 0;
    this.failed_docs_count = data.failed_docs_count || 0;
    this.last_sync_start_at = data.last_sync_start_at;
    this.last_sync_start_at = data.last_sync_start_at;
    this.last_sync_end_at = data.last_sync_end_at;

    this.chunk_size = data.chunk_size || 300;
    this.chunk_overlap = data.chunk_overlap || 30;

    // Transient
    this.sync_current = 0;
    this.sync_total = 0;
  }
}

/**
 * Derives a simplified schedule type and configuration from a cron expression.
 * @param {string} [cron] - The cron expression.
 * @returns {{ type: string, minute: number, hour: number, dayWeek: number, dayMonth: number }}
 */
export function parseCronExpression(cron?: string): {
  type: string;
  minute: number;
  hour: number;
  dayWeek: number;
  dayMonth: number;
} {
  if (!cron) return { type: 'manual', minute: 0, hour: 0, dayWeek: 0, dayMonth: 1 };

  const parts = cron.trim().split(' ');
  if (parts.length < 5) return { type: 'manual', minute: 0, hour: 0, dayWeek: 0, dayMonth: 1 };

  // Safe access since we checked length but TS needs assurance
  const m = parts[0] || '0';
  const h = parts[1] || '0';
  const d = parts[2] || '0';
  const mon = parts[3] || '0';
  const dow = parts[4] || '0';

  // Helper to safely parse int
  const p = (v: string) => (v === '*' || v === '?' ? 0 : parseInt(v, 10) || 0);

  // Helper to check for "any" (* or ?)
  const isAny = (v: string) => v === '*' || v === '?';
  const isSpec = (v: string) => !isAny(v);

  // Hourly: "15 * * * *" (Minute specified, others match all)
  if (isSpec(m) && isAny(h) && isAny(d) && isAny(mon) && isAny(dow)) {
    return {
      type: 'hourly',
      minute: p(m),
      hour: 0,
      dayWeek: 0,
      dayMonth: 1,
    };
  }

  // Daily: "30 14 * * *" (Minute, Hour specified, Day/Month/Dow match all)
  // Also handles standard "0 0 * * *"
  if (isSpec(m) && isSpec(h) && isAny(d) && isAny(mon) && isAny(dow)) {
    return {
      type: 'daily',
      minute: p(m),
      hour: p(h),
      dayWeek: 0,
      dayMonth: 1,
    };
  }

  // Weekly: "30 14 * * 1" (Minute, Hour, DoW specified)
  if (isSpec(m) && isSpec(h) && isAny(d) && isAny(mon) && isSpec(dow)) {
    return {
      type: 'weekly',
      minute: p(m),
      hour: p(h),
      dayWeek: p(dow),
      dayMonth: 1,
    };
  }

  // Monthly: "0 0 1 * *" (Minute, Hour, DayOfMonth specified)
  if (isSpec(m) && isSpec(h) && isSpec(d) && isAny(mon) && isAny(dow)) {
    return {
      type: 'monthly',
      minute: p(m),
      hour: p(h),
      dayWeek: 0,
      dayMonth: p(d),
    };
  }

  // Default to manual if we can't parse or it's complex
  return { type: 'manual', minute: 0, hour: 0, dayWeek: 0, dayMonth: 1 };
}

export function getScheduleLabel(cron: string | undefined, t: (key: string) => string): string {
  if (!cron) return t('scheduleManual');

  const { type, minute, hour, dayWeek, dayMonth } = parseCronExpression(cron);
  const time = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;

  switch (type) {
    case 'hourly':
      return `${t('Hourly')} (00:${String(minute).padStart(2, '0')})`;
    case 'daily':
      return `${t('scheduleDaily')} (${time})`;
    case 'weekly': {
      // Map 0-6 to Day names if possible, simplified here
      const days = [
        t('Sunday'),
        t('Monday'),
        t('Tuesday'),
        t('Wednesday'),
        t('Thursday'),
        t('Friday'),
        t('Saturday'),
      ];
      // Handle potential 7=Sun or 0=Sun mismatch if needed. Standard cron 0-6.
      const dayName = days[dayWeek % 7] || '';
      return `${t('scheduleWeekly')} (${dayName}, ${time})`;
    }
    case 'monthly':
      return `${t('scheduleMonthly')} (${t('Day')} ${dayMonth}, ${time})`;
    default:
      return t('scheduleManual'); // Or raw cron if preferred?
  }
}

/**
 * Legacy wrapper for getScheduleTypeFromCron if used elsewhere.
 */
export function getScheduleTypeFromCron(cron?: string): string {
  return parseCronExpression(cron).type;
}

/**
 * Converts a UI schedule configuration to backend CRON config.
 */
export function getScheduleConfigFromUiType(
  uiType: string,
  config: {
    minute?: number;
    hour?: number;
    dayWeek?: number;
    dayMonth?: number;
  } = {},
): {
  schedule_type: ScheduleType;
  schedule_cron?: string | undefined;
} {
  const { minute = 0, hour = 0, dayWeek = 1, dayMonth = 1 } = config;

  switch (uiType) {
    case 'hourly':
      return {
        schedule_type: ScheduleType.CRON,
        schedule_cron: `${minute} * * * *`,
      };
    case 'daily':
      return {
        schedule_type: ScheduleType.CRON,
        schedule_cron: `${minute} ${hour} * * *`,
      };
    case 'weekly':
      return {
        schedule_type: ScheduleType.CRON,
        schedule_cron: `${minute} ${hour} * * ${dayWeek}`,
      };
    case 'monthly':
      return {
        schedule_type: ScheduleType.CRON,
        schedule_cron: `${minute} ${hour} ${dayMonth} * *`,
      };
    case 'manual':
    default:
      return { schedule_type: ScheduleType.MANUAL, schedule_cron: undefined };
  }
}
