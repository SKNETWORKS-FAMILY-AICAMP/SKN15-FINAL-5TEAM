
import { useState, useEffect, useRef, useMemo } from 'react';
import CharacterSelectionModal from './CharacterSelectionModal';
import BubbleCounter from './BubbleCounter';
import AffinityPanel from './AffinityPanel';
import MemoryUpdateLog from './MemoryUpdateLog';
import { sendChatMessage, ChatResponse, MemoryEvent } from '@/services/api';
import { useBackgroundImage } from '@/hooks/useBackgroundImage';
import { useSoundEffects } from '@/hooks/useSoundEffects';
import { useApp } from '@/contexts/AppContext';
import { normalizeScenarioId } from '@/utils/scenario';

const CDN_URL = import.meta.env.VITE_CDN_URL || '/images';

interface Message {
  id: number;
  text: string;
  isUser: boolean;
  timestamp: Date;
  characterId?: string; // 메시지를 보낸 캐릭터 ID
  isSystemMessage?: boolean; // 시스템/에이전트 메시지 여부
  imageIndex?: string; // 이 메시지가 표시될 때 변경할 배경 이미지 인덱스
}

interface ChatInterfaceProps {
  onUserLogin?: (username: string) => void;
  onMessageSent?: () => void;
  characterId?: string;
  initialSessionId?: string;  // 세션 복원용 session_id
  onInvitedCharactersChange?: (characters: string[]) => void;  // 참여 캐릭터 변경 콜백
  sessionCheckDone?: boolean;  // 세션 체크 완료 여부 (모달에서 사용자 선택 완료)
  onSessionStart?: (sessionId: string) => void;  // 세션 시작 시 콜백 (세션 종료를 위해)
}

const TYPING_INTERVAL_MS = 10; // 타이핑 애니메이션 속도 (값이 클수록 느려짐) - Phase 1 개선: 60 → 10 (6배 빠르게)

// Placeholder 치환 함수: 백엔드에서 렌더링되지 않은 {admin}, {user} 등을 실제 값으로 변환
const replacePlaceholders = (text: string, userName?: string): string => {
  if (!text) return text;

  const name = userName || '츠구코';

  // 1. 이중 중괄호 {{user}} 형태 처리
  let result = text
    .replace(/\{\{user\}\}/g, name)
    .replace(/\{\{user_name\}\}/g, name);

  // 2. 단일 중괄호 {user}, {Administrator} 등 모든 형태 처리
  // {단어} 형태를 사용자 이름으로 치환 (일반적으로 사용자 이름을 의미)
  result = result.replace(/\{([A-Za-z가-힣0-9_]+)\}/g, name);

  return result;
};

export default function ChatInterface({
  onUserLogin,
  onMessageSent,
  characterId = 'ending',
  initialSessionId,
  onInvitedCharactersChange,
  sessionCheckDone = true,  // 기본값: true (기존 동작 유지)
  onSessionStart
}: ChatInterfaceProps) {
  // App context (for bubble consumption and user info)
  const { consumeBubbles, currentUser, openMyAccount } = useApp();

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [showCharacterModal, setShowCharacterModal] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [invitedCharacters, setInvitedCharacters] = useState<string[]>([]); // 현재 참여중인 캐릭터들 (백엔드 응답에서 동기화)
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);  // 세션 복원 지원
  const [isLoading, setIsLoading] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false); // 타이핑 중 표시
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null); // 로딩 메시지
  const [isAutoRequesting, setIsAutoRequesting] = useState(false); // 자동 요청 중
  const autoRequestTimerRef = useRef<number | null>(null); // 자동 요청 타이머
  const shouldCancelAutoRequest = useRef(false); // 사용자 중단 플래그
  const messageIdCounter = useRef(0); // 고유한 메시지 ID 생성용 카운터
  const isAddingMessages = useRef(false); // 메시지 추가 중 플래그 (중복 방지)
  const isSendingRef = useRef(false); // 메시지 전송 중 플래그 (중복 전송 방지)
  const [affinityScores, setAffinityScores] = useState<Record<string, number>>({}); // 친밀도
  const [isTransitioning, setIsTransitioning] = useState(false); // 컷신 전환 효과
  const [isEnded, setIsEnded] = useState(false); // Phase 4: 시나리오 종료 여부
  const [currentStage, setCurrentStage] = useState<string | undefined>(undefined); // 현재 스테이지 (INTRO 판별용)
  const [showEndingReward, setShowEndingReward] = useState(false); // 엔딩 보상 모달 표시 여부
  const [endingSummary, setEndingSummary] = useState<string>(''); // 대화 요약
  const [memoryEvents, setMemoryEvents] = useState<Array<MemoryEvent & { id: string; timestamp: number }>>([]); // 메모리 이벤트 히스토리

  // Skip 기능을 위한 ref
  const typingIntervalRef = useRef<NodeJS.Timeout | null>(null); // 현재 타이핑 interval
  const pendingMessagesRef = useRef<Message[]>([]); // Skip 시 즉시 표시할 남은 메시지들
  const shouldSkip = useRef(false); // Skip 플래그

  // 가장 최근 메시지 ID 계산 (모든 메시지 포함 - 시스템/나레이션/사용자/AI 모두)
  // 단, 첫 메시지는 확대하지 않음 (겹침 방지)
  const latestMessageId = useMemo(() => {
    // 메시지가 2개 이상일 때만 마지막 메시지 확대
    if (messages.length > 1) {
      return messages[messages.length - 1].id;
    }
    return null;
  }, [messages]);

  // 백엔드 시나리오 ID 결정 (매핑 적용)
  const backendScenarioId = useMemo(() => normalizeScenarioId(characterId), [characterId]);

  // 배경 이미지 관리 (시나리오별 배경 이미지)
  const {
    currentBackground,
    backgroundImageUrl,
    setBackgroundById,
    setBackgroundByIndex,
    setBackgroundByFileName,
    preloadImages
  } = useBackgroundImage(backendScenarioId);

  // 소리 효과 관리 (몰입감 향상)
  const {
    playMessageSound,
    playSystemSound,
    playTypingStartSound,
    unlockAudio
  } = useSoundEffects();

  // 배경 이미지 프리로드 (성능 최적화)
  useEffect(() => {
    preloadImages();
  }, [preloadImages]);

  // 세션 히스토리 로드 (이전 대화 이어하기)
  useEffect(() => {
    if (initialSessionId && messages.length === 0) {
      console.log('[ChatInterface] Loading session history:', initialSessionId);

      const loadHistory = async () => {
        try {
          const { apiClient } = await import('@/services/api');
          const dialogues = await apiClient.getSessionDialogues(initialSessionId, 100);

          if (dialogues && dialogues.length > 0) {
            console.log(`[ChatInterface] Loaded ${dialogues.length} messages from history`);

            // 현재 로그인한 사용자의 이름 가져오기
            const userName = currentUser || '';

            // 시스템/나레이터 speaker 목록
            const systemSpeakers = new Set(['narr', 'system']);

            const historyMessages: Message[] = dialogues.map((d, idx) => {
              // speaker가 현재 사용자 이름과 일치하면 유저 메시지
              const isUserMessage = d.speaker === userName;
              const isSystemMsg = systemSpeakers.has(d.speaker);

              return {
                id: messageIdCounter.current++,
                text: d.text,
                isUser: isUserMessage,  // speaker가 사용자 이름과 일치하는지 확인
                timestamp: d.timestamp ? new Date(d.timestamp) : new Date(),
                characterId: d.speaker,
                isSystemMessage: isSystemMsg
              };
            });

            console.log('[ChatInterface] 🔍 History messages (userName:', userName, '):');
            historyMessages.forEach((m, idx) => {
              console.log(`  [${idx}] ${m.isUser ? 'USER' : 'NPC '} ${m.characterId}: ${m.text.substring(0, 50)}`);
            });

            setMessages(historyMessages);
          }
        } catch (error) {
          console.error('[ChatInterface] Failed to load session history:', error);
        }
      };

      loadHistory();
    }
  }, [initialSessionId, currentUser]);

  // 배경 이미지 변경 추적 (디버깅)
  useEffect(() => {
    if (currentBackground) {
      console.log(`🎨 Background changed to: index=${currentBackground.index}, fileName=${currentBackground.fileName}`);
      console.log(`🎨 Background URL:`, backgroundImageUrl);
    }
  }, [currentBackground, backgroundImageUrl]);

  // 참여 중인 캐릭터 변경 시 부모 컴포넌트에 알림
  useEffect(() => {
    if (onInvitedCharactersChange) {
      onInvitedCharactersChange(invitedCharacters);
    }
  }, [invitedCharacters, onInvitedCharactersChange]);

  // 캐릭터 순서 우선순위 정의 (일관된 순서 유지)
  const characterOrder: Record<string, number> = {
    tanjiro: 1,
    nezuko: 2,
    zenitsu: 3,
    inosuke: 4,
    rengoku: 5,
    shinobu: 6,
  };

  // 참여 캐릭터 업데이트 헬퍼 함수
  const updateInvitedCharacters = (
    dialogues: Array<{ speaker?: string }>,
    shouldAccumulate: boolean = false // has_more 처리 중에는 true
  ) => {
    // dialogues에서 실제 발언한 캐릭터들 추출
    const newParticipants = Array.from(
      new Set(
        dialogues
          .map(d => d.speaker)
          .filter(speaker => speaker && speaker !== 'system' && speaker !== 'narr')
      )
    );

    // 디버깅: speaker 값 로깅
    if (newParticipants.length > 0) {
      console.log('🎭 Detected participants from dialogues:', newParticipants);
    }

    // 빈 응답 처리: 새 캐릭터가 없으면 이전 상태 유지
    if (newParticipants.length === 0) {
      console.log('⚠️ No new participants found, keeping previous state');
      return;
    }

    // has_more 처리 중이면 기존 캐릭터와 합침 (깜빡임 방지)
    const finalParticipants = shouldAccumulate
      ? Array.from(new Set([...invitedCharacters, ...newParticipants]))
      : newParticipants;

    // 일관된 순서로 정렬 (우선순위 기준)
    const sortedParticipants = finalParticipants.sort((a, b) => {
      const orderA = characterOrder[a?.toLowerCase() ?? ''] ?? 999;
      const orderB = characterOrder[b?.toLowerCase() ?? ''] ?? 999;
      return orderA - orderB;
    }).filter((char): char is string => char !== undefined);

    console.log('✅ Updated invited characters:', sortedParticipants);
    setInvitedCharacters(sortedParticipants);
  };

  // 백엔드 응답에서 받은 current_image를 처리하여 배경 변경 (페이드 효과 포함)
  const extractFileName = (value: string) => {
    if (!value) return '';
    const cleaned = value.replace(/^["']|["']$/g, '');
    const noQuery = cleaned.split(/[?#]/)[0];
    const decoded = decodeURIComponent(noQuery);
    const parts = decoded.split(/[/\\]/);
    return parts[parts.length - 1] || decoded;
  };

  const getFileNameCandidates = (raw: string) => {
    const candidates = new Set<string>();
    const direct = extractFileName(raw);
    if (raw) candidates.add(raw);
    if (direct) candidates.add(direct);
    return Array.from(candidates).filter(name => /\.[a-z0-9]+$/i.test(name));
  };

  const handleBackgroundChange = (currentImage: string | null) => {
    if (!currentImage) return;

    console.log(`🖼️ handleBackgroundChange called with: "${currentImage}"`);

    // 전환 효과 시작
    setIsTransitioning(true);

    // 500ms 후에 배경 변경
    setTimeout(() => {
      const trimmed = currentImage.trim();
      let handled = false;

      const fileNameCandidates = getFileNameCandidates(trimmed);
      for (const fileName of fileNameCandidates) {
        if (!fileName) continue;
        if (setBackgroundByFileName(fileName)) {
          handled = true;
          break;
        }
      }

      if (!handled) {
        const indexNum = Number(trimmed);
        if (!Number.isNaN(indexNum) && indexNum >= 0) {
          handled = setBackgroundByIndex(indexNum);
        }
      }

      if (!handled) {
        handled = setBackgroundById(trimmed);
      }

      if (!handled) {
        console.warn(`[ChatInterface] Unknown background identifier: ${trimmed}`);
      } else {
        console.log(`  → Background updated using identifier: ${trimmed}`);
      }

      // 전환 효과 종료
      setIsTransitioning(false);
    }, 500);
  };

  // 캐릭터별 프로필 이미지 매핑 (패턴 기반 매칭)
  const getCharacterProfile = (charId: string) => {
    const lowerCharId = charId.toLowerCase();

    // 1. 주요 캐릭터 패턴 매칭 (정확한 이름이 아니어도 포함되면 매칭)
    if (lowerCharId.includes('tanjiro') || lowerCharId.includes('tanjirou') || lowerCharId.includes('탄지로')) {
      return `${CDN_URL}/프로필_탄지로.png`;
    }
    if (lowerCharId.includes('rengoku') || lowerCharId.includes('렌고쿠')) {
      return `${CDN_URL}/프로필_렌고쿠.png`;
    }
    if (lowerCharId.includes('zenitsu') || lowerCharId.includes('젠이츠')) {
      return `${CDN_URL}/프로필_젠이츠.png`;
    }
    if (lowerCharId.includes('inosuke') || lowerCharId.includes('이노스케')) {
      return `${CDN_URL}/프로필_이노스케.png`;
    }
    if (lowerCharId.includes('nezuko') || lowerCharId.includes('네즈코')) {
      return `${CDN_URL}/프로필_네즈코.png`;
    }
    if (lowerCharId.includes('giyu') || lowerCharId.includes('기유')) {
      return `${CDN_URL}/프로필_기유.png`;
    }
    if (lowerCharId.includes('shinobu') || lowerCharId.includes('시노부')) {
      return `${CDN_URL}/프로필_시노부.png`;
    }
    if (lowerCharId.includes('akaza') || lowerCharId.includes('아카자')) {
      return `${CDN_URL}/프로필_아카자.png`;
    }
    if (lowerCharId.includes('enmu') || lowerCharId.includes('엔무')) {
      return `${CDN_URL}/프로필_엔무.png`;
    }

    // 2. 시스템/특수 캐릭터
    if (lowerCharId.includes('user') || lowerCharId.includes('플레이어')) {
      return `${CDN_URL}/기본이미지.png`;
    }
    if (lowerCharId.includes('system') || lowerCharId.includes('narr') || lowerCharId.includes('내레이터')) {
      return `${CDN_URL}/기본이미지.png`;
    }
    if (lowerCharId.includes('kasugai') || lowerCharId.includes('crow') || lowerCharId.includes('까마귀')) {
      return `${CDN_URL}/꺾쇠_까마귀.png`;
    }

    // 3. 역무원/차장 관련
    if (lowerCharId.includes('conductor') || lowerCharId.includes('역무원') || lowerCharId.includes('차장') ||
        lowerCharId.includes('station')) {
      return `${CDN_URL}/역무원.jpg`;
    }

    // 4. 여성 캐릭터 관련 (woman을 man보다 먼저 체크 - 충돌 방지)
    if (lowerCharId.includes('woman') || lowerCharId.includes('여자') || lowerCharId.includes('여성') ||
        lowerCharId.includes('female') || lowerCharId.includes('girl')) {
      return `${CDN_URL}/일반인_여성.png`;
    }

    // 5. 남성 캐릭터 관련
    if (lowerCharId.includes('man') || lowerCharId.includes('남자') || lowerCharId.includes('남성') ||
        lowerCharId.includes('male') || lowerCharId.includes('boy')) {
      return `${CDN_URL}/일반인_남성.png`;
    }

    // 6. 승객 관련 (passenger, 승객 포함) - 기본 남성으로
    if (lowerCharId.includes('passenger') || lowerCharId.includes('승객')) {
      return `${CDN_URL}/일반인_남성.png`;
    }

    // 7. NPC 관련 - 기본 남성으로
    if (lowerCharId.includes('npc') || lowerCharId.includes('일반인')) {
      return `${CDN_URL}/일반인_남성.png`;
    }

    // 8. 기본 이미지로 폴백
    return `${CDN_URL}/기본이미지.png`;
  };

  // 캐릭터별 화자 이름 매핑 (패턴 기반 매칭)
  const getCharacterName = (charId: string) => {
    const lowerCharId = charId.toLowerCase();

    // 1. 주요 캐릭터 패턴 매칭 (이름이 포함되면 매칭)
    if (lowerCharId.includes('tanjiro') || lowerCharId.includes('tanjirou') || lowerCharId.includes('탄지로')) {
      return '탄지로';
    }
    if (lowerCharId.includes('rengoku') || lowerCharId.includes('렌고쿠')) {
      return '렌고쿠';
    }
    if (lowerCharId.includes('zenitsu') || lowerCharId.includes('젠이츠')) {
      return '젠이츠';
    }
    if (lowerCharId.includes('inosuke') || lowerCharId.includes('이노스케')) {
      return '이노스케';
    }
    if (lowerCharId.includes('nezuko') || lowerCharId.includes('네즈코')) {
      return '네즈코';
    }
    if (lowerCharId.includes('giyu') || lowerCharId.includes('기유')) {
      return '기유';
    }
    if (lowerCharId.includes('shinobu') || lowerCharId.includes('시노부')) {
      return '시노부';
    }
    if (lowerCharId.includes('akaza') || lowerCharId.includes('아카자')) {
      return '아카자';
    }
    if (lowerCharId.includes('enmu') || lowerCharId.includes('엔무')) {
      return '엔무';
    }

    // 2. 시스템/특수 캐릭터
    if (lowerCharId.includes('user') || lowerCharId.includes('플레이어')) {
      return currentUser || 'Player';  // 로그인한 사용자 이름 표시
    }
    if (lowerCharId.includes('system') || lowerCharId.includes('narr') || lowerCharId.includes('내레이터')) {
      return '내레이터';
    }
    if (lowerCharId.includes('kasugai') || lowerCharId.includes('crow') || lowerCharId.includes('까마귀')) {
      return '꺾쇠까마귀';
    }

    // 3. 역무원/차장 관련
    if (lowerCharId.includes('conductor') || lowerCharId.includes('차장')) {
      return '차장';
    }
    if (lowerCharId.includes('station') || lowerCharId.includes('역무원')) {
      return '역무원';
    }

    // 4. 승객 관련
    if (lowerCharId.includes('passenger') || lowerCharId.includes('승객')) {
      return '승객';
    }

    // 5. 일반 NPC 관련
    if (lowerCharId.includes('npc') || lowerCharId.includes('일반인')) {
      return '일반인';
    }

    // 6. 여성/남성 관련 (woman을 man보다 먼저 체크)
    if (lowerCharId.includes('woman') || lowerCharId.includes('여자') || lowerCharId.includes('여성') ||
        lowerCharId.includes('female') || lowerCharId.includes('girl')) {
      return '승객';
    }
    if (lowerCharId.includes('man') || lowerCharId.includes('남자') || lowerCharId.includes('남성') ||
        lowerCharId.includes('male') || lowerCharId.includes('boy')) {
      return '승객';
    }

    // 7. ID 그대로 반환
    return charId;
  };

  // 캐릭터별 글로우 색상 매핑 (패턴 기반 매칭)
  const getCharacterGlowColor = (charId: string) => {
    const lowerCharId = charId.toLowerCase();

    // 1. 주요 캐릭터 패턴 매칭 (이름이 포함되면 매칭)
    if (lowerCharId.includes('tanjiro') || lowerCharId.includes('tanjirou') || lowerCharId.includes('탄지로')) {
      return {
        primary: '#EF4444',
        shadow: 'rgba(239, 68, 68, 0.6)',
        bg: 'linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03))'
      };
    }
    if (lowerCharId.includes('rengoku') || lowerCharId.includes('렌고쿠')) {
      return {
        primary: '#F59E0B',
        shadow: 'rgba(245, 158, 11, 0.6)',
        bg: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03))'
      };
    }
    if (lowerCharId.includes('zenitsu') || lowerCharId.includes('젠이츠')) {
      return {
        primary: '#FBBF24',
        shadow: 'rgba(251, 191, 36, 0.6)',
        bg: 'linear-gradient(135deg, rgba(251, 191, 36, 0.08), rgba(251, 191, 36, 0.03))'
      };
    }
    if (lowerCharId.includes('inosuke') || lowerCharId.includes('이노스케')) {
      return {
        primary: '#10B981',
        shadow: 'rgba(16, 185, 129, 0.6)',
        bg: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.03))'
      };
    }
    if (lowerCharId.includes('nezuko') || lowerCharId.includes('네즈코')) {
      return {
        primary: '#EC4899',
        shadow: 'rgba(236, 72, 153, 0.6)',
        bg: 'linear-gradient(135deg, rgba(236, 72, 153, 0.08), rgba(236, 72, 153, 0.03))'
      };
    }
    if (lowerCharId.includes('giyu') || lowerCharId.includes('기유')) {
      return {
        primary: '#3B82F6',
        shadow: 'rgba(59, 130, 246, 0.6)',
        bg: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(59, 130, 246, 0.03))'
      };
    }
    if (lowerCharId.includes('shinobu') || lowerCharId.includes('시노부')) {
      return {
        primary: '#8B5CF6',
        shadow: 'rgba(139, 92, 246, 0.6)',
        bg: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08), rgba(139, 92, 246, 0.03))'
      };
    }
    if (lowerCharId.includes('akaza') || lowerCharId.includes('아카자')) {
      return {
        primary: '#A855F7',
        shadow: 'rgba(168, 85, 247, 0.6)',
        bg: 'linear-gradient(135deg, rgba(168, 85, 247, 0.08), rgba(168, 85, 247, 0.03))'
      };
    }
    if (lowerCharId.includes('enmu') || lowerCharId.includes('엔무')) {
      return {
        primary: '#7C3AED',
        shadow: 'rgba(124, 58, 237, 0.6)',
        bg: 'linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(124, 58, 237, 0.03))'
      };
    }

    // 2. 시스템/특수 캐릭터
    if (lowerCharId.includes('user') || lowerCharId.includes('플레이어')) {
      return {
        primary: '#F97316',
        shadow: 'rgba(249, 115, 22, 0.6)',
        bg: 'linear-gradient(135deg, rgba(249, 115, 22, 0.08), rgba(249, 115, 22, 0.03))'
      };
    }

    // 3. 역무원/차장 관련 - 중립 회색
    if (lowerCharId.includes('conductor') || lowerCharId.includes('station') ||
        lowerCharId.includes('역무원') || lowerCharId.includes('차장')) {
      return {
        primary: '#6B7280',
        shadow: 'rgba(107, 114, 128, 0.5)',
        bg: 'linear-gradient(135deg, rgba(107, 114, 128, 0.06), rgba(107, 114, 128, 0.02))'
      };
    }

    // 4. 승객, NPC, 일반인 관련 - 밝은 회색 (woman을 man보다 먼저 체크)
    if (lowerCharId.includes('passenger') || lowerCharId.includes('npc') ||
        lowerCharId.includes('woman') || lowerCharId.includes('man') ||
        lowerCharId.includes('승객') || lowerCharId.includes('일반인') ||
        lowerCharId.includes('male') || lowerCharId.includes('female') ||
        lowerCharId.includes('남자') || lowerCharId.includes('여자') ||
        lowerCharId.includes('남성') || lowerCharId.includes('여성') ||
        lowerCharId.includes('boy') || lowerCharId.includes('girl')) {
      return {
        primary: '#9CA3AF',
        shadow: 'rgba(156, 163, 175, 0.4)',
        bg: 'linear-gradient(135deg, rgba(156, 163, 175, 0.05), rgba(156, 163, 175, 0.02))'
      };
    }

    // 5. 기본 색상으로 폴백
    return {
      primary: '#6B7280',
      shadow: 'rgba(107, 114, 128, 0.4)',
      bg: 'linear-gradient(135deg, rgba(107, 114, 128, 0.05), rgba(107, 114, 128, 0.02))'
    };
  };

  // 캐릭터별 대사 생성 로딩 메시지 (각 캐릭터당 3개씩)
  const getRandomLoadingMessage = () => {
    const loadingMessages = [
      // 탄지로 (3개) - 후각에 특화
      '탄지로가 냄새를 맡는 중입니다...',
      '탄지로가 상황의 냄새를 분석하고 있어요...',
      '탄지로가 주변의 기운을 감지하고 있어요...',

      // 아카자 (3개) - 투지/전투에 특화
      '아카자가 투지를 감지하는 중입니다...',
      '아카자가 상대의 강함을 측정하고 있어요...',
      '아카자가 전투 의지를 불태우고 있어요...',

      // 렌고쿠 (3개) - 열정/결의에 특화
      '렌고쿠가 마음을 불태우고 있습니다...',
      '렌고쿠가 굳은 결의를 다지고 있어요...',
      '렌고쿠가 동료를 지키기 위해 고민하고 있어요...',

      // 젠이츠 (3개) - 공포/용기에 특화
      '젠이츠가 떨면서도 용기를 내고 있어요...',
      '젠이츠가 위험을 감지하고 경계하고 있어요...',
      '젠이츠가 번개같은 판단을 하려 하고 있어요...',

      // 이노스케 (3개) - 야성/직감에 특화
      '이노스케가 야생의 직감으로 상황을 파악하고 있어요...',
      '이노스케가 돌격할 기회를 엿보고 있어요...',
      '이노스케가 멧돼지처럼 코를 벌름거리며 냄새를 맡고 있어요...',
    ];
    return loadingMessages[Math.floor(Math.random() * loadingMessages.length)];
  };

  // INTRO 스테이지 판별 함수 (빠른 출력 적용용)
  const isIntroStage = (stage?: string): boolean => {
    if (!stage) return false;
    const stageUpper = stage.toUpperCase();
    // Backend constants의 INTRO_STAGE_TAGS와 동기화: "상현_삼_등장", "INTRO"
    return stageUpper === 'INTRO' || stageUpper === '상현_삼_등장';
  };

  // 대화 내용 요약 생성 (엔딩 리워드용)
  const generateConversationSummary = (): string => {
    const userMessages = messages.filter(m => m.isUser);
    const aiMessages = messages.filter(m => !m.isUser && !m.isSystemMessage);
    const characterCounts: Record<string, number> = {};

    aiMessages.forEach(m => {
      const charId = m.characterId || 'unknown';
      characterCounts[charId] = (characterCounts[charId] || 0) + 1;
    });

    const topCharacters = Object.entries(characterCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([charId]) => getCharacterName(charId));

    const totalMessages = userMessages.length + aiMessages.length;

    return `무한열차 시나리오를 클리어하셨습니다!\n\n` +
           `총 대화 수: ${totalMessages}회\n` +
           `사용자 입력: ${userMessages.length}회\n` +
           `주요 대화 상대: ${topCharacters.join(', ')}\n\n` +
           `당신은 동료들과 함께 위기를 극복하고,\n` +
           `무한열차의 비밀을 밝혀냈습니다.\n\n` +
           `지금까지의 여정을 기념하는\n` +
           `특별한 이미지를 생성하고 있습니다...`;
  };

  // 음성 재생 함수
  const handlePlayAudio = (text: string) => {
    // 여기에 TTS (Text-to-Speech) 기능을 구현할 수 있습니다
    console.log('음성 재생:', text);
    // 예시: Web Speech API 사용
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'ko-KR';
      speechSynthesis.speak(utterance);
    }
  };

  // 메모리 이벤트 히스토리에 추가
  const handleMemoryEvents = (events: MemoryEvent[] | undefined) => {
    if (!events || events.length === 0) return;

    const now = Date.now();
    const newEvents = events.map((event, index) => ({
      ...event,
      id: `${now}-${index}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: now + index // 각 이벤트에 약간씩 다른 타임스탬프
    }));

    setMemoryEvents((prev) => [...prev, ...newEvents]);
  };

  // 메시지 스크롤 자동화
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]); // 메시지 변경 또는 타이핑 상태 변경 시 스크롤

  // 타이핑 효과와 함께 메시지를 표시하는 함수 (INTRO: 1ms, 일반: 10ms)
  const addMessageWithTypingEffect = async (message: Message): Promise<void> => {
    return new Promise((resolve) => {
      // 이 메시지에 배경 이미지 변경 요청이 있으면 먼저 처리
      if (message.imageIndex) {
        const imageIndex = parseInt(message.imageIndex);
        console.log(`🖼️ [Frontend] Changing background to image ${imageIndex} for message: ${message.text.substring(0, 30)}...`);
        console.log(`🖼️ Current background before change:`, currentBackground);
        setBackgroundByIndex(imageIndex);
        console.log(`🖼️ setBackgroundByIndex(${imageIndex}) called`);
      } else {
        console.log(`⚠️ No imageIndex for message: ${message.text.substring(0, 30)}...`);
      }

      // 소리 효과 재생 (몰입감 향상)
      if (!message.isUser) {
        if (message.isSystemMessage) {
          playSystemSound(); // 시스템 메시지: 낮은 톤
        } else {
          playMessageSound(); // 일반 AI 메시지: 부드러운 핑
        }
      }

      // 빈 메시지로 시작 (타이핑 시작)
      const messageId = message.id;
      setMessages(prev => [...prev, { ...message, text: '' }]);

      // INTRO 스테이지 판별하여 타이핑 속도 결정 (하드코딩에 가깝게 빠르게)
      const typingSpeed = isIntroStage(currentStage) ? 1 : TYPING_INTERVAL_MS;
      if (isIntroStage(currentStage)) {
        console.log(`⚡ [INTRO] Fast typing enabled (${typingSpeed}ms) for stage: ${currentStage}`);
      }

      // 타이핑 효과: typingSpeed마다 한 글자씩 추가
      const chars = message.text.split('');
      let currentIndex = 0;

      const typingInterval = setInterval(() => {
        // Skip 플래그 체크
        if (shouldSkip.current) {
          // 즉시 전체 텍스트 표시
          setMessages(prev => prev.map(msg =>
            msg.id === messageId ? { ...msg, text: message.text } : msg
          ));
          clearInterval(typingInterval);
          typingIntervalRef.current = null;
          resolve();
          return;
        }

        currentIndex++;
        const typedText = chars.slice(0, currentIndex).join('');

        setMessages(prev => prev.map(msg =>
          msg.id === messageId ? { ...msg, text: typedText } : msg
        ));

        if (currentIndex >= chars.length) {
          clearInterval(typingInterval);
          typingIntervalRef.current = null;
          resolve();
        }
      }, typingSpeed);

      // interval을 ref에 저장
      typingIntervalRef.current = typingInterval;
    });
  };

  // 고유한 메시지 ID 생성 함수
  const generateMessageId = () => {
    messageIdCounter.current += 1;
    return Date.now() * 1000 + messageIdCounter.current; // 타임스탬프 * 1000 + 카운터로 고유성 보장
  };

  // 메시지를 순차적으로 표시하는 함수 (타이핑 효과 + 2.5초 간격)
  const addMessagesSequentially = async (newMessages: Message[]) => {
    if (isAddingMessages.current) {
      console.warn('⚠️ Already adding messages, skipping duplicate call');
      return;
    }

    // 🔥 플래그 리셋: 이전 요청에서 true로 남아있을 수 있음
    shouldCancelAutoRequest.current = false;
    shouldSkip.current = false; // Skip 플래그 리셋

    // 남은 메시지들을 ref에 저장 (Skip 기능용)
    pendingMessagesRef.current = [...newMessages];

    isAddingMessages.current = true;
    setIsTyping(true);

    try {
      console.log(`📝 Adding ${newMessages.length} messages sequentially...`);

      for (let i = 0; i < newMessages.length; i++) {
        // 사용자가 중단을 요청했는지 확인
        if (shouldCancelAutoRequest.current) {
          console.log('⚠️ User cancelled, stopping message display');
          break;
        }

        console.log(`  → Message ${i + 1}/${newMessages.length}: ${newMessages[i].characterId} - ${newMessages[i].text.substring(0, 30)}...`);

        // 남은 메시지 업데이트
        pendingMessagesRef.current = newMessages.slice(i + 1);

        // 타이핑 효과로 메시지 표시
        await addMessageWithTypingEffect(newMessages[i]);

        // 마지막 메시지가 아니면 50ms 대기 (빠른 흐름) - Phase 1 개선: 800ms → 50ms (16배 빠르게)
        if (i < newMessages.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 50)); // 0.05 seconds
        }
      }

      console.log('✅ Finished adding messages');
    } finally {
      // 🔥 에러가 발생해도 반드시 타이핑 상태를 해제
      setIsTyping(false);
      isAddingMessages.current = false;
      pendingMessagesRef.current = []; // pending messages 초기화
      shouldSkip.current = false; // Skip 플래그 리셋
    }
  };

  // 자동 요청 함수 (has_more가 true일 때 호출)
  const handleAutoRequest = async (currentSessionId: string, retryCount: number = 0) => {
    // 최대 재시도 횟수 체크
    if (retryCount >= 3) {
      console.error('Max retry attempts reached');
      setLoadingMessage(null);
      setIsAutoRequesting(false); // 🔧 FIX: 최대 재시도 도달 시 상태 초기화
      return;
    }

    // 사용자가 중단을 원하면 취소
    if (shouldCancelAutoRequest.current) {
      shouldCancelAutoRequest.current = false;
      setLoadingMessage(null);
      setIsAutoRequesting(false);
      return;
    }

    try {
      setIsAutoRequesting(true);
      setLoadingMessage(getRandomLoadingMessage());

      // 자동 요청 시에는 "__AUTO_CONTINUE__"를 user_input으로 전송
      const response: ChatResponse = await sendChatMessage(
        backendScenarioId,
        '__AUTO_CONTINUE__',
        currentSessionId,
        currentUser || 'Player'  // 로그인한 사용자 이름 사용
      );

      setLoadingMessage(null);

      console.log(`📥 Received ${response.dialogues.length} dialogues, has_more: ${response.has_more}, stage: ${response.current_stage}`);
      console.log('🔍 Full response:', response);

      // Update affinity_scores and current_stage from response
      setAffinityScores(response.affinity_scores || {});
      setCurrentStage(response.current_stage); // INTRO 판별을 위한 현재 스테이지 저장

      // 메모리 이벤트 처리 (토스트 알림 표시)
      handleMemoryEvents(response.memory_events);

      // 배경 이미지 변경 (current_image 사용)
      if (response.current_image) {
        console.log(`🖼️ [Auto-request] Changing background to: ${response.current_image}`);
        handleBackgroundChange(response.current_image);
      }

      // 참여 중인 캐릭터 업데이트 (has_more가 true면 누적, false면 새로고침)
      updateInvitedCharacters(response.dialogues, response.has_more);

      // 백엔드 응답을 메시지로 변환 (고유 ID 사용)
      const backendMessages: Message[] = response.dialogues.map((dialogue) => {
        // 디버깅: image_index 값 로깅
        if (dialogue.image_index) {
          console.log(`🖼️ Dialogue has image_index: ${dialogue.image_index} for speaker: ${dialogue.speaker}`);
        }
        return {
          id: generateMessageId(),
          text: dialogue.text || dialogue.content || '',  // 백엔드는 text 필드 사용
          isUser: false,
          timestamp: new Date(),
          characterId: dialogue.speaker,
          isSystemMessage: dialogue.speaker === 'system' || dialogue.speaker === 'narr',
          imageIndex: dialogue.image_index  // 배경 이미지 인덱스
        };
      });

      // 순차적으로 메시지 표시 (타이핑 효과 포함)
      await addMessagesSequentially(backendMessages);

      // has_more가 true이면 계속 자동 요청
      if (response.has_more && !shouldCancelAutoRequest.current) {
        console.log('🔄 has_more is true, scheduling next auto-request in 1s...');
        // 1초 후 다음 배치 요청
        autoRequestTimerRef.current = window.setTimeout(() => {
          handleAutoRequest(response.session_id, 0); // 성공 시 재시도 카운트 리셋
        }, 1000);
      } else {
        console.log(`✅ Auto-request complete. has_more: ${response.has_more}, cancelled: ${shouldCancelAutoRequest.current}`);
        setIsAutoRequesting(false);
      }
    } catch (error) {
      console.error(`Auto request failed (attempt ${retryCount + 1}/3):`, error);
      setLoadingMessage(null); // 🔧 FIX: 에러 시 로딩 메시지 제거

      // 최대 재시도 횟수에 도달했는지 확인
      if (retryCount + 1 >= 3) {
        console.error('🔥 Max retry attempts reached after error');
        setIsAutoRequesting(false); // 🔧 FIX: 최대 재시도 도달 시 상태 초기화
        return;
      }

      // 재시도
      autoRequestTimerRef.current = window.setTimeout(() => {
        handleAutoRequest(currentSessionId, retryCount + 1);
      }, 1000 * (retryCount + 1)); // Exponential backoff: 1s, 2s, 3s
    }
  };

  // 초기 시나리오 로드 (백엔드 연결)
  useEffect(() => {
    // 세션 체크가 완료될 때까지 대기 (모달에서 사용자 선택 완료 대기)
    if (!sessionCheckDone) {
      console.log('⏸️ Waiting for session check to complete...');
      return;
    }

    const initializeChat = async () => {
      setIsLoading(true);
      setBackendError(null);

      try {
        // 기존 세션을 이어하는 경우 (initialSessionId가 있는 경우)
        if (initialSessionId) {
          console.log(`🔄 Resuming session: ${initialSessionId}`);
          // 세션 히스토리 로드는 별도 useEffect에서 처리되므로 여기서는 세션 ID만 설정
          setSessionId(initialSessionId);
          setIsLoading(false);
          return;
        }

        // 새 세션 시작: 첫 메시지 전송 (prologue가 있으면 백엔드에서 자동 반환)
        console.log('🎬 Starting new session with prologue...');
        const response: ChatResponse = await sendChatMessage(
          backendScenarioId,
          '시작',  // Initial trigger message (prologue가 있으면 백엔드에서 무시됨)
          undefined,
          currentUser || 'Player'  // 로그인한 사용자 이름 사용
        );

        // 세션 ID 저장
        setSessionId(response.session_id);
        onSessionStart?.(response.session_id); // Notify parent of new session creation

        console.log(`🎬 Initial response: ${response.dialogues.length} dialogues, has_more: ${response.has_more}, stage: ${response.current_stage}`);
        console.log('🔍 Full response:', response);

        // Update affinity_scores and current_stage from response
        setAffinityScores(response.affinity_scores || {});
        setCurrentStage(response.current_stage); // INTRO 판별을 위한 현재 스테이지 저장

        // 메모리 이벤트 처리 (토스트 알림 표시)
        handleMemoryEvents(response.memory_events);

        // 배경 이미지 변경 (current_image 사용)
        if (response.current_image) {
          console.log(`🖼️ [Initial session] Changing background to: ${response.current_image}`);
          handleBackgroundChange(response.current_image);
        }

        // 참여 중인 캐릭터 업데이트 (초기 세션이므로 누적 없이 새로 설정)
        updateInvitedCharacters(response.dialogues, false);

        // 백엔드 응답을 메시지로 변환 (고유 ID 사용)
        const backendMessages: Message[] = response.dialogues.map((dialogue) => {
          // 디버깅: image_index 값 로깅
          if (dialogue.image_index) {
            console.log(`🖼️ Dialogue has image_index: ${dialogue.image_index} for speaker: ${dialogue.speaker}`);
          }
          return {
            id: generateMessageId(),
            text: dialogue.text || dialogue.content || '',  // 백엔드는 text 필드 사용
            isUser: false,
            timestamp: new Date(),
            characterId: dialogue.speaker,
            isSystemMessage: dialogue.speaker === 'system' || dialogue.speaker === 'narr',
            imageIndex: dialogue.image_index  // 배경 이미지 인덱스
          };
        });

        // 순차적으로 메시지 표시 (타이핑 효과 포함)
        await addMessagesSequentially(backendMessages);

        // has_more가 true이면 자동 요청 시작
        if (response.has_more) {
          console.log('🔄 Starting auto-request chain...');
          handleAutoRequest(response.session_id);
        }
      } catch (error) {
        console.error('Failed to initialize chat:', error);
        setBackendError('백엔드 연결에 실패했습니다. 서버가 실행 중인지 확인해주세요.');

        // Fallback: Show error message
        const errorMessage: Message = {
          id: Date.now(),
          text: '⚠️ 백엔드 서버에 연결할 수 없습니다. http://localhost:8000 에서 서버를 시작해주세요.',
          isUser: false,
          timestamp: new Date(),
          characterId: 'system',
          isSystemMessage: true
        };
        setMessages([errorMessage]);
      } finally {
        setIsLoading(false);
      }
    };

    initializeChat();
  }, [characterId, initialSessionId, sessionCheckDone]); // sessionCheckDone 추가

  // Old hardcoded scenario (removed)
  /*
  useEffect(() => {
    const scenarioMessages = [
      {
        characterId: 'system',
        text: '⚠️ 시스템 알림: 본 채팅방은 귀살대원들을 위한 공간입니다. 부적절한 언어 사용은 금지되며, 귀살대원들은 정당한 명령에만 응합니다.',
        delay: 0,
        isSystemMessage: true
      },
      {
        characterId: 'system',
        text: '🗡️ 최종 결전이 끝나고 평화가 찾아온 세상입니다. 🌸 훈련장에서는 따뜻한 오후 햇살이 비추고 있고, 네 명의 동료들이 모여 있습니다. 💭 이제는 전투가 아닌 일상을 나누며 서로를 돌보는 시간이 시작되었어요. ✨ 평화로운 대화가 흘러가고 있습니다.',
        delay: 2000,
        isSystemMessage: true
      },
      {
        characterId: 'tanjiro',
        text: '오늘은 훈련은 조금만… 몸이 아직 무겁네요.',
        delay: 4000
      },
      {
        characterId: 'user',
        text: '괜찮아요, 탄지로 선배. 제가 함께 페이스 맞출게요.',
        delay: 4800
      },
      {
        characterId: 'zenitsu',
        text: '저도… 오늘은 네즈코와 잠깐 쉬다 올까 생각 중이에요.',
        delay: 5600
      },
      {
        characterId: 'user',
        text: '젠이츠, 그래도 순찰은 같이 가야죠. 네즈코는 걱정하지 마세요.',
        delay: 6400
      },
      {
        characterId: 'inosuke',
        text: '하! 탄지로가 몸 상태가 안 좋다고? 오늘은 내가 신나게 뛰어줄 차례군!',
        delay: 7200
      },
      {
        characterId: 'user',
        text: '조심하세요, 이노스케. 몸 상태 안 좋은 분 먼저 챙겨야죠.',
        delay: 8000
      },
      {
        characterId: 'tanjiro',
        text: '고마워요… 같이 순찰해주니 마음이 놓이네요.',
        delay: 8800
      },
      {
        characterId: 'zenitsu',
        text: '우리도 이제 단순 전투만 하는 건 아니네요… 이렇게 서로 돌봐주고…',
        delay: 9600
      },
      {
        characterId: 'user',
        text: '맞아요. 평화가 찾아오니 이렇게 마음을 나누는 시간도 필요하네요.',
        delay: 10400
      },
      {
        characterId: 'inosuke',
        text: '젠이츠, 네즈코랑 데이트는 언제가 돼? 순찰 말고!',
        delay: 11200
      },
      {
        characterId: 'zenitsu',
        text: '그런 거… 은근히 바쁘네요. 오늘은 잠깐 얼굴 보고 올 거예요.',
        delay: 12000
      },
      {
        characterId: 'user',
        text: '젠이츠, 숨겨진 행복도 중요하죠. 훈련 후에 이야기 듣게 해주세요.',
        delay: 12800
      },
      {
        characterId: 'tanjiro',
        text: '전투 후 회복도 중요하지만, 마음의 회복도 필요하군요.',
        delay: 13600
      },
      {
        characterId: 'user',
        text: '우리 모두 전투 이후 더 단단해진 거죠. 서로 의지하면서.',
        delay: 14400
      },
      {
        characterId: 'nezuko',
        text: '음... 음음! (네즈코가 모두를 따뜻하게 바라보며 고개를 끄덕입니다)',
        delay: 15200
      },
      {
        characterId: 'inosuke',
        text: '그래, 모두가 서로 챙기니 진짜 팀 같군!',
        delay: 16000
      },
      {
        characterId: 'zenitsu',
        text: '전투를 함께한 동료가 이렇게 함께해주니… 힘이 나네요.',
        delay: 16800
      },
      {
        characterId: 'tanjiro',
        text: '오늘 순찰이 끝나면 조금 쉬어야겠어요. 피가 아직 완전히 회복되지 않았네요.',
        delay: 17600
      },
      {
        characterId: 'user',
        text: '좋아요. 오늘 하루, 평화 속에서 이렇게 서로 챙기며 보내는 게 가장 큰 보람인 것 같아요.',
        delay: 18400
      },
      {
        characterId: 'system',
        text: '🌸 따뜻한 오후 햇살이 귀살대 훈련장을 비추고 있습니다. 네 사람의 얼굴엔 평화로운 미소가 번지고 있어요.',
        delay: 19200,
        isSystemMessage: true
      },
      {
        characterId: 'nezuko',
        text: '음음~ 음! (네즈코가 탄지로의 어깨를 살짝 두드리며 걱정스럽게 바라봅니다)',
        delay: 20000
      },
      {
        characterId: 'tanjiro',
        text: '네즈코야, 괜찮아. 조금만 쉬면 금방 나아질 거야.',
        delay: 20800
      },
      {
        characterId: 'zenitsu',
        text: '이제 정말 평화로운 일상이 시작된 것 같아요. 무서운 전투는 이제 그만...',
        delay: 21600
      },
      {
        characterId: 'inosuke',
        text: '하지만 훈련은 계속해야지! 평화를 지키려면 더 강해져야 한다!',
        delay: 22400
      },
      {
        characterId: 'system',
        text: '🍃 바람에 벚꽃 잎이 흩날리며 네 명의 동료들 사이를 지나갑니다. 이노스케는 주먹을 불끈 쥐고, 젠이츠는 하늘을 올려다보고 있어요.',
        delay: 23200,
        isSystemMessage: true
      },
      {
        characterId: 'user',
        text: '맞아요. 우리가 지켜낸 이 평화를 계속 지켜나가야죠.',
        delay: 24000
      },
      {
        characterId: 'tanjiro',
        text: '함께라면 뭐든 할 수 있을 거예요. 우리는 이미 많은 것을 이겨냈으니까.',
        delay: 24800
      },
      {
        characterId: 'zenitsu',
        text: '그래요... 이제는 무서운 것도 덜하고. 네즈코가 곁에 있으니까 더욱 용기가 나요.',
        delay: 25600
      },
      {
        characterId: 'nezuko',
        text: '음... 음음음! (네즈코가 젠이츠를 보며 부끄러워하는 듯 고개를 살짝 숙입니다)',
        delay: 26400
      },
      {
        characterId: 'inosuke',
        text: '아하! 젠이츠가 또 빨개졌다! 네즈코 앞에서는 항상 그러네!',
        delay: 27200
      },
      {
        characterId: 'system',
        text: '😊 젠이츠의 얼굴이 빨갛게 달아오르고, 네즈코는 살짝 미소를 짓고 있습니다. 탄지로와 이노스케는 즐거워하며 웃고 있어요.',
        delay: 28000,
        isSystemMessage: true
      },
      {
        characterId: 'user',
        text: '이런 순간들이 정말 소중하네요. 전투 중에는 생각할 수 없었던 일상의 행복이에요.',
        delay: 28800
      },
      {
        characterId: 'tanjiro',
        text: '정말 그래요. 이제는 웃을 수 있고, 서로를 걱정할 여유도 생겼고...',
        delay: 29600
      },
      {
        characterId: 'zenitsu',
        text: '앞으로도 이런 평화로운 날들이 계속되었으면 좋겠어요.',
        delay: 30400
      },
      {
        characterId: 'inosuke',
        text: '그럼 우리가 더 열심히 훈련해서 마을을 지키면 되지! 간단한 일이야!',
        delay: 31200
      },
      {
        characterId: 'nezuko',
        text: '음음! (네즈코가 모든 이들을 바라보며 따뜻하게 웃고 있습니다)',
        delay: 32000
      },
      {
        characterId: 'system',
        text: '🌅 해가 서서히 지기 시작하며 하늘이 황금빛으로 물들어갑니다. 네 명의 동료들은 서로를 바라보며 깊은 유대감을 느끼고 있어요.',
        delay: 32800,
        isSystemMessage: true
      },
      {
        characterId: 'user',
        text: '오늘 정말 좋은 시간이었어요. 내일도 함께 순찰하며 이런 평화를 지켜나가요.',
        delay: 33600
      }
    ];

    const timeouts: NodeJS.Timeout[] = [];

    scenarioMessages.forEach((scenario, index) => {
      const timeout = setTimeout(() => {
        const newMessage: Message = {
          id: Date.now() + index,
          text: scenario.text,
          isUser: scenario.characterId === 'user',
          timestamp: new Date(),
          characterId: scenario.characterId === 'user' ? undefined : scenario.characterId,
          isSystemMessage: scenario.isSystemMessage || false
        };
        setMessages(prev => [...prev, newMessage]);
      }, scenario.delay);

      timeouts.push(timeout);
    });
  }, [characterId]);
  */

  // Skip 버튼 핸들러 - 대화 출력 중 즉시 완료
  const handleSkip = () => {
    console.log('⏩ Skip button clicked');

    // Skip 플래그 설정
    shouldSkip.current = true;

    // 현재 타이핑 interval이 있으면 즉시 완료 처리
    if (typingIntervalRef.current) {
      console.log('  → Stopping current typing animation');
    }

    // 남은 메시지들이 있으면 즉시 모두 표시
    if (pendingMessagesRef.current.length > 0) {
      console.log(`  → Adding ${pendingMessagesRef.current.length} pending messages immediately`);
      const remainingMessages = [...pendingMessagesRef.current];
      pendingMessagesRef.current = [];

      // 남은 메시지들을 즉시 추가 (타이핑 효과 없이)
      setMessages(prev => [...prev, ...remainingMessages]);

      // 타이핑 상태 해제
      setIsTyping(false);
      isAddingMessages.current = false;
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    // 🎯 명령어 처리 (백엔드로 전송하지 않음)
    const command = text.trim().toLowerCase();
    if (command === 'my account' || command === '/my account' || command === '마이 어카운트' || command === '내 계정') {
      openMyAccount();
      setInputMessage(''); // 입력창 초기화
      return;
    }

    // 🚫 중복 전송 방지
    if (isSendingRef.current) {
      console.log('⚠️ [DUPLICATE] Message already sending, ignoring duplicate call');
      return;
    }

    isSendingRef.current = true;
    // 🫧 버블 소비 (1회 대화당 1 버블)
    const bubbleCost = 1;
    const consumed = await consumeBubbles(bubbleCost);

    if (!consumed) {
      setBackendError(`버블이 부족합니다. 최소 ${bubbleCost}개의 버블이 필요합니다.`);
      isSendingRef.current = false;  // 실패 시 플래그 리셋
      return;
    }

    // 🔊 오디오 활성화 (브라우저 자동재생 정책 우회) - 비차단 방식
    unlockAudio();

    // 🔥 디버깅: 현재 상태 출력
    console.log('🔍 [DEBUG] sendMessage called:', {
      isLoading,
      isTyping,
      isAutoRequesting,
      text: text.substring(0, 20)
    });

    // 🔥 자동 요청 중일 때는 사용자 입력 차단
    if (isAutoRequesting) {
      console.log('⚠️ Auto-requesting in progress, user input blocked');
      isSendingRef.current = false;  // 차단 시 플래그 리셋
      return;
    }

    // 사용자가 메시지를 보내면 진행 중인 자동 요청을 중단
    shouldCancelAutoRequest.current = true;
    if (autoRequestTimerRef.current) {
      clearTimeout(autoRequestTimerRef.current);
      autoRequestTimerRef.current = null;
    }
    setIsAutoRequesting(false);
    setLoadingMessage(null);

    // Add user message to UI
    const newMessage: Message = {
      id: Date.now(),
      text,
      isUser: true,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, newMessage]);
    setInputMessage('');

    // Call message sent callback
    onMessageSent?.();

    // Send to backend
    setIsLoading(true);
    setBackendError(null);

    try {
      const response: ChatResponse = await sendChatMessage(
        backendScenarioId,
        text,
        sessionId,
        currentUser || 'Player'  // 로그인한 사용자 이름 사용
      );

      console.log(`📥 User message response: ${response.dialogues.length} dialogues, has_more: ${response.has_more}, stage: ${response.current_stage}`);
      console.log('🔍 Full response:', response);

      // Update session ID if it changed
      if (response.session_id !== sessionId) {
        setSessionId(response.session_id);
        onSessionStart?.(response.session_id); // Notify parent of session change
      }

      // Update affinity_scores and current_stage from response
      setAffinityScores(response.affinity_scores || {});
      setCurrentStage(response.current_stage); // INTRO 판별을 위한 현재 스테이지 저장

      // 메모리 이벤트 처리 (토스트 알림 표시)
      handleMemoryEvents(response.memory_events);

      // 배경 이미지 변경 (current_image 사용)
      if (response.current_image) {
        console.log(`🖼️ [User message] Changing background to: ${response.current_image}`);
        handleBackgroundChange(response.current_image);
      }

      // 참여 중인 캐릭터 업데이트 (사용자 메시지 응답이므로 누적 없이 새로 설정)
      updateInvitedCharacters(response.dialogues, false);

      // Add backend responses to messages sequentially (고유 ID 사용)
      const backendMessages: Message[] = response.dialogues.map((dialogue) => {
        // 디버깅: image_index 값 로깅
        if (dialogue.image_index) {
          console.log(`🖼️ Dialogue has image_index: ${dialogue.image_index} for speaker: ${dialogue.speaker}`);
        }
        return {
          id: generateMessageId(),
          text: dialogue.text || dialogue.content || '',  // 백엔드는 text 필드 사용
          isUser: false,
          timestamp: new Date(),
          characterId: dialogue.speaker,
          isSystemMessage: dialogue.speaker === 'system' || dialogue.speaker === 'narr',
          imageIndex: dialogue.image_index  // 배경 이미지 인덱스
        };
      });

      const hasSystemMessageInBackend = backendMessages.some(
        (message) => message.isSystemMessage && message.text.trim().length > 0
      );
      const systemDialogue = response.dialogues.find(
        (dialogue) =>
          dialogue.speaker &&
          dialogue.speaker.toLowerCase() === 'system' &&
          (dialogue.text || dialogue.content)
      );
      const fallbackSystemMessage =
        response.system_message ||
        systemDialogue?.text ||
        systemDialogue?.content ||
        '';

      // 시스템 메시지와 종료 메시지를 백엔드 메시지에 추가
      const allMessages = [...backendMessages];
      let extraMessageOffset = 1;

      const pushSystemMessage = (text: string) => {
        allMessages.push({
          id: Date.now() + backendMessages.length + extraMessageOffset,
          text,
          isUser: false,
          timestamp: new Date(),
          characterId: 'system',
          isSystemMessage: true
        });
        extraMessageOffset += 1;
      };

      // Show system message if provided
      if (response.system_message) {
        pushSystemMessage(response.system_message);
      } else if (!hasSystemMessageInBackend && fallbackSystemMessage) {
        pushSystemMessage(fallbackSystemMessage);
      }

      // Check if chat has ended - Phase 4 개선 + 엔딩 리워드
      if (response.is_ended) {
        pushSystemMessage('🎬 시나리오가 종료되었습니다.');
        setIsEnded(true); // Phase 4: 엔딩 상태 설정
        setBackgroundByIndex(21); // Phase 4: 엔딩 이미지 표시 (무한열차 마지막 이미지)

        // 엔딩 리워드: 대화 요약 생성 및 모달 표시
        setTimeout(() => {
          const summary = generateConversationSummary();
          setEndingSummary(summary);
          setShowEndingReward(true);
        }, 2000); // 2초 후 리워드 모달 표시
      }

      // 순차적으로 메시지 표시 (타이핑 효과 포함)
      await addMessagesSequentially(allMessages);

      // has_more가 true이면 자동 요청 시작
      if (response.has_more) {
        handleAutoRequest(response.session_id);
      }
    } catch (error) {
      console.error('Failed to send message:', error);

      // 오류 메시지 표시
      const errorDetail = error instanceof Error ? error.message : '알 수 없는 오류';
      setBackendError(`메시지 전송에 실패했습니다.\n${errorDetail}`);

      // 시스템 에러 메시지 추가
      const errorMessage: Message = {
        id: Date.now() + 1,
        text: '⚠️ 메시지 전송에 실패했습니다. 네트워크 상태를 확인하거나 잠시 후 다시 시도해주세요.',
        isUser: false,
        timestamp: new Date(),
        characterId: 'system',
        isSystemMessage: true
      };
      setMessages(prev => [...prev, errorMessage]);

      // 모든 진행 중인 상태 초기화 (대화창 복구)
      setIsTyping(false);
      setIsAutoRequesting(false);
      setLoadingMessage(null);
      shouldCancelAutoRequest.current = true;
      if (autoRequestTimerRef.current) {
        clearTimeout(autoRequestTimerRef.current);
        autoRequestTimerRef.current = null;
      }
      isAddingMessages.current = false;

      // 5초 후 에러 메시지 자동 제거
      setTimeout(() => {
        setBackendError(null);
      }, 5000);
    } finally {
      setIsLoading(false);
      isSendingRef.current = false; // 전송 완료 플래그 리셋
    }
  };

  // 캐릭터 선택 핸들러
  const handleCharacterSelect = (selectedCharacterId: string) => {
    console.log('Selected character:', selectedCharacterId);

    // 이미 초대된 캐릭터인지 확인
    if (invitedCharacters.includes(selectedCharacterId)) {
      alert('이미 대화에 참여중인 캐릭터입니다!');
      return;
    }

    // 새 캐릭터 초대
    setInvitedCharacters(prev => [...prev, selectedCharacterId]);

    // 캐릭터 모달 닫기
    setShowCharacterModal(false);

    // 캐릭터별 등장 시나리오
    const characterEntryScenarios: Record<string, any[]> = {
      'giyu': [
        {
          characterId: 'system',
          text: '🌊 훈련장 입구에서 조용한 발걸음이 들려옵니다. 기유가 차분한 표정으로 천천히 다가오고 있어요.',
          delay: 500,
          isSystemMessage: true
        },
        {
          characterId: 'giyu',
          text: '기유입니다. 모두 수고하고 계시는군요.',
          delay: 1500
        },
        {
          characterId: 'tanjiro',
          text: '기유 선배! 오늘도 순찰 다녀오셨나요?',
          delay: 2500
        },
        {
          characterId: 'giyu',
          text: '네. 마을은 평화롭습니다. 여러분도 몸조리 잘하고 계시는 것 같아 다행이네요.',
          delay: 3500
        },
        {
          characterId: 'zenitsu',
          text: '기유 선배! 정말 오랜만이에요. 이제는 무서운 전투 없이 만날 수 있어서 좋아요.',
          delay: 4500
        },
        {
          characterId: 'giyu',
          text: '그렇습니다. 이런 평화로운 시간이 계속되기를 바랍니다.',
          delay: 5500
        }
      ],
      'akaza': [
        {
          characterId: 'system',
          text: '💫 갑자기 주변의 공기가 차갑게 변합니다. 아카자가 조용히 나타나며, 모든 이의 몸이 긴장으로 굳어지고 있어요.',
          delay: 500,
          isSystemMessage: true
        },
        {
          characterId: 'tanjiro',
          text: '아카자... 너는 분명히 죽었을 텐데? 어떻게 여기에...?',
          delay: 1500
        },
        {
          characterId: 'akaza',
          text: '탄지로... 맞다. 나는 죽었다. 하지만 지금은 다른 형태로 존재하고 있다.',
          delay: 2500
        },
        {
          characterId: 'zenitsu',
          text: '뭐... 뭐야?! 유령이야?! 무서워!!!',
          delay: 3500
        },
        {
          characterId: 'akaza',
          text: '유령이라고 할 수도 있겠군. 하지만 나는 더 이상 인간을 해치지 않는다.',
          delay: 4500
        },
        {
          characterId: 'inosuke',
          text: '그럼... 뭐하러 나타난 거야? 또 싸우러 온 거냐?',
          delay: 5500
        },
        {
          characterId: 'akaza',
          text: '아니다. 나는... 속죄하러 왔다. 그리고 너희의 강함을 다시 한 번 확인하고 싶었다.',
          delay: 6500
        },
        {
          characterId: 'tanjiro',
          text: '속죄... 그렇다면 정말로 마음이 바뀐 건가요?',
          delay: 7500
        },
        {
          characterId: 'akaza',
          text: '탄지로, 너의 말들이... 나를 변화시켰다. 강함의 진정한 의미를 깨달았다.',
          delay: 8500
        },
        {
          characterId: 'nezuko',
          text: '음... 음음? (네즈코가 조심스럽게 아카자를 바라보고 있습니다)',
          delay: 9500
        },
        {
          characterId: 'akaza',
          text: '네즈코... 너도 강해졌구나. 인간을 지키는 강함을. 나도... 이제 그런 강함을 추구하고 싶다.',
          delay: 10500
        }
      ]
    };

    // 선택된 캐릭터의 시나리오 실행
    const scenario = characterEntryScenarios[selectedCharacterId];
    if (scenario) {
      const timeouts: NodeJS.Timeout[] = [];

      scenario.forEach((scene, index) => {
        const timeout = setTimeout(() => {
          const newMessage: Message = {
            id: Date.now() + index,
            text: scene.text,
            isUser: false,  // 시나리오 메시지는 모두 NPC (characterId='user'는 플레이어 캐릭터 NPC)
            timestamp: new Date(),
            characterId: scene.characterId,  // 'user' characterId도 NPC 캐릭터로 처리
            isSystemMessage: scene.isSystemMessage || false
          };
          setMessages(prev => [...prev, newMessage]);
        }, scene.delay);

        timeouts.push(timeout);
      });
    } else {
      // 기본 입장 메시지 (다른 캐릭터들용)
      const joinMessage: Message = {
        id: Date.now(),
        text: `${getCharacterName(selectedCharacterId)}가 대화에 참여했습니다! 🎉`,
        isUser: false,
        timestamp: new Date(),
        characterId: selectedCharacterId
      };
      setMessages(prev => [...prev, joinMessage]);

      // 잠시 후 캐릭터 인사 메시지 추가
      setTimeout(() => {
        const greetingMessages: Record<string, string> = {
          'tanjiro': '안녕하세요! 탄지로입니다. 잘 부탁드려요!',
          'nezuko': '음... 음음! (네즈코가 인사하고 있어요)',
          'zenitsu': '젠이츠입니다! 떨리지만 열심히 하겠습니다!',
          'inosuke': '산왕 이노스케님 등장이다! 잘 부탁한다!'
        };

        const greetingMessage: Message = {
          id: Date.now() + 1,
          text: greetingMessages[selectedCharacterId] || `${getCharacterName(selectedCharacterId)}입니다. 잘 부탁드려요!`,
          isUser: false,
          timestamp: new Date(),
          characterId: selectedCharacterId
        };
        setMessages(prev => [...prev, greetingMessage]);
      }, 1500);
    }
  };

  // 친구 선택 핸들러
  const handleFriendSelect = (friendId: string) => {
    console.log('Selected friend:', friendId);
    // 여기서 선택된 친구로 대화 추가 로직을 구현할 수 있습니다
  };

  // + 버튼 클릭 핸들러
  const handleAddClick = () => {
    setShowCharacterModal(true);
  };

  // 마이크 버튼 클릭 핸들러
  const handleMicClick = () => {
    setShowVoiceModal(true);
    setTranscript('');
    startListening();
  };

  // STT 시작
  const startListening = () => {
    setIsListening(true);

    // Web Speech API 사용 (실제 STT)
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();

      recognition.lang = 'ko-KR';
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        const current = event.resultIndex;
        const transcript = event.results[current][0].transcript;
        setTranscript(transcript);
      };

      recognition.onerror = (event: any) => {
        console.error('STT 오류:', event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } else {
      // Web Speech API가 지원되지 않는 경우 시뮬레이션
      simulateSTT();
    }
  };

  // STT 시뮬레이션 (Web Speech API 미지원 시)
  const simulateSTT = () => {
    const simulatedTexts = [
      '안녕하세요',
      '네즈코야 안녕',
      '오늘 날씨가 좋네요',
      '같이 놀까요',
      '고마워요'
    ];

    let currentText = '';
    const targetText = simulatedTexts[Math.floor(Math.random() * simulatedTexts.length)];

    const typeInterval = setInterval(() => {
      if (currentText.length < targetText.length) {
        currentText += targetText[currentText.length];
        setTranscript(currentText);
      } else {
        clearInterval(typeInterval);
        setIsListening(false);
      }
    }, 150);
  };

  // STT 완료 및 메시지 전송
  const handleVoiceComplete = () => {
    if (transcript.trim()) {
      sendMessage(transcript);
    }
    setShowVoiceModal(false);
    setTranscript('');
    setIsListening(false);
  };

  // STT 취소
  const handleVoiceCancel = () => {
    setShowVoiceModal(false);
    setTranscript('');
    setIsListening(false);
  };

  const renderBackgroundVisual = () => {
    const transitionClass = `w-full h-full transition-opacity duration-500 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`;

    if (currentBackground?.isVideo && backgroundImageUrl) {
      return (
        <video
          key={backgroundImageUrl}
          className={`${transitionClass} object-cover`}
          src={backgroundImageUrl}
          autoPlay
          loop
          muted
          playsInline
        />
      );
    }

    // 시나리오별 기본 배경 이미지 설정
    const getDefaultBackgroundImage = () => {
      if (characterId === 'counseling') {
        return 'url(/images/scenarios/counseling.jpg)';
      }
      // 기본값: 무한열차
      return 'url(/images/무한열차.png)';
    };

    return (
      <div
        className={`${transitionClass} bg-cover bg-center bg-no-repeat`}
        style={{
          backgroundImage: backgroundImageUrl
            ? `url(${backgroundImageUrl})`
            : getDefaultBackgroundImage()
        }}
      />
    );
  };

  return (
    <div className="w-full h-full flex flex-col md:flex-row bg-gray-100">
      {/* 왼쪽: 컷신 이미지 영역 (50%) */}
      <div className="relative w-full md:w-1/2 h-[40vh] md:h-full overflow-hidden">
        {/* 컷신 배경 이미지 */}
        {renderBackgroundVisual()}

        {/* 왼쪽 아래: 친밀도 패널 */}
        <div className="absolute bottom-4 left-4 right-44 z-10">
          <AffinityPanel affinityScores={affinityScores} />
        </div>

        {/* 오른쪽 아래: 버블 카운터 */}
        <div className="absolute bottom-4 right-4 z-10">
          <BubbleCounter compact />
        </div>
      </div>

      {/* 오른쪽: 채팅 영역 (50%) */}
      <div className="w-full md:w-1/2 h-[60vh] md:h-full flex flex-col bg-white">
        {/* 메시지 영역 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Backend error banner */}
        {backendError && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{backendError}</p>
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && messages.length === 0 && (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            <span className="ml-3 text-gray-500">시나리오를 불러오는 중...</span>
          </div>
        )}

        {/* 메시지들 */}
        {messages.map((message, index) => {
          const isLatestMessage = message.id === latestMessageId;
          const isFirstMessage = index === 0;

          // 시스템 메시지 렌더링 (경고 메시지는 꺾쇄까마귀 + 붉은색)
          if (message.isSystemMessage) {
            // 경고 메시지 판별 (오류, 경고, 제한 등의 키워드 포함 시)
            const isWarning = /경고|오류|금지|제한|불가|실패|차단|거부/.test(message.text);

            return (
              <div key={message.id} className={`flex justify-center ${isFirstMessage ? 'mb-8' : 'mb-32'} animate-slide-in-fade`}>
                <div
                  style={{
                    transform: isLatestMessage ? 'scale(1.35)' : 'scale(1)',
                    transformOrigin: 'center',
                    transition: 'transform 0.5s ease'
                  }}
                >
                <div className="max-w-lg">
                  <div className={`rounded-xl px-4 py-3 shadow-lg border-2 ${
                    isWarning
                      ? 'bg-gradient-to-r from-red-50 via-red-100 to-red-50 border-red-300'
                      : 'bg-gradient-to-r from-pink-50 via-purple-50 to-blue-50 border-purple-200'
                  }`}>
                    <p className={`text-center text-sm leading-relaxed font-medium ${
                      isWarning ? 'text-red-700' : 'text-gray-700 italic'
                    }`}>
                      {isWarning && <span className="font-bold">⚠️ 꺾쇄까마귀: </span>}
                      {replacePlaceholders(message.text, currentUser || undefined)}
                    </p>
                    <div className={`text-xs text-center mt-1 ${
                      isWarning ? 'text-red-400' : 'text-gray-400'
                    }`}>
                      {message.timestamp.toLocaleTimeString('ko-KR', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>
                </div>
                </div>
              </div>
            );
          }

          // 일반 메시지 렌더링
          const glowColors = getCharacterGlowColor(message.characterId || characterId);

          return (
            <div
              key={message.id}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'} ${isFirstMessage ? 'mb-8' : 'mb-32'} ${!message.isUser ? 'animate-slide-in-fade' : ''}`}
            >
              <div
                style={{
                  transform: isLatestMessage ? 'scale(1.35)' : 'scale(1)',
                  transformOrigin: message.isUser ? 'right center' : 'left center',
                  transition: 'transform 0.5s ease'
                }}
                className="flex"
              >
              {!message.isUser && (
                <div
                  className={`w-16 h-16 rounded-full mr-3 flex-shrink-0 transition-all duration-500`}
                  style={isLatestMessage && !message.isUser ? {
                    boxShadow: `0 0 20px ${glowColors.shadow}, 0 0 40px ${glowColors.shadow.replace('0.6', '0.3')}, 0 0 60px ${glowColors.shadow.replace('0.6', '0.15')}`
                  } : {}}
                >
                  <img
                    src={getCharacterProfile(message.characterId || characterId)}
                    alt="Character"
                    className="w-full h-full rounded-full object-cover border-2 border-gray-200"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = '/images/프로필_탄지로.png';
                    }}
                  />
                </div>
              )}
              <div className={`flex flex-col transition-all duration-500 ${
                message.isUser
                  ? 'max-w-md lg:max-w-lg'
                  : 'max-w-xs lg:max-w-md'
              }`}>
                {/* 화자 표시 */}
                <div className={`text-xs mb-1 ${message.isUser ? 'text-right text-gray-500' : 'text-left text-gray-500'}`}>
                  {message.isUser ? '사용자' : getCharacterName(message.characterId || characterId)}
                </div>

                <div className="flex items-start">
                  <div
                    className={`px-4 py-3 rounded-2xl flex-1 transition-all duration-500 ${
                      message.isUser
                        ? `bg-purple-500 text-white rounded-br-md ${isLatestMessage ? 'shadow-lg' : ''}`
                        : `text-gray-800 border border-gray-200 rounded-bl-md ${isLatestMessage ? '' : 'bg-white shadow-sm'}`
                    }`}
                    style={!message.isUser && isLatestMessage ? {
                      background: `${glowColors.bg}, white`,
                      boxShadow: `0 4px 20px ${glowColors.shadow.replace('0.6', '0.25')}, 0 8px 40px ${glowColors.shadow.replace('0.6', '0.15')}`
                    } : message.isUser && isLatestMessage ? {
                      boxShadow: '0 4px 30px rgba(147, 51, 234, 0.4), 0 8px 50px rgba(147, 51, 234, 0.2)'
                    } : {}}
                  >
                    <p className="text-sm leading-relaxed">{replacePlaceholders(message.text, currentUser || undefined)}</p>
                    <div className={`text-xs mt-1 ${message.isUser ? 'text-purple-100' : 'text-gray-400'}`}>
                      {message.timestamp.toLocaleTimeString('ko-KR', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>

                  {/* AI 메시지에만 스피커 아이콘 추가 */}
                  {!message.isUser && (
                    <button
                      onClick={() => handlePlayAudio(replacePlaceholders(message.text, currentUser || undefined))}
                      className="ml-2 p-1 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-600"
                      aria-label="음성으로 듣기"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M9 9h6a2 2 0 012 2v2a2 2 0 01-2 2H9V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9v6" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>

              {message.isUser && (
                <div className="w-16 h-16 rounded-full ml-3 flex-shrink-0 overflow-hidden border-2 border-purple-200">
                  <img
                    src={`${CDN_URL}/유저_이미지.jpg`}
                    alt="사용자"
                    className="w-full h-full object-cover rounded-full"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `${CDN_URL}/기본이미지.png`;
                    }}
                  />
                </div>
              )}
              </div> {/* scale wrapper 닫기 */}
            </div>
          );
        })}

        {/* 타이핑 중 인디케이터 (카카오톡 스타일) */}
        {isTyping && (
          <div className="flex justify-start mb-4">
            <div className="w-16 h-16 rounded-full mr-3 flex-shrink-0">
              <div className="w-full h-full rounded-full bg-gray-200 flex items-center justify-center">
                <svg className="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
                </svg>
              </div>
            </div>
            <div className="flex flex-col max-w-xs lg:max-w-md">
              <div className="text-xs mb-1 text-left text-gray-500">
                {loadingMessage || '입력 중...'}
              </div>
              <div className="px-4 py-3 rounded-2xl bg-white border border-gray-200 rounded-bl-md shadow-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

          {/* 스크롤을 위한 마커 */}
          <div ref={messagesEndRef} />
        </div>

        {/* 메시지 입력 영역 */}
        <div className="p-4 border-t border-gray-200 bg-white shrink-0">
          <div className="flex items-center space-x-3">
            <button
              onClick={handleAddClick}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </button>
            <button
              onClick={handleMicClick}
              className="p-2 hover:bg-purple-100 rounded-full transition-colors text-purple-500 hover:text-purple-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </button>
            {/* ⏩ Skip 버튼 - 타이핑 중일 때만 표시 */}
            {isTyping && !isAutoRequesting && (
              <button
                onClick={handleSkip}
                className="p-2 hover:bg-blue-100 rounded-full transition-colors text-blue-500 hover:text-blue-600 animate-pulse"
                title="대화 건너뛰기 (Skip)"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
              </button>
            )}
            {/* 🔧 긴급 리셋 버튼 */}
            {(isLoading || isTyping || isAutoRequesting) && (
              <button
                onClick={() => {
                  console.log('🔧 [RESET] Emergency reset triggered');
                  setIsAutoRequesting(false);
                  setIsTyping(false);
                  setIsLoading(false);
                  setLoadingMessage(null);
                  shouldCancelAutoRequest.current = true;
                  if (autoRequestTimerRef.current) {
                    clearTimeout(autoRequestTimerRef.current);
                    autoRequestTimerRef.current = null;
                  }
                  isAddingMessages.current = false;
                }}
                className="p-2 hover:bg-red-100 rounded-full transition-colors text-red-500 hover:text-red-600"
                title="입력 활성화 (긴급 리셋)"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault(); // 이벤트 중복 전파 방지
                    console.log('🔍 [ENTER KEY] Enter pressed!', {
                      inputMessage: inputMessage.substring(0, 20),
                      hasInput: !!inputMessage.trim(),
                      isLoading,
                      isTyping,
                      isAutoRequesting
                    });

                    if (!inputMessage.trim()) return;
                    if (isLoading || isTyping || isAutoRequesting) {
                      console.log('⚠️ [ENTER] Blocked by state checks');
                      return;
                    }

                    console.log('✅ [ENTER] Calling sendMessage');
                    sendMessage(inputMessage);
                  }
                }}
                onFocus={() => {
                  // 🔧 안전장치: 입력창 포커스 시 상태 리셋
                  console.log('🔍 [DEBUG] Input focused, current states:', {
                    isLoading,
                    isTyping,
                    isAutoRequesting
                  });
                  if (isAutoRequesting || isTyping) {
                    console.log('🔧 [FIX] Resetting stuck states');
                    setIsAutoRequesting(false);
                    setIsTyping(false);
                    setLoadingMessage(null);
                    shouldCancelAutoRequest.current = true;
                  }
                }}
                placeholder={isEnded ? "시나리오가 종료되었습니다" : (isAutoRequesting ? "대화가 자동으로 진행 중입니다..." : "메시지를 입력하세요...")}
                disabled={isLoading || isTyping || isAutoRequesting || isEnded}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-full text-gray-700 placeholder-gray-400 outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={() => {
                  console.log('🔍 [BUTTON CLICK] Send button clicked!', {
                    inputMessage: inputMessage.substring(0, 20),
                    hasInput: !!inputMessage.trim(),
                    isLoading,
                    isTyping,
                    isAutoRequesting
                  });

                  if (!inputMessage.trim()) {
                    console.log('⚠️ [BUTTON] No input message');
                    return;
                  }

                  if (isLoading) {
                    console.log('⚠️ [BUTTON] Blocked: isLoading=true');
                    return;
                  }

                  if (isTyping) {
                    console.log('⚠️ [BUTTON] Blocked: isTyping=true');
                    return;
                  }

                  if (isAutoRequesting) {
                    console.log('⚠️ [BUTTON] Blocked: isAutoRequesting=true');
                    return;
                  }

                  console.log('✅ [BUTTON] All checks passed, calling sendMessage');
                  sendMessage(inputMessage);
                }}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 text-purple-500 hover:text-purple-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!inputMessage.trim() || isLoading || isTyping || isAutoRequesting || isEnded}
              >
                {isLoading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-500"></div>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 캐릭터 선택 모달 */}
      <CharacterSelectionModal
        isOpen={showCharacterModal}
        onClose={() => setShowCharacterModal(false)}
        onSelectCharacter={handleCharacterSelect}
        onSelectFriend={handleFriendSelect}
        invitedCharacters={invitedCharacters}
      />

      {/* 엔딩 리워드 모달 */}
      {showEndingReward && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[10000]">
          <div className="bg-gradient-to-br from-purple-900 via-purple-800 to-indigo-900 rounded-3xl p-8 mx-4 max-w-2xl w-full shadow-2xl border-4 border-yellow-400">
            {/* 헤더 */}
            <div className="text-center mb-6">
              <h2 className="text-3xl font-bold text-yellow-400 mb-2">🎉 시나리오 클리어! 🎉</h2>
              <p className="text-purple-200 text-sm">숨겨진 엔딩 보상을 획득했습니다</p>
            </div>

            {/* 대화 요약 */}
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 mb-6 border-2 border-purple-400">
              <h3 className="text-xl font-bold text-yellow-300 mb-4">📜 여정의 기록</h3>
              <p className="text-white whitespace-pre-line leading-relaxed">
                {endingSummary}
              </p>
            </div>

            {/* 이미지 플레이스홀더 */}
            <div className="bg-gradient-to-br from-purple-600/30 to-indigo-600/30 rounded-xl p-8 mb-6 border-2 border-purple-400 flex flex-col items-center justify-center min-h-[200px]">
              <div className="animate-pulse mb-4">
                <svg className="w-16 h-16 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-yellow-300 text-center font-medium">
                🎨 귀멸의 칼날 스타일 이미지 생성 준비 중...
              </p>
              <p className="text-purple-300 text-sm text-center mt-2">
                백엔드 이미지 생성 API 연동 예정
              </p>
            </div>

            {/* 버튼 영역 */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowEndingReward(false)}
                className="flex-1 py-3 px-6 bg-white/20 text-white rounded-xl font-medium hover:bg-white/30 transition-all border-2 border-white/40"
              >
                계속 보기
              </button>
              <button
                onClick={() => {
                  setShowEndingReward(false);
                  // 홈으로 돌아가기 (페이지 새로고침)
                  window.location.reload();
                }}
                className="flex-1 py-3 px-6 bg-gradient-to-r from-yellow-400 to-yellow-500 text-purple-900 rounded-xl font-bold text-lg hover:from-yellow-300 hover:to-yellow-400 transition-all transform hover:scale-105 shadow-lg"
              >
                🏠 홈으로
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STT 음성 입력 모달 */}
      {showVoiceModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[9999]">
          <div className="bg-white rounded-3xl p-8 mx-4 max-w-md w-full shadow-2xl">
            {/* 헤더 */}
            <div className="text-center mb-6">
              <h3 className="text-xl font-bold text-gray-800 mb-2">음성 메시지</h3>
              <p className="text-gray-500 text-sm">
                {isListening ? '듣고 있습니다...' : '음성을 인식했습니다'}
              </p>
            </div>

            {/* 마이크 아이콘과 애니메이션 */}
            <div className="flex justify-center mb-6">
              <div className={`relative ${isListening ? 'animate-pulse' : ''}`}>
                {/* 파동 효과 */}
                {isListening && (
                  <>
                    <div className="absolute inset-0 rounded-full bg-purple-400/30 animate-ping"></div>
                    <div className="absolute inset-0 rounded-full bg-purple-400/20 animate-ping animation-delay-75"></div>
                    <div className="absolute inset-0 rounded-full bg-purple-400/10 animate-ping animation-delay-150"></div>
                  </>
                )}

                {/* 마이크 아이콘 */}
                <div className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 ${
                  isListening
                    ? 'bg-gradient-to-br from-purple-500 to-purple-600 shadow-lg shadow-purple-500/30'
                    : 'bg-gradient-to-br from-gray-400 to-gray-500'
                }`}>
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </div>
              </div>
            </div>

            {/* 인식된 텍스트 */}
            <div className="mb-6">
              <div className="min-h-[60px] p-4 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
                <p className={`text-center ${transcript ? 'text-gray-800' : 'text-gray-400'}`}>
                  {transcript || '음성을 입력해주세요...'}
                </p>
              </div>
            </div>

            {/* 버튼 영역 */}
            <div className="flex space-x-3">
              <button
                onClick={handleVoiceCancel}
                className="flex-1 py-3 px-4 bg-gray-100 text-gray-600 rounded-xl font-medium hover:bg-gray-200 transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleVoiceComplete}
                disabled={!transcript.trim()}
                className={`flex-1 py-3 px-4 rounded-xl font-medium transition-colors ${
                  transcript.trim()
                    ? 'bg-purple-500 text-white hover:bg-purple-600'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                전송
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Memory Update Log (Hover-based) */}
      <MemoryUpdateLog events={memoryEvents} />
    </div>
  );
}
