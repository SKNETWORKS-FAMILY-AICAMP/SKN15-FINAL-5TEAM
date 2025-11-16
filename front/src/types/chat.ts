/**
 * Chat Types
 * 채팅 관련 타입 정의
 */

export interface Message {
  id: number;
  text: string;
  isUser: boolean;
  timestamp: Date;
  characterId?: string;
  isSystemMessage?: boolean;
  imageIndex?: string;
}

export interface BackgroundImage {
  index: string;
  fileName: string;
  url: string;
}

export interface ChatResponse {
  session_id: string;
  dialogues: Dialogue[];
  has_more?: boolean;
  agent_messages?: Array<{ text: string }>;
  stage_id?: string;
  invited_characters?: string[];
  affinity_changes?: Record<string, number>;
  image_index?: string;
  is_ended?: boolean;
  ending_summary?: string;
}

export interface Dialogue {
  speaker: string;
  text: string;
  is_user?: boolean;  // ✅ 백엔드에서 명시적으로 전달하는 필드
  emotion?: string;
  timestamp?: string;
}

export interface AffinityScore {
  characterId: string;
  score: number;
  level: number;
}
