const CANONICAL_SCENARIO_ID = 'mugen-train';

const SCENARIO_ALIAS_SET = new Set([
  CANONICAL_SCENARIO_ID,
  'mugen_train_full',
  'mugentrainfull',
  'cutscene5_llm_driven',
  'cutscene5-llm-driven',
  'ending'
]);

export const normalizeScenarioId = (rawId?: string): string => {
  if (!rawId) {
    return CANONICAL_SCENARIO_ID;
  }

  const normalized = rawId.trim().toLowerCase().replace(/_/g, '-');
  if (!normalized) {
    return CANONICAL_SCENARIO_ID;
  }

  if (SCENARIO_ALIAS_SET.has(normalized)) {
    return CANONICAL_SCENARIO_ID;
  }

  return normalized;
};
