/**
 * Canonical mapping from phase IDs (both long and short forms) to display names.
 * Source of truth: config/phases_config.yaml
 */
const PHASE_DISPLAY_NAMES: Record<string, string> = {
  // New canonical IDs
  discover: 'Discover',
  extract: 'Extract',
  analyze: 'Analyze',
  document: 'Document',
  plan: 'Plan',
  implement: 'Implement',
  verify: 'Verify',
  deliver: 'Deliver',
  // Legacy long form (backwards compat for historical data)
  phase0_indexing: 'Repository Indexing',
  phase1_architecture_facts: 'Architecture Facts Extraction',
  phase2_architecture_analysis: 'Architecture Analysis',
  phase3_architecture_synthesis: 'Architecture Synthesis',
  phase4_development_planning: 'Development Planning',
  phase5_code_generation: 'Code Generation',
  phase6_test_generation: 'Test Generation',
  phase7_review_deploy: 'Review & Deploy',
  // Legacy short form (backwards compat for historical data)
  indexing: 'Repository Indexing',
  facts_extraction: 'Architecture Facts Extraction',
  deep_analysis: 'Architecture Analysis',
  synthesis: 'Architecture Synthesis',
  planning: 'Development Planning',
  code_generation: 'Code Generation',
  test_generation: 'Test Generation',
  review_deploy: 'Review & Deploy',
};

/**
 * Convert a phase ID to a human-readable display name.
 * Falls back to title-casing the ID if not found in the map.
 */
export function humanizePhaseId(phaseId: string): string {
  if (!phaseId) return '';
  const known = PHASE_DISPLAY_NAMES[phaseId];
  if (known) return known;
  // Fallback: strip "phaseN_" prefix, replace _ with space, title case
  return phaseId
    .replace(/^phase\d+_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Short compact labels for phase chips (e.g. "Discover", "Extract"). */
const SHORT_PHASE_LABELS: Record<string, string> = {
  // New canonical IDs
  discover: 'Discover',
  extract: 'Extract',
  analyze: 'Analyze',
  document: 'Document',
  plan: 'Plan',
  implement: 'Implement',
  verify: 'Verify',
  deliver: 'Deliver',
  // Legacy long form
  phase0_indexing: 'Index',
  phase1_architecture_facts: 'Facts',
  phase2_architecture_analysis: 'Analysis',
  phase3_architecture_synthesis: 'Synthesis',
  phase4_development_planning: 'Planning',
  phase5_code_generation: 'CodeGen',
  phase6_test_generation: 'TestGen',
  phase7_review_deploy: 'Deploy',
  // Legacy short form
  indexing: 'Index',
  facts_extraction: 'Facts',
  deep_analysis: 'Analysis',
  synthesis: 'Synthesis',
  planning: 'Planning',
  code_generation: 'CodeGen',
  test_generation: 'TestGen',
  review_deploy: 'Deploy',
};

/** Convert phase ID to compact label for chips and small UI elements. */
export function shortPhase(phaseId: string): string {
  return SHORT_PHASE_LABELS[phaseId] || phaseId.replace(/^phase\d+_/, '').replace(/_/g, ' ').slice(0, 10);
}

/** Format seconds to human-readable duration (e.g. "2m 30s"). */
export function formatDuration(seconds?: number): string {
  if (!seconds) return '0s';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const min = Math.floor(seconds / 60);
  const sec = Math.round(seconds % 60);
  return sec > 0 ? `${min}m ${sec}s` : `${min}m`;
}

/** Format bytes to human-readable size (e.g. "1.5 MB"). */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Format a large number compactly (e.g. 1500 → "1.5K", 1500000 → "1.5M"). */
export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return `${n}`;
}
