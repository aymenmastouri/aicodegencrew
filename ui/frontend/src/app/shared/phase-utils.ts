/**
 * Canonical mapping from phase IDs (both long and short forms) to display names.
 * Source of truth: config/phases_config.yaml
 */
const PHASE_DISPLAY_NAMES: Record<string, string> = {
  // Long form (phases_config.yaml keys)
  phase0_indexing: 'Repository Indexing',
  phase1_architecture_facts: 'Architecture Facts Extraction',
  phase2_architecture_analysis: 'Architecture Analysis',
  phase3_architecture_synthesis: 'Architecture Synthesis',
  phase4_development_planning: 'Development Planning',
  phase5_code_generation: 'Code Generation',
  phase6_test_generation: 'Test Generation',
  phase7_review_deploy: 'Review & Deploy',
  // Short form (used in pipeline executor / presets)
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
