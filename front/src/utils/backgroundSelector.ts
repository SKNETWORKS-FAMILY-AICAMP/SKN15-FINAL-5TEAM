import { getScenarioBackgrounds } from '@/config/backgroundImages';

type DialogueLike = { text?: string; content?: string };

const normalize = (text: string) => text.toLowerCase();

const tokenize = (text: string) =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9가-힣_]+/g, ' ')
    .split(' ')
    .filter(Boolean);

const speakerDefaults: Record<string, string> = {
  tanjiro: '탄지로_기본.png',
  rengoku: '렌고쿠_기본.png',
  akaza: '아카자_기본.png',
  inosuke: '이노스케_기본.png',
  zenitsu: '젠이츠_기본.png',
  nezuko: '네즈코_기본.png',
  giyu: '기유_기본.png',
  shinobu: '시노부_기본.png'
};

const pickSpeakerDefault = (scenario: ReturnType<typeof getScenarioBackgrounds>, dialogues?: DialogueLike[]) => {
  if (!dialogues || !scenario) return null;

  // scenario 내에서만 기본컷을 선택하도록 제한
  const available = new Set((scenario.backgrounds || []).map(bg => bg.fileName));

  const counts: Record<string, number> = {};
  dialogues.forEach(d => {
    // speaker 정보는 ChatInterface에서 message.characterId로 전달되지만
    // 여기서는 text/content만 넘어오므로 패턴 매칭으로 추정
    const raw = (d as any).speaker || '';
    const speaker = String(raw || '').toLowerCase();
    if (!speaker) return;
    counts[speaker] = (counts[speaker] || 0) + 1;
  });

  // 최빈 speaker부터 기본 배경을 찾음
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  for (const [sp] of sorted) {
    const candidate = speakerDefaults[sp];
    if (candidate && available.has(candidate)) return candidate;
  }
  return null;
};

export function selectBestBackgroundByDialogue(
  scenarioId: string,
  dialogues?: DialogueLike[],
  stageTag?: string
): string | null {
  const scenario = getScenarioBackgrounds(scenarioId);
  if (!scenario) return null;

  const combinedText = normalize(
    (dialogues || [])
      .map(d => d.text || d.content || '')
      .join(' ')
  );
  const combinedTokens = new Set(tokenize(combinedText));

  let bestFile: string | null = null;
  let bestScore = 0;

  scenario.backgrounds.forEach(bg => {
    let score = 0;

    // tags 우선
    (bg.tags || []).forEach(tag => {
      if (combinedText.includes(tag.toLowerCase())) {
        score += 3;
      }
    });

    // 파일명/이름/설명 토큰 매칭
    const nameTokens = tokenize(bg.name || '');
    nameTokens.forEach(tok => {
      if (combinedTokens.has(tok)) {
        score += 1;
      }
    });
    const descTokens = tokenize(bg.description || '');
    descTokens.forEach(tok => {
      if (combinedTokens.has(tok)) {
        score += 1;
      }
    });

    // stageTag가 id와 일치하면 약한 페널티/보너스 (tie-breaker 용)
    if (stageTag && bg.id && bg.id.toLowerCase().includes(stageTag.toLowerCase())) {
      score += 1;
    }

    // 기본값: 스코어가 같으면 낮은 index 우선
    if (score > bestScore || (score === bestScore && bestFile && bg.index < scenario.backgrounds.find(b => b.fileName === bestFile)?.index!)) {
      bestScore = score;
      bestFile = bg.fileName;
    }
  });

  // 점수가 없으면 발화자 기반 기본 배경 사용
  const speakerDefault = pickSpeakerDefault(scenario, dialogues);
  if (speakerDefault) return speakerDefault;

  // 그래도 없으면 시나리오 기본 배경 사용
  const defaultBg = scenario?.backgrounds?.[0]?.fileName;
  return defaultBg || null;
}
