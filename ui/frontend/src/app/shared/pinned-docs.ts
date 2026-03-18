/** Pinned documents stored in localStorage. */
export interface PinnedDocs {
  runId: string;
  pipelineRunId: string | null;
  startedAt: string | null;
  pinnedAt: string;
}

export const PINNED_DOCS_KEY = 'knowledge_pinned_docs';
