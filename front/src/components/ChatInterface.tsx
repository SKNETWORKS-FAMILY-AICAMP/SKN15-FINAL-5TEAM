
import { useState, useEffect, useRef, useMemo } from 'react';
import CharacterSelectionModal from './CharacterSelectionModal';
import BubbleCounter from './BubbleCounter';
import AffinityPanel from './AffinityPanel';
import { sendChatMessage, ChatResponse } from '@/services/api';
import { useBackgroundImage } from '@/hooks/useBackgroundImage';
import { useSoundEffects } from '@/hooks/useSoundEffects';

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
}

export default function ChatInterface({ onUserLogin, onMessageSent, characterId = 'ending' }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [showCharacterModal, setShowCharacterModal] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [invitedCharacters, setInvitedCharacters] = useState<string[]>(['tanjiro', 'inosuke', 'zenitsu', 'nezuko']); // 현재 참여중인 캐릭터들
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false); // 타이핑 중 표시
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null); // 로딩 메시지
  const [isAutoRequesting, setIsAutoRequesting] = useState(false); // 자동 요청 중
  const autoRequestTimerRef = useRef<number | null>(null); // 자동 요청 타이머
  const shouldCancelAutoRequest = useRef(false); // 사용자 중단 플래그
  const messageIdCounter = useRef(0); // 고유한 메시지 ID 생성용 카운터
  const isAddingMessages = useRef(false); // 메시지 추가 중 플래그 (중복 방지)
  const [affinityScores, setAffinityScores] = useState<Record<string, number>>({}); // 친밀도
  const [isTransitioning, setIsTransitioning] = useState(false); // 컷신 전환 효과

  // 가장 최근의 AI 메시지 ID 계산 (몰입감 향상을 위한 스케일 효과)
  const latestAiMessageId = useMemo(() => {
    // 역순으로 탐색하여 가장 최근의 비사용자, 비시스템 메시지 찾기
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (!msg.isUser && !msg.isSystemMessage) {
        return msg.id;
      }
    }
    return null;
  }, [messages]);

  // 배경 이미지 관리 (무한열차 시나리오)
  const {
    currentBackground,
    backgroundImageUrl,
    setBackgroundById,
    setBackgroundByIndex,
    preloadImages
  } = useBackgroundImage('mugen_train');

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

  // 백엔드 이미지 파일명 → 프론트엔드 인덱스 매핑
  const backendImageToIndex: Record<string, number> = {
    'default.png': 1,
    'cutscene_01_derail.png': 1,           // 무한열차 탈선
    'cutscene_02_battle_begins.png': 3,    // 전투 시작 (아카자 등장)
    'cutscene_03_fight_akaza.png': 6,      // 아카자와의 전투
    'cutscene_04_rengoku_sacrifice.png': 13, // 렌고쿠의 희생
    'cutscene_05_aftermath.png': 18,       // 전투 이후
  };

  // 백엔드 응답에서 받은 current_image를 처리하여 배경 변경 (페이드 효과 포함)
  const handleBackgroundChange = (currentImage: string | null) => {
    if (!currentImage) return;

    console.log(`🖼️ handleBackgroundChange called with: "${currentImage}"`);

    // 전환 효과 시작
    setIsTransitioning(true);

    // 500ms 후에 배경 변경
    setTimeout(() => {
      // 1. 숫자인 경우 인덱스로 처리
      const indexNum = parseInt(currentImage, 10);
      if (!isNaN(indexNum) && indexNum >= 1 && indexNum <= 21) {
        console.log(`  → Setting background by index: ${indexNum}`);
        setBackgroundByIndex(indexNum);
      }
      // 2. 백엔드 이미지 파일명인 경우 매핑된 인덱스로 처리
      else if (backendImageToIndex[currentImage]) {
        const mappedIndex = backendImageToIndex[currentImage];
        console.log(`  → Mapped backend image "${currentImage}" to index: ${mappedIndex}`);
        setBackgroundByIndex(mappedIndex);
      }
      // 3. ID로 처리 (예: "derailed_train", "battle_scene_01" 등)
      else {
        console.log(`  → Setting background by ID: ${currentImage}`);
        setBackgroundById(currentImage);
      }

      // 전환 효과 종료
      setIsTransitioning(false);
    }, 500);
  };

  // 캐릭터별 프로필 이미지 매핑 (백엔드 화자 ID -> 프로필 이미지)
  const getCharacterProfile = (charId: string) => {
    const profileMap: Record<string, string> = {
      'tanjiro': '/images/프로필_탄지로.png',
      'tanjirou': '/images/프로필_탄지로.png',
      'rengoku': '/images/프로필_렌고쿠.png',
      'zenitsu': '/images/프로필_젠이츠.png',
      'inosuke': '/images/프로필_이노스케.png',
      'nezuko': '/images/프로필_네즈코.png',
      'giyu': '/images/프로필_기유.png',
      'shinobu': '/images/프로필_시노부.png',
      'akaza': '/images/프로필_아카자.png',
      'system': '/images/프로필_시스템.png',
      'narr': '/images/프로필_시스템.png',
      'ending': '/images/프로필_네즈코.png',
    };
    return profileMap[charId.toLowerCase()] || '/images/프로필_탄지로.png';
  };

  // 캐릭터별 화자 이름 매핑 (백엔드 화자 ID -> 한글 이름)
  const getCharacterName = (charId: string) => {
    const nameMap: Record<string, string> = {
      'tanjiro': '탄지로',
      'tanjirou': '탄지로',
      'rengoku': '렌고쿠',
      'zenitsu': '젠이츠',
      'inosuke': '이노스케',
      'nezuko': '네즈코',
      'giyu': '기유',
      'shinobu': '시노부',
      'akaza': '아카자',
      'system': '시스템',
      'narr': '시스템', // 내레이터를 시스템으로 통합
      'ending': '네즈코',
    };
    return nameMap[charId.toLowerCase()] || charId;
  };

  // 캐릭터별 글로우 색상 매핑 (몰입감 향상)
  const getCharacterGlowColor = (charId: string) => {
    const colorMap: Record<string, { primary: string; shadow: string; bg: string }> = {
      'tanjiro': {
        primary: '#EF4444',
        shadow: 'rgba(239, 68, 68, 0.6)',
        bg: 'linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03))'
      },
      'tanjirou': {
        primary: '#EF4444',
        shadow: 'rgba(239, 68, 68, 0.6)',
        bg: 'linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03))'
      },
      'rengoku': {
        primary: '#F59E0B',
        shadow: 'rgba(245, 158, 11, 0.6)',
        bg: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03))'
      },
      'zenitsu': {
        primary: '#FBBF24',
        shadow: 'rgba(251, 191, 36, 0.6)',
        bg: 'linear-gradient(135deg, rgba(251, 191, 36, 0.08), rgba(251, 191, 36, 0.03))'
      },
      'inosuke': {
        primary: '#10B981',
        shadow: 'rgba(16, 185, 129, 0.6)',
        bg: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.03))'
      },
      'nezuko': {
        primary: '#EC4899',
        shadow: 'rgba(236, 72, 153, 0.6)',
        bg: 'linear-gradient(135deg, rgba(236, 72, 153, 0.08), rgba(236, 72, 153, 0.03))'
      },
      'akaza': {
        primary: '#A855F7',
        shadow: 'rgba(168, 85, 247, 0.6)',
        bg: 'linear-gradient(135deg, rgba(168, 85, 247, 0.08), rgba(168, 85, 247, 0.03))'
      },
      'giyu': {
        primary: '#3B82F6',
        shadow: 'rgba(59, 130, 246, 0.6)',
        bg: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(59, 130, 246, 0.03))'
      },
      'shinobu': {
        primary: '#8B5CF6',
        shadow: 'rgba(139, 92, 246, 0.6)',
        bg: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08), rgba(139, 92, 246, 0.03))'
      },
    };
    return colorMap[charId.toLowerCase()] || {
      primary: '#6B7280',
      shadow: 'rgba(107, 114, 128, 0.4)',
      bg: 'linear-gradient(135deg, rgba(107, 114, 128, 0.05), rgba(107, 114, 128, 0.02))'
    };
  };

  // 로딩 메시지 목록 (상황별로 다양하게)
  const getRandomLoadingMessage = () => {
    const loadingMessages = [
      '탄지로가 심각한 표정을 지으며 생각하고 있어요...',
      '렌고쿠가 무언가를 결정하려 하고 있어요...',
      '아카자가 주변을 살피고 있어요...',
      '긴장감이 흐르고 있어요...',
      '동료들이 상황을 파악하고 있어요...',
      '잠시 후 대화가 이어집니다...',
    ];
    return loadingMessages[Math.floor(Math.random() * loadingMessages.length)];
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

  // 메시지 스크롤 자동화
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]); // 메시지 변경 또는 타이핑 상태 변경 시 스크롤

  // 타이핑 효과와 함께 메시지를 표시하는 함수 (50ms per character)
  const addMessageWithTypingEffect = async (message: Message): Promise<void> => {
    return new Promise((resolve) => {
      // 이 메시지에 배경 이미지 변경 요청이 있으면 먼저 처리
      if (message.imageIndex) {
        const imageIndex = parseInt(message.imageIndex);
        console.log(`🖼️ [Frontend] Changing background to image ${imageIndex} for message: ${message.text.substring(0, 30)}...`);
        setBackgroundByIndex(imageIndex);
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

      // 타이핑 효과: 50ms마다 한 글자씩 추가
      const chars = message.text.split('');
      let currentIndex = 0;

      const typingInterval = setInterval(() => {
        currentIndex++;
        const typedText = chars.slice(0, currentIndex).join('');

        setMessages(prev => prev.map(msg =>
          msg.id === messageId ? { ...msg, text: typedText } : msg
        ));

        if (currentIndex >= chars.length) {
          clearInterval(typingInterval);
          resolve();
        }
      }, 10); // 50ms per character
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

    isAddingMessages.current = true;
    setIsTyping(true);

    console.log(`📝 Adding ${newMessages.length} messages sequentially...`);

    for (let i = 0; i < newMessages.length; i++) {
      // 사용자가 중단을 요청했는지 확인
      if (shouldCancelAutoRequest.current) {
        console.log('⚠️ User cancelled, stopping message display');
        break;
      }

      console.log(`  → Message ${i + 1}/${newMessages.length}: ${newMessages[i].characterId} - ${newMessages[i].text.substring(0, 30)}...`);

      // 타이핑 효과로 메시지 표시
      await addMessageWithTypingEffect(newMessages[i]);

      // 마지막 메시지가 아니면 2.5초 대기
      if (i < newMessages.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 2500)); // 2.5 seconds
      }
    }

    setIsTyping(false);
    isAddingMessages.current = false;
    console.log('✅ Finished adding messages');
  };

  // 자동 요청 함수 (has_more가 true일 때 호출)
  const handleAutoRequest = async (currentSessionId: string, retryCount: number = 0) => {
    // 최대 재시도 횟수 체크
    if (retryCount >= 3) {
      console.error('Max retry attempts reached');
      setLoadingMessage(null);
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
        characterId,
        '__AUTO_CONTINUE__',
        currentSessionId,
        '츠고쿠'
      );

      setLoadingMessage(null);

      console.log(`📥 Received ${response.dialogues.length} dialogues, has_more: ${response.has_more}`);

      // Update affinity_scores from response
      // Note: background changes are now handled per-dialogue via imageIndex
      // handleBackgroundChange(response.current_image || null); // ← REMOVED: current_image is final state, not initial
      setAffinityScores(response.affinity_scores || {});

      // 백엔드 응답을 메시지로 변환 (고유 ID 사용)
      const backendMessages: Message[] = response.dialogues.map((dialogue) => ({
        id: generateMessageId(),
        text: dialogue.text || dialogue.content || '',  // 백엔드는 text 필드 사용
        isUser: false,
        timestamp: new Date(),
        characterId: dialogue.speaker,
        isSystemMessage: dialogue.speaker === 'system' || dialogue.speaker === 'narr',
        imageIndex: dialogue.image_index  // 배경 이미지 인덱스
      }));

      // 순차적으로 메시지 표시 (타이핑 효과 포함)
      await addMessagesSequentially(backendMessages);

      // has_more가 true이면 계속 자동 요청
      if (response.has_more && !shouldCancelAutoRequest.current) {
        console.log('🔄 has_more is true, scheduling next auto-request in 2.5s...');
        // 2.5초 후 다음 배치 요청
        autoRequestTimerRef.current = window.setTimeout(() => {
          handleAutoRequest(response.session_id, 0); // 성공 시 재시도 카운트 리셋
        }, 2500);
      } else {
        console.log(`✅ Auto-request complete. has_more: ${response.has_more}, cancelled: ${shouldCancelAutoRequest.current}`);
        setIsAutoRequesting(false);
      }
    } catch (error) {
      console.error(`Auto request failed (attempt ${retryCount + 1}/3):`, error);

      // 재시도
      autoRequestTimerRef.current = window.setTimeout(() => {
        handleAutoRequest(currentSessionId, retryCount + 1);
      }, 1000 * (retryCount + 1)); // Exponential backoff: 1s, 2s, 3s
    }
  };

  // 초기 시나리오 로드 (백엔드 연결)
  useEffect(() => {
    const initializeChat = async () => {
      setIsLoading(true);
      setBackendError(null);

      try {
        // 첫 메시지로 대화 시작 (시나리오 초기화)
        const response: ChatResponse = await sendChatMessage(
          characterId,
          '시작',  // Initial trigger message
          undefined,
          '츠고쿠'
        );

        // 세션 ID 저장
        setSessionId(response.session_id);

        console.log(`🎬 Initial response: ${response.dialogues.length} dialogues, has_more: ${response.has_more}`);

        // Update affinity_scores from response
        // Note: background changes are now handled per-dialogue via imageIndex
        // handleBackgroundChange(response.current_image || null); // ← REMOVED: current_image is final state, not initial
        setAffinityScores(response.affinity_scores || {});

        // 백엔드 응답을 메시지로 변환 (고유 ID 사용)
        const backendMessages: Message[] = response.dialogues.map((dialogue) => ({
          id: generateMessageId(),
          text: dialogue.text || dialogue.content || '',  // 백엔드는 text 필드 사용
          isUser: false,
          timestamp: new Date(),
          characterId: dialogue.speaker,
          isSystemMessage: dialogue.speaker === 'system' || dialogue.speaker === 'narr',
          imageIndex: dialogue.image_index  // 배경 이미지 인덱스
        }));

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
  }, [characterId]); // Re-initialize when characterId changes

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

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    // 🔊 오디오 활성화 (브라우저 자동재생 정책 우회)
    // unlock이 완전히 완료될 때까지 기다림
    await unlockAudio();

    // 🔥 자동 요청 중일 때는 사용자 입력 차단
    if (isAutoRequesting) {
      console.log('⚠️ Auto-requesting in progress, user input blocked');
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
        characterId,
        text,
        sessionId,
        '츠고쿠'
      );

      // Update session ID if it changed
      if (response.session_id !== sessionId) {
        setSessionId(response.session_id);
      }

      // Update affinity_scores from response
      // Note: background changes are now handled per-dialogue via imageIndex
      // handleBackgroundChange(response.current_image || null); // ← REMOVED: current_image is final state, not initial
      setAffinityScores(response.affinity_scores || {});

      // Add backend responses to messages sequentially (고유 ID 사용)
      const backendMessages: Message[] = response.dialogues.map((dialogue) => ({
        id: generateMessageId(),
        text: dialogue.text || dialogue.content || '',  // 백엔드는 text 필드 사용
        isUser: false,
        timestamp: new Date(),
        characterId: dialogue.speaker,
        isSystemMessage: dialogue.speaker === 'system' || dialogue.speaker === 'narr',
        imageIndex: dialogue.image_index  // 배경 이미지 인덱스
      }));

      // 시스템 메시지와 종료 메시지를 백엔드 메시지에 추가
      const allMessages = [...backendMessages];

      // Show system message if provided
      if (response.system_message) {
        allMessages.push({
          id: Date.now() + backendMessages.length + 1,
          text: response.system_message,
          isUser: false,
          timestamp: new Date(),
          characterId: 'system',
          isSystemMessage: true
        });
      }

      // Check if chat has ended
      if (response.is_ended) {
        allMessages.push({
          id: Date.now() + backendMessages.length + 2,
          text: '🎬 시나리오가 종료되었습니다. 새로운 시나리오를 시작하려면 페이지를 새로고침 해주세요.',
          isUser: false,
          timestamp: new Date(),
          characterId: 'system',
          isSystemMessage: true
        });
      }

      // 순차적으로 메시지 표시 (타이핑 효과 포함)
      await addMessagesSequentially(allMessages);

      // has_more가 true이면 자동 요청 시작
      if (response.has_more) {
        handleAutoRequest(response.session_id);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setBackendError('메시지 전송에 실패했습니다.');

      // Show error message
      const errorMessage: Message = {
        id: Date.now() + 1,
        text: '⚠️ 메시지 전송에 실패했습니다. 다시 시도해주세요.',
        isUser: false,
        timestamp: new Date(),
        characterId: 'system',
        isSystemMessage: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
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
            isUser: scene.characterId === 'user',
            timestamp: new Date(),
            characterId: scene.characterId === 'user' ? undefined : scene.characterId,
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

  return (
    <div className="w-full h-full flex flex-col md:flex-row bg-gray-100">
      {/* 왼쪽: 컷신 이미지 영역 (50%) */}
      <div className="relative w-full md:w-1/2 h-[40vh] md:h-full overflow-hidden">
        {/* 컷신 배경 이미지 */}
        <div
          className={`w-full h-full bg-cover bg-center bg-no-repeat transition-opacity duration-500 ${
            isTransitioning ? 'opacity-0' : 'opacity-100'
          }`}
          style={{
            backgroundImage: backgroundImageUrl
              ? `url(${backgroundImageUrl})`
              : 'url(/images/무한열차.jpeg)'  // 초기 로딩: 무한열차 카드 이미지
          }}
        />

        {/* 하단 패널: 친밀도 (가로로 넓게) + 버블 (오른쪽) */}
        <div className="absolute bottom-4 left-4 right-4 z-10 flex gap-3 items-end">
          {/* 친밀도 패널 - 버블 옆까지 가로로 확장 */}
          <div className="flex-1">
            <AffinityPanel affinityScores={affinityScores} />
          </div>

          {/* 버블 카운터 */}
          <div className="flex-shrink-0">
            <BubbleCounter compact />
          </div>
        </div>
      </div>

      {/* 오른쪽: 채팅 영역 (50%) */}
      <div className="w-full md:w-1/2 h-[60vh] md:h-full flex flex-col bg-white">
        {/* 채팅 헤더 - 높이 축소 */}
        <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-200 bg-white shrink-0 gap-4">
          {/* 중앙: Kime Chat */}
          <div className="flex items-center flex-1 justify-center">
            <span className="text-base font-roboto text-text-primary">
              🗡️ Kime Chat
            </span>
          </div>

          {/* 오른쪽: 참여중인 캐릭터들 */}
          <div className="flex items-center space-x-1">
            {invitedCharacters.map((charId, index) => (
              <div key={charId} className="relative">
                <img
                  src={getCharacterProfile(charId)}
                  alt={getCharacterName(charId)}
                  className="w-6 h-6 rounded-full border-2 border-white shadow-sm"
                  style={{ marginLeft: index > 0 ? '-6px' : '0' }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = '/images/프로필_탄지로.png';
                  }}
                />
              </div>
            ))}
            {invitedCharacters.length > 1 && (
              <span className="text-xs text-gray-500 ml-2">
                {invitedCharacters.length}명
              </span>
            )}
          </div>
        </div>

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
        {messages.map((message) => {
          // 시스템 메시지 렌더링
          if (message.isSystemMessage) {
            return (
              <div key={message.id} className="flex justify-center mb-4">
                <div className="max-w-lg">
                  <div className="bg-gradient-to-r from-pink-50 via-purple-50 to-blue-50 border border-purple-200 rounded-xl px-4 py-3 shadow-sm">
                    <p className="text-center text-sm text-gray-700 leading-relaxed italic">
                      {message.text}
                    </p>
                    <div className="text-xs text-center text-gray-400 mt-1">
                      {message.timestamp.toLocaleTimeString('ko-KR', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>
                </div>
              </div>
            );
          }

          // 일반 메시지 렌더링
          const isLatestMessage = message.id === latestAiMessageId;
          const glowColors = getCharacterGlowColor(message.characterId || characterId);

          return (
            <div key={message.id} className={`flex ${message.isUser ? 'justify-end' : 'justify-start'} mb-4 ${!message.isUser ? 'animate-slide-in-fade' : ''}`}>
              {!message.isUser && (
                <div
                  className={`w-16 h-16 rounded-full mr-3 flex-shrink-0 transition-all duration-500`}
                  style={isLatestMessage ? {
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
              <div className="flex flex-col max-w-xs lg:max-w-md">
                {/* 화자 표시 */}
                <div className={`text-xs mb-1 ${message.isUser ? 'text-right text-gray-500' : 'text-left text-gray-500'}`}>
                  {message.isUser ? '사용자' : getCharacterName(message.characterId || characterId)}
                </div>

                <div className="flex items-start">
                  <div
                    className={`px-4 py-3 rounded-2xl flex-1 transition-all duration-500 ${
                      message.isUser
                        ? 'bg-purple-500 text-white rounded-br-md'
                        : `text-gray-800 border border-gray-200 rounded-bl-md ${isLatestMessage ? '' : 'bg-white shadow-sm'}`
                    }`}
                    style={!message.isUser && isLatestMessage ? {
                      background: `${glowColors.bg}, white`,
                      boxShadow: `0 4px 20px ${glowColors.shadow.replace('0.6', '0.25')}, 0 8px 40px ${glowColors.shadow.replace('0.6', '0.15')}`
                    } : {}}
                  >
                    <p className="text-sm leading-relaxed">{message.text}</p>
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
                      onClick={() => handlePlayAudio(message.text)}
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
                <div className="w-16 h-16 rounded-full ml-3 flex-shrink-0">
                  <div className="w-full h-full rounded-full bg-purple-600 flex items-center justify-center text-white font-medium">
                    U
                  </div>
                </div>
              )}
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
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && inputMessage.trim() && !isLoading && !isTyping && !isAutoRequesting && sendMessage(inputMessage)}
                placeholder={isAutoRequesting ? "대화가 자동으로 진행 중입니다..." : "메시지를 입력하세요..."}
                disabled={isLoading || isTyping || isAutoRequesting}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-full text-gray-700 placeholder-gray-400 outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={() => inputMessage.trim() && !isLoading && !isTyping && !isAutoRequesting && sendMessage(inputMessage)}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 text-purple-500 hover:text-purple-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!inputMessage.trim() || isLoading || isTyping || isAutoRequesting}
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
    </div>
  );
}