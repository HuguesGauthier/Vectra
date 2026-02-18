import { uid } from 'quasar';
import { api } from 'boot/axios';
import { type ChatStep } from '../composables/useChatStream';
import messages from 'src/i18n';

// We define the type locally or import it if exported.
// Based on typical usage, let's define a flexible interface for now to avoid 'any'
interface TechSheetSection {
  title: string;
  items?: { label: string; value: string }[];
}

interface TechSheet {
  title?: string;
  sections?: TechSheetSection[];
}

// Minimal Source interface to satisfy type checking
interface Source {
  type?: string;
  name?: string;
  content?: string;
  metadata?: {
    file_name?: string;
    filename?: string;
    name?: string;
    connector_document_id?: string;
    connector_type?: string;
    timestamp_start?: string;
    page_label?: string;
    page_number?: number;
    page?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export class MessageRenderer {
  /**
   * Helper to get step description from i18n
   */
  private static getStepDescription(stepType: string | undefined): string {
    if (!stepType) return '';
    // Access i18n messages
    const locale = localStorage.getItem('app_language') || 'en-US';
    const localeMessages = messages[locale as keyof typeof messages];
    const stepDescriptions = localeMessages?.stepDescriptions as Record<string, string> | undefined;
    return stepDescriptions?.[stepType] || '';
  }

  /**
   * Generates HTML for a Tech Sheet
   */
  static renderTechSheet(techSheet: TechSheet): string {
    if (!techSheet) return '';

    // Basic Table Style for Tech Sheet
    // We use inline styles or classes defined in deep-chat-theme.css
    // deep-chat-html-container is defined in our CSS

    let html = `<div class="deep-chat-html-container tech-sheet-container">`;
    html += `<div class="text-h6 q-mb-sm">${techSheet.title || 'Technical Details'}</div>`;

    if (techSheet.sections && Array.isArray(techSheet.sections)) {
      techSheet.sections.forEach((section: TechSheetSection) => {
        html += `<div class="text-subtitle2 q-mt-sm text-weight-bold">${section.title}</div>`;
        if (section.items) {
          html += `<table style="width:100%; border-collapse: collapse; margin-top: 4px;">`;
          section.items.forEach((item) => {
            html += `
                        <tr style="border-bottom: 1px solid var(--q-third);">
                            <td style="padding: 4px 8px; font-weight: 500;">${item.label}</td>
                            <td style="padding: 4px 8px;">${item.value}</td>
                        </tr>
                     `;
          });
          html += `</table>`;
        }
      });
    }

    html += `</div>`;
    return html;
  }

  /**
   * Generates HTML for a generic Data Table (SQL Results)
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  static renderTable(data: any): string {
    // Check if data is just the array of records (legacy/Vanna format)
    let rows: Record<string, unknown>[] = [];
    let columns: { name: string; label?: string }[] = [];

    if (Array.isArray(data)) {
      rows = data;
      if (rows.length > 0) {
        // Auto-detect columns from first row
        columns = Object.keys(rows[0]!).map((key) => ({ name: key, label: key }));
      }
    } else if (data && data.columns && data.data) {
      // Structured format
      rows = data.data;
      columns = data.columns;
    }

    if (!rows || rows.length === 0) return '';

    // Wrap in Details/Summary for expandable UI
    let html = `
      <details class="data-table-details" style="
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px 16px;
        margin: 12px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        cursor: pointer;
      ">
        <summary style="
          list-style: none;
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 13px;
          font-weight: 500;
          user-select: none;
          outline: none;
        ">
          <span style="font-size: 16px;">📊</span>
          <span style="flex: 1;">
            Data Preview
            <span style="opacity: 0.7; font-weight: 400; margin-left: 8px;">
              (${rows.length} rows, ${columns.length} columns)
            </span>
          </span>
          <span class="expand-arrow" style="
            transition: transform 0.2s;
            font-size: 12px;
            opacity: 0.6;
          ">▼</span>
        </summary>

        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.1); overflow-x: auto;">
          <table style="width:100%; border-collapse: collapse; font-size: 13px; min-width: 400px;">
    `;

    // Header
    html += `<thead><tr style="border-bottom: 2px solid var(--q-primary); background: rgba(0,0,0,0.1);">`;
    columns.forEach((col) => {
      html += `<th style="padding: 8px; text-align: left; font-weight: 600; opacity: 0.9;">${col.label || col.name}</th>`;
    });
    html += `</tr></thead>`;

    // Body
    html += `<tbody>`;
    rows.forEach((row, index) => {
      const bg = index % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent';
      html += `<tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background: ${bg};">`;
      columns.forEach((col) => {
        const val = row[col.name] !== undefined && row[col.name] !== null ? row[col.name] : '';
        html += `<td style="padding: 8px; opacity: 0.8;">${String(val)}</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table></div>`;

    // Add styles for the arrow
    html += `
      </details>
      <style>
        .data-table-details[open] .expand-arrow {
          transform: rotate(180deg);
        }
        .data-table-details:hover {
          background: rgba(255, 255, 255, 0.08);
        }
      </style>
    `;
    return html;
  }

  /**
   * Generates HTML container for ApexCharts
   * The actual chart initialization happens via MutationObserver in the wrapper
   */
  static renderVisualizationContainer(): string {
    const uniqueId = `chart-${uid()}`;

    // We store the ID in a data-attribute so the observer can find it
    // We also put the configuration stringified in a hidden attribute or
    // we rely on a global store.
    // LIMITATION: HTML attributes have size limits and stringifying huge data is bad.
    // BETTER APPROACH: Return the HTML and the ID/Config pair separately to be registered.

    // For this implementation, let's keep it simple:
    // The wrapper will look for this ID. The caller (ChatPage) MUST register the chart config
    // in a temporary store or map using this ID before adding the message.

    return `
      <div id="${uniqueId}" 
           class="deep-chat-visualization-container" 
           style="min-height: 300px; width: 100%;">
           <div class="row flex-center full-height">
             <span class="text-grey italic">Loading Chart...</span>
           </div>
      </div>
    `;
  }

  /**
   * Generates HTML for Steps/Pipeline with expandable/collapsible functionality
   */
  static renderSteps(steps: ChatStep[]): string {
    if (!steps || steps.length === 0) return '';

    // FIX: Use the "Completed" step's values directly (it already contains correct totals)
    // If no "Completed" step exists, fall back to summing non-substeps
    const completedStep = steps.find(
      (s) => s.step_type === 'completed' && s.status === 'completed',
    );

    let totalDuration: number;
    let totalInputTokens: number;
    let totalOutputTokens: number;

    if (completedStep) {
      // Use the Completed step's values (already accurate)
      totalDuration = completedStep.duration || 0;
      totalInputTokens = completedStep.tokens?.input || 0;
      totalOutputTokens = completedStep.tokens?.output || 0;
    } else {
      // Fallback: sum non-substeps only
      totalDuration = steps.reduce((sum, s) => sum + (s.isSubStep ? 0 : s.duration || 0), 0);
      totalInputTokens = steps.reduce(
        (sum, s) => sum + (s.isSubStep ? 0 : s.tokens?.input || 0),
        0,
      );
      totalOutputTokens = steps.reduce(
        (sum, s) => sum + (s.isSubStep ? 0 : s.tokens?.output || 0),
        0,
      );
    }

    // Count completed steps (excluding the "Completed" summary step itself)
    const completedCount = steps.filter(
      (s) => s.status === 'completed' && s.step_type !== 'completed',
    ).length;
    const failedCount = steps.filter((s) => s.status === 'failed').length;

    // Access i18n messages for static rendering
    const locale = localStorage.getItem('app_language') || 'en-US';
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const appMessages = messages[locale as keyof typeof messages] as any;
    const pipelineTitle = appMessages?.pipelineSteps?.title || 'Pipeline Steps';
    const completedLabel = appMessages?.pipelineSteps?.completed || 'completed';
    const failedLabel = appMessages?.pipelineSteps?.failed || 'failed';

    let html = `
      <details class="pipeline-steps-details" style="
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px 16px;
        margin: 12px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        cursor: pointer;
      ">
        <summary style="
          list-style: none;
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 13px;
          font-weight: 500;
          user-select: none;
          outline: none;
        ">
          <span style="font-size: 16px;">📊</span>
          <span style="flex: 1;">
            ${pipelineTitle}
            <span style="opacity: 0.7; font-weight: 400; margin-left: 8px;">
              (${completedCount} ${completedLabel}${failedCount > 0 ? `, ${failedCount} ${failedLabel}` : ''})
            </span>
          </span>
          <span style="
            background: rgba(255, 255, 255, 0.1);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            opacity: 0.8;
          ">
            ${totalDuration.toFixed(2)}s
          </span>
          ${
            totalInputTokens > 0 || totalOutputTokens > 0
              ? `
          <span style="
            background: rgba(255, 255, 255, 0.1);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            opacity: 0.8;
          ">
            ↑${totalInputTokens} ↓${totalOutputTokens}
          </span>
          `
              : ''
          }
          <span class="expand-arrow" style="
            transition: transform 0.2s;
            font-size: 12px;
            opacity: 0.6;
          ">▼</span>
        </summary>

        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.1); display: flex; flex-direction: column; width: 100%;">
    `;

    // Render each step
    steps.forEach((step, index) => {
      const statusIcon = step.status === 'completed' ? '✓' : step.status === 'failed' ? '✕' : '⟳';
      const statusColor =
        step.status === 'completed' ? '#4caf50' : step.status === 'failed' ? '#f44336' : '#ff9800';

      const isSubStep = step.isSubStep || false;
      const opacity = isSubStep ? '0.7' : '1';
      const fontSize = isSubStep ? '12px' : '13px';
      const paddingLeft = isSubStep ? '20px' : '0';

      // Duration Text - Always show, even if 0
      const durationText = step.duration !== undefined ? `${step.duration.toFixed(2)}s` : '0.00s';

      // Tokens Text - Use up/down arrows
      let tokensText = '';
      if (step.tokens && (step.tokens.input > 0 || step.tokens.output > 0)) {
        tokensText = `↑${step.tokens.input || 0} ↓${step.tokens.output || 0}`;
      }

      html += `
        <div style="
          display: grid;
          grid-template-columns: 24px 1fr 60px 100px;
          align-items: center;
          gap: 8px;
          font-size: ${fontSize};
          margin-bottom: ${index < steps.length - 1 ? '8px' : '0'};
          padding-left: ${paddingLeft};
          opacity: ${opacity};
          width: 100%;
          box-sizing: border-box;
        ">
          <!-- 1. Icon -->
          <span style="
            color: ${statusColor};
            font-weight: bold;
            text-align: center;
          ">${statusIcon}</span>
          
          <!-- 2. Label -->
          <span 
            style="
              font-weight: ${isSubStep ? '400' : '500'};
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
              cursor: help;
            "
            title="${this.getStepDescription(step.step_type)}"
          >
            ${step.label}
          </span>

          <!-- 3. Duration (Fixed Width) -->
          <span style="
            text-align: right;
            font-family: monospace;
            font-size: 11px;
            opacity: 0.7;
          ">
            ${
              durationText
                ? `
              <span style="
                background: rgba(255, 255, 255, 0.08);
                padding: 2px 6px;
                border-radius: 6px;
                display: inline-block;
                min-width: 45px;
              ">${durationText}</span>
            `
                : ''
            }
          </span>

          <!-- 4. Tokens (Fixed Width) -->
          <span style="
            text-align: right;
            font-family: monospace;
            font-size: 11px;
            opacity: 0.7;
          ">
             ${
               tokensText
                 ? `
              <span style="
                background: rgba(255, 255, 255, 0.08);
                padding: 2px 6px;
                border-radius: 6px;
                display: inline-block;
                min-width: 60px;
              ">${tokensText}</span>
            `
                 : ''
             }
          </span>
          
          <!-- Sources (Optional - absolute positioned or just appened if we want? 
               Grid forbids extra items unless defined, or they wrap. 
               Let's keep it simple: Sources are rare in the summary, 
               but if they exist, we might need a 5th column or overlay.
               For now, let's add a 5th column just in case: minmax(0, auto) -->
        </div>
      `;
    });

    html += `
        </div>
      </details>

      <style>
        .pipeline-steps-details[open] .expand-arrow {
          transform: rotate(180deg);
        }
        .pipeline-steps-details:hover {
          background: rgba(255, 255, 255, 0.08);
        }
      </style>
    `;

    return html;
  }

  /**
   * Generates HTML for Sources with beautiful styling matching Pipeline Steps
   */
  static renderSources(sources: Source[]): string {
    if (!sources || sources.length === 0) return '';

    // Group sources by document/file
    const groups: Record<
      string,
      { fileName: string; documentId: string | undefined; items: Source[] }
    > = {};

    sources.forEach((source) => {
      const meta = source.metadata || {};
      const fileName = meta.file_name || meta.filename || meta.name || source.name || 'Unknown';
      const documentId = meta.connector_document_id;
      const key = documentId || fileName;

      if (!groups[key]) {
        groups[key] = { fileName, documentId, items: [] };
      }
      groups[key].items.push(source);
    });

    const fileCount = Object.keys(groups).length;
    const totalSources = sources.length;

    // Main expandable container with same styling as Pipeline Steps
    let html = `
      <details class="sources-details" style="
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px 16px;
        margin: 12px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        cursor: pointer;
      ">
        <summary style="
          list-style: none;
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 13px;
          font-weight: 500;
          user-select: none;
          outline: none;
        ">
          <span style="font-size: 16px;">📄</span>
          <span style="flex: 1;">
            Sources
            <span style="opacity: 0.7; font-weight: 400; margin-left: 8px;">
              (${totalSources} from ${fileCount} ${fileCount === 1 ? 'file' : 'files'})
            </span>
          </span>
          <span class="expand-arrow" style="
            transition: transform 0.2s;
            font-size: 12px;
            opacity: 0.6;
          ">▼</span>
        </summary>

        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
    `;

    // Render each file group
    Object.values(groups).forEach((group, groupIndex) => {
      const isAudioSource = group.items.some(
        (s) => s.type === 'audio' || s.metadata?.connector_type === 'audio',
      );

      html += `
        <div style="
          display: flex;
          align-items: flex-start;
          gap: 10px;
          margin-bottom: ${groupIndex < fileCount - 1 ? '12px' : '0'};
          padding: 8px;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 8px;
          border-left: 3px solid ${isAudioSource ? '#9c27b0' : '#2196f3'};
        ">
          <span style="
            min-width: 16px;
            text-align: center;
            font-size: 14px;
            margin-top: 2px;
          ">${isAudioSource ? '🎵' : '📄'}</span>
          
          <div style="flex: 1; min-width: 0;">
            <div style="
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 6px;
              flex-wrap: wrap;
            ">
              <span style="
                font-weight: 500;
                font-size: 13px;
                word-break: break-word;
              ">${group.fileName}</span>
              
              <span style="
                background: rgba(255, 255, 255, 0.1);
                padding: 2px 8px;
                border-radius: 8px;
                font-size: 11px;
                opacity: 0.8;
              ">${group.items.length} ${group.items.length === 1 ? 'excerpt' : 'excerpts'}</span>
              
              ${
                group.documentId
                  ? `
              <button 
                data-doc-id="${group.documentId}"
                onclick="window.dispatchEvent(new CustomEvent('vectra-open-file', {detail: '${group.documentId}'}))"
                style="
                  background: rgba(33, 150, 243, 0.2);
                  border: 1px solid rgba(33, 150, 243, 0.4);
                  color: #64b5f6;
                  padding: 2px 10px;
                  border-radius: 8px;
                  font-size: 11px;
                  cursor: pointer;
                  transition: all 0.2s;
                "
                onmouseover="this.style.background='rgba(33, 150, 243, 0.3)'"
                onmouseout="this.style.background='rgba(33, 150, 243, 0.2)'"
              >
                Open File
              </button>
              `
                  : ''
              }
            </div>
            
            <div style="
              display: flex;
              flex-direction: column;
              gap: 6px;
              font-size: 12px;
              opacity: 0.85;
            ">
              ${group.items
                .map((source) => {
                  const meta = source.metadata || {};

                  // Audio Source
                  if (source.type === 'audio' || meta.connector_type === 'audio') {
                    const fileId = meta.connector_document_id;
                    const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api/v1';
                    const audioUrl = fileId
                      ? `${baseUrl.replace(/\/$/, '')}/audio/stream/${fileId}`
                      : '';
                    const timestamp = meta.timestamp_start || '00:00';

                    return `
                      <div style="
                        background: rgba(0, 0, 0, 0.2);
                        padding: 8px;
                        border-radius: 6px;
                        border: 1px solid rgba(156, 39, 176, 0.3);
                      ">
                        <div style="
                          font-size: 11px;
                          color: #ce93d8;
                          margin-bottom: 4px;
                        ">⏱️ ${timestamp}</div>
                        ${
                          audioUrl
                            ? `<audio controls src="${audioUrl}" style="width: 100%; height: 32px;"></audio>`
                            : '<em style="color: #ef5350;">Audio unavailable</em>'
                        }
                      </div>
                    `;
                  }

                  // Text Source
                  const page = meta.page_label || meta.page_number || meta.page;
                  const content = source.content ? source.content.substring(0, 150) : '';

                  return `
                    <div style="
                      padding: 6px 8px;
                      background: rgba(0, 0, 0, 0.15);
                      border-radius: 4px;
                      border-left: 2px solid rgba(33, 150, 243, 0.4);
                    ">
                      ${
                        page
                          ? `<span style="
                        color: #64b5f6;
                        font-size: 11px;
                        margin-right: 6px;
                        font-weight: 500;
                      ">Page ${page}</span>`
                          : ''
                      }
                      <div style="
                        color: rgba(255, 255, 255, 0.75);
                        line-height: 1.4;
                        margin-top: ${page ? '4px' : '0'};
                      ">${content}${content.length >= 150 ? '...' : ''}</div>
                    </div>
                  `;
                })
                .join('')}
            </div>
          </div>
        </div>
      `;
    });

    html += `
        </div>
      </details>

      <style>
        .sources-details[open] .expand-arrow {
          transform: rotate(180deg);
        }
        .sources-details:hover {
          background: rgba(255, 255, 255, 0.08);
        }
      </style>
    `;

    return html;
  }
}
