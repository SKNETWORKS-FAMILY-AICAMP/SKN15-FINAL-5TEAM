// 시나리오별 캐릭터 목록 (scenario_id의 character_refs 기반)
// 특정 캐릭터 제외(예: 악역)를 손쉽게 관리할 수 있도록 exclude 지원

const GLOBAL_EXCLUDED = new Set(['akaza', 'enmu', 'kasugai_crow']);

const scenarioCharacters: Record<
  string,
  { characters: string[]; exclude?: string[] }
> = {
  'mugen-train': {
    // data/scenarios/mugen-train.json 의 character_refs 키에서 가져옴
    characters: ['rengoku', 'tanjiro', 'akaza', 'zenitsu', 'inosuke', 'nezuko', 'enmu'],
    exclude: ['akaza', 'enmu']
  },
  'counseling': {
    // data/scenarios/counseling.json 의 character_refs 키에서 가져옴
    characters: ['tanjiro', 'zenitsu', 'inosuke', 'nezuko', 'rengoku', 'giyu', 'shinobu']
  }
};

const normalizeId = (id: string) => id.trim().toLowerCase();

export function filterExcludedCharacters(ids: string[]): string[] {
  const unique = Array.from(new Set(ids.map(id => normalizeId(id))));
  return unique.filter(id => !GLOBAL_EXCLUDED.has(id));
}

export function getScenarioCharacters(scenarioId: string): string[] {
  if (!scenarioId) return [];
  const normalized = normalizeId(scenarioId).replace(/_/g, '-');
  const config = scenarioCharacters[normalized];
  if (!config) return [];

  const excluded = new Set([...(config.exclude ?? []), ...GLOBAL_EXCLUDED]);
  return config.characters
    .map(id => normalizeId(id))
    .filter(id => !excluded.has(id));
}
