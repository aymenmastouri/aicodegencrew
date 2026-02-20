/**
 * Central status definitions. Mirror of pipeline_contract.py.
 * RULE: Add new status here first, then in Python.
 */

export const PHASE_STATUS = {
  RUNNING: 'running',
  COMPLETED: 'completed',
  PARTIAL: 'partial',
  SKIPPED: 'skipped',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const;

export const DISPLAY_STATUS = {
  IDLE: 'idle',
  READY: 'ready',
  PLANNED: 'planned',
} as const;

export type PhaseStatusValue = (typeof PHASE_STATUS)[keyof typeof PHASE_STATUS];
export type DisplayStatusValue = (typeof DISPLAY_STATUS)[keyof typeof DISPLAY_STATUS];
export type AnyStatusValue = PhaseStatusValue | DisplayStatusValue;

/** Status -> Material icon. */
export function statusIcon(status: string): string {
  switch (status) {
    case 'completed':
      return 'check_circle';
    case 'partial':
      return 'warning';
    case 'running':
      return 'sync';
    case 'failed':
      return 'error';
    case 'skipped':
      return 'check_circle';
    case 'cancelled':
      return 'cancel';
    default:
      return 'radio_button_unchecked';
  }
}

/** Human-readable label. */
export function statusLabel(status: string): string {
  switch (status) {
    case 'skipped':
      return 'up to date';
    case 'planned':
      return 'not available';
    default:
      return status;
  }
}

/** Whether status is terminal (phase done). */
export function isTerminal(status: string): boolean {
  return ['completed', 'partial', 'skipped', 'failed', 'cancelled'].includes(status);
}

/** Whether status counts as successful. */
export function isSuccess(status: string): boolean {
  return ['completed', 'partial', 'skipped'].includes(status);
}
