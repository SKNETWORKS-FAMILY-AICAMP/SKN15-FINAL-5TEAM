/**
 * API Service Layer
 * Handles all backend communication for KIME Chat
 */

import axios from 'axios'
import authenticatedApiClient from '@/utils/apiClient'

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ============================================================
// Types
// ============================================================

export interface ChatMessage {
  speaker: string
  text: string  // 백엔드는 'text' 필드 사용
  content?: string  // 하위 호환성
  emotion?: string
  timestamp?: string
  fx?: string | null
  image_index?: string
  affinity_level?: string
  emotion_intensity?: string
}

export interface ChatRequest {
  session_id?: string
  scenario_id: string
  user_input: string
  user_name?: string
}

export interface ChatResponse {
  session_id: string
  turn_count: number
  dialogues: ChatMessage[]
  current_stage?: string
  affinity_scores?: Record<string, number>
  is_ended: boolean
  has_more: boolean  // 더 생성할 대화가 있는지 여부 (배치 모드)
  system_message?: string
  current_image?: string  // 현재 표시할 이미지 경로 (ImageManager 제공)
  output?: Record<string, unknown>
}

export interface SessionInfo {
  session_id: string
  scenario_id: string
  current_stage?: string
  turn_count: number
  affinity_scores: Record<string, number>
}

export interface ScenarioInfo {
  id: string
}

export interface LastSessionInfo {
  sessionId: string
  scenarioId: string
  currentStage?: string
  turnCount: number
  createdAt?: string
  updatedAt?: string
  conversationSummary?: string
}

export interface UserInfo {
  user_id: string
  username: string
  display_name: string
}

export interface UserCredits {
  bubble_count: number
  total_purchased: number
  total_consumed: number
  last_updated?: string
}

export interface UserProgression {
  user_id: string
  rank_code: string
  rank_name_ko: string
  rank_icon: string
  experience_points: number
  level: number
  next_rank_xp: number
  total_messages: number
  total_sessions: number
  total_play_minutes: number
  scenarios_completed: number
  achievements_count: number
  sword_status: string
  uniform_status: string
  crow_status: string
  updated_at?: string
}

export interface UserEquipment {
  sword_status: string
  uniform_status: string
  crow_status: string
  sword_type?: string
  uniform_color?: string
  crow_name?: string
}

export interface XPTransaction {
  transaction_id: string
  xp_amount: number
  xp_type: string
  xp_balance_after: number
  level_before: number
  level_after: number
  did_level_up: boolean
  description?: string
  created_at: string
}

export interface LeaderboardEntry {
  rank: number
  user_id: string
  username: string
  display_name: string
  rank_code: string
  rank_name_ko: string
  rank_icon: string
  experience_points: number
  level: number
  total_messages: number
  scenarios_completed: number
}

// Scenario interfaces
export interface ScenarioCard {
  scenario_id: string
  title: string
  description: string
  image_url: string
  thumbnail_url?: string
  tags: string[]
  card_size: 'large' | 'normal'
  route_path: string
  display_order: number
  is_active: boolean
  likes: number
  comments: number
  views: number
  chat_sessions?: number
  total_messages?: number
  average_affinity_score?: number
  bubble_reward?: number
  bubble_cost?: number
  total_completions?: number
  // User-specific fields (if authenticated)
  is_liked?: boolean
  has_started?: boolean
  has_completed?: boolean
  completion_percentage?: number
  last_played_at?: string
}

export interface ScenarioProgress {
  user_id: string
  scenario_id: string
  has_started: boolean
  has_completed: boolean
  completion_percentage: number
  last_session_id?: string
  last_played_at?: string
  total_messages: number
  total_play_time: number
  is_liked: boolean
}

export interface LiveStats {
  total_likes: number
  total_comments: number
  total_chats: number
  active_chat_sessions: number
  avg_affinity_score: number
  bubble_circulation: number
  last_updated: string
}

export interface ScenarioMetrics {
  scenario_id: string
  likes: number
  comments: number
  chat_sessions: number
  total_messages: number
  avg_affinity: number
  bubble_reward: number
  bubble_cost?: number
  last_updated?: string
}

export interface ScenarioComment {
  comment_id: string
  scenario_id: string
  user_id: string
  username: string
  display_name?: string
  avatar_url?: string
  content: string
  like_count?: number
  is_liked?: boolean
  is_owner?: boolean
  created_at: string
  updated_at?: string
}

export interface ScenarioCommentList {
  items: ScenarioComment[]
  next_cursor: string | null
  total_count: number
}

export interface ScenarioCommentPayload {
  content: string
  parent_comment_id?: string
}

// ============================================================
// API Client
// ============================================================

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  /**
   * Send chat message and get response (with JWT authentication)
   */
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      // Use authenticated API client (automatically adds JWT token)
      const response = await authenticatedApiClient.post('/api/chat', request)
      return response.data
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    }
  }

  /**
   * Get session information (with JWT authentication)
   */
  async getSession(sessionId: string): Promise<SessionInfo> {
    try {
      const response = await authenticatedApiClient.get(`/api/session/${sessionId}`)
      return response.data
    } catch (error) {
      console.error('Error getting session:', error)
      throw error
    }
  }

  /**
   * Delete a session (with JWT authentication)
   */
  async deleteSession(sessionId: string): Promise<void> {
    try {
      await authenticatedApiClient.delete(`/api/session/${sessionId}`)
    } catch (error) {
      console.error('Error deleting session:', error)
      throw error
    }
  }

  /**
   * List available scenarios (with JWT authentication)
   */
  async listScenarios(): Promise<ScenarioInfo[]> {
    try {
      const response = await authenticatedApiClient.get('/api/scenarios')
      return response.data.scenarios
    } catch (error) {
      console.error('Error listing scenarios:', error)
      throw error
    }
  }

  /**
   * Health check (no authentication required)
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await authenticatedApiClient.get('/')
      return response.status === 200
    } catch (error) {
      console.error('Health check failed:', error)
      return false
    }
  }

  /**
   * Get user's last session (with JWT authentication)
   */
  async getUserLastSession(scenarioId?: string): Promise<LastSessionInfo | null> {
    try {
      const params = scenarioId ? { scenario_id: scenarioId } : {}
      const response = await authenticatedApiClient.get('/api/session/last', { params })

      if (response.data.has_session) {
        return {
          sessionId: response.data.session_id,
          scenarioId: response.data.scenario_id,
          currentStage: response.data.current_stage,
          turnCount: response.data.turn_count,
          createdAt: response.data.created_at,
          updatedAt: response.data.updated_at,
          conversationSummary: response.data.conversation_summary
        }
      }
      return null
    } catch (error) {
      console.error('Error getting last session:', error)
      return null
    }
  }

  /**
   * Get current user information (with JWT authentication)
   */
  async getCurrentUser(): Promise<UserInfo> {
    try {
      const response = await authenticatedApiClient.get('/api/auth/me')
      return response.data
    } catch (error) {
      console.error('Error getting current user:', error)
      throw error
    }
  }

  /**
   * Request password reset (no authentication required)
   */
  async requestPasswordReset(email: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/password-reset/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('Error requesting password reset:', error)
      throw error
    }
  }

  /**
   * Confirm password reset with token (no authentication required)
   */
  async confirmPasswordReset(token: string, newPassword: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/password-reset/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword })
      })
      const data = await response.json()

      if (!response.ok) {
        // Handle HTTP errors (400, 500, etc.)
        throw new Error(data.detail || '비밀번호 재설정에 실패했습니다.')
      }

      return data
    } catch (error) {
      console.error('Error confirming password reset:', error)
      throw error
    }
  }

  /**
   * Get user credits (bubble count)
   */
  async getUserCredits(): Promise<UserCredits> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/credits')
      return response.data
    } catch (error) {
      console.error('Error getting user credits:', error)
      throw error
    }
  }

  /**
   * Consume user credits
   */
  async consumeCredits(amount: number, description: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await authenticatedApiClient.post('/api/users/me/credits/consume', {
        amount,
        description
      })
      return response.data
    } catch (error) {
      console.error('Error consuming credits:', error)
      throw error
    }
  }

  // ============================================================
  // User Progression Methods
  // ============================================================

  /**
   * Get user progression (rank, level, XP, stats, equipment)
   */
  async getUserProgression(): Promise<UserProgression> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/progression')
      return response.data
    } catch (error) {
      console.error('Error getting user progression:', error)
      throw error
    }
  }

  /**
   * Get user equipment status
   */
  async getUserEquipment(): Promise<UserEquipment> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/equipment')
      return response.data
    } catch (error) {
      console.error('Error getting user equipment:', error)
      throw error
    }
  }

  /**
   * Award experience points (internal API - typically called by backend)
   */
  async awardXP(
    xpAmount: number,
    xpType: string,
    description?: string,
    metadata?: Record<string, any>
  ): Promise<{
    user_id: string
    experience_points: number
    level: number
    level_before: number
    level_after: number
    did_level_up: boolean
  }> {
    try {
      const response = await authenticatedApiClient.post('/api/users/me/progression/award-xp', {
        xp_amount: xpAmount,
        xp_type: xpType,
        description,
        metadata
      })
      return response.data
    } catch (error) {
      console.error('Error awarding XP:', error)
      throw error
    }
  }

  /**
   * Update user equipment status
   */
  async updateEquipment(equipmentUpdates: Record<string, string>): Promise<{ success: boolean }> {
    try {
      const response = await authenticatedApiClient.put('/api/users/me/equipment', {
        equipment_updates: equipmentUpdates
      })
      return response.data
    } catch (error) {
      console.error('Error updating equipment:', error)
      throw error
    }
  }

  /**
   * Get XP transaction history (paginated)
   */
  async getXPTransactions(limit: number = 50, offset: number = 0): Promise<XPTransaction[]> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/xp-transactions', {
        params: { limit, offset }
      })
      return response.data
    } catch (error) {
      console.error('Error getting XP transactions:', error)
      throw error
    }
  }

  /**
   * Get global leaderboard (public API, no JWT required)
   */
  async getLeaderboard(limit: number = 100): Promise<LeaderboardEntry[]> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/leaderboard`, {
        params: { limit }
      })
      return response.data
    } catch (error) {
      console.error('Error getting leaderboard:', error)
      throw error
    }
  }

  // ============================================================
  // Scenario Management Methods
  // ============================================================

  /**
   * Get realtime landing-page stats
   */
  async getLiveStats(): Promise<LiveStats> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/stats/live`)
      return response.data
    } catch (error) {
      console.error('Error getting live stats:', error)
      throw error
    }
  }

  /**
   * Get all scenarios (public API, no JWT required)
   */
  async getScenarios(): Promise<ScenarioCard[]> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/scenarios`)
      return response.data
    } catch (error) {
      console.error('Error getting scenarios:', error)
      throw error
    }
  }

  /**
   * Get specific scenario by ID (public API)
   */
  async getScenario(scenarioId: string): Promise<ScenarioCard> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/scenarios/${scenarioId}`)
      return response.data
    } catch (error) {
      console.error(`Error getting scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Record scenario view (public API, auth optional)
   */
  async recordScenarioView(scenarioId: string): Promise<{ success: boolean }> {
    try {
      // Try with auth first if user is logged in
      const response = await authenticatedApiClient.post(`/api/scenarios/${scenarioId}/view`)
      return response.data
    } catch (error) {
      // Fallback to public API if not authenticated
      try {
        const response = await axios.post(`${this.baseUrl}/api/scenarios/${scenarioId}/view`)
        return response.data
      } catch (fallbackError) {
        console.error(`Error recording view for scenario ${scenarioId}:`, fallbackError)
        throw fallbackError
      }
    }
  }

  /**
   * Get scenarios with user progress (requires JWT)
   */
  async getUserScenarios(): Promise<ScenarioCard[]> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/scenarios')
      return response.data
    } catch (error) {
      console.error('Error getting user scenarios:', error)
      throw error
    }
  }

  /**
   * Toggle like for scenario (requires JWT)
   */
  async toggleScenarioLike(scenarioId: string): Promise<{ liked: boolean, total_likes: number }> {
    try {
      const response = await authenticatedApiClient.post(`/api/users/me/scenarios/${scenarioId}/like`)
      return response.data
    } catch (error) {
      console.error(`Error toggling like for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Get scenario-level metrics (public API)
   */
  async getScenarioMetrics(scenarioId: string): Promise<ScenarioMetrics> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/scenarios/${scenarioId}/metrics`)
      return response.data
    } catch (error) {
      console.error(`Error getting metrics for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Get comments for a scenario (public API)
   */
  async getScenarioComments(
    scenarioId: string,
    params: { cursor?: string; limit?: number } = {}
  ): Promise<ScenarioCommentList> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/scenarios/${scenarioId}/comments`, {
        params
      })
      return response.data
    } catch (error) {
      console.error(`Error getting comments for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Create a new scenario comment (requires JWT)
   */
  async createScenarioComment(
    scenarioId: string,
    payload: ScenarioCommentPayload
  ): Promise<ScenarioComment> {
    try {
      const response = await authenticatedApiClient.post(
        `/api/scenarios/${scenarioId}/comments`,
        payload
      )
      return response.data
    } catch (error) {
      console.error(`Error creating comment for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Update an existing comment (requires JWT)
   */
  async updateScenarioComment(
    scenarioId: string,
    commentId: string,
    payload: ScenarioCommentPayload
  ): Promise<ScenarioComment> {
    try {
      const response = await authenticatedApiClient.put(
        `/api/scenarios/${scenarioId}/comments/${commentId}`,
        payload
      )
      return response.data
    } catch (error) {
      console.error(`Error updating comment ${commentId} for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Delete a comment (requires JWT)
   */
  async deleteScenarioComment(scenarioId: string, commentId: string): Promise<{ success: boolean }> {
    try {
      const response = await authenticatedApiClient.delete(
        `/api/scenarios/${scenarioId}/comments/${commentId}`
      )
      return response.data
    } catch (error) {
      console.error(`Error deleting comment ${commentId} for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Get user progress for specific scenario (requires JWT)
   */
  async getScenarioProgress(scenarioId: string): Promise<ScenarioProgress> {
    try {
      const response = await authenticatedApiClient.get(`/api/users/me/scenarios/${scenarioId}/progress`)
      return response.data
    } catch (error) {
      console.error(`Error getting progress for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Update user progress for scenario (requires JWT)
   */
  async updateScenarioProgress(
    scenarioId: string,
    progressData: Partial<ScenarioProgress>
  ): Promise<{ success: boolean }> {
    try {
      const response = await authenticatedApiClient.put(
        `/api/users/me/scenarios/${scenarioId}/progress`,
        progressData
      )
      return response.data
    } catch (error) {
      console.error(`Error updating progress for scenario ${scenarioId}:`, error)
      throw error
    }
  }
}

// ============================================================
// Export singleton instance
// ============================================================

export const apiClient = new ApiClient()

// ============================================================
// Convenience functions
// ============================================================

/**
 * Send a chat message
 */
import { getAccessToken, getRefreshToken, getTokenType, isTokenExpired } from '../utils/authUtils';

// This is a standalone token refresh function to be used with fetch
async function ensureValidToken(): Promise<string | null> {
  let accessToken = getAccessToken();

  // A simple check for expiration. The original interceptor logic was more complex.
  if (!accessToken || isTokenExpired(accessToken)) {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      console.error("No refresh token available. Cannot refresh.");
      return null;
    }

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Token refresh request failed');
      }
      
      const newTokens = await response.json();
      // Mimic original interceptor behavior: only set the new access token.
      localStorage.setItem('access_token', newTokens.access_token);
      // The old refresh token remains valid.
      accessToken = newTokens.access_token;
    } catch (error) {
      console.error("Failed to refresh token:", error);
      return null;
    }
  }
  return accessToken;
}

/**
 * Send a chat message
 */
export async function* sendChatMessage(
  scenarioId: string,
  userInput: string,
  sessionId?: string,
  userName?: string
): AsyncGenerator<any> {
  const token = await ensureValidToken();

  if (!token) {
    throw new Error('Authentication failed: Could not obtain a valid token.');
  }

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const tokenType = getTokenType() || 'Bearer';

  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `${tokenType} ${token}`,
    },
    body: JSON.stringify({
      session_id: sessionId,
      scenario_id: scenarioId,
      user_input: userInput,
      user_name: userName,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error('API request failed:', errorText);
    throw new Error(`API request failed with status ${response.status}`);
  }

  if (!response.body) {
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent: string | null = null;
  let dataBuffer: string[] = [];

  const flushEvent = () => {
    if (dataBuffer.length === 0) {
      return null;
    }

    const dataString = dataBuffer.join('\n');
    let payload: any;
    try {
      payload = dataString ? JSON.parse(dataString) : {};
    } catch (e) {
      console.error('Failed to parse stream chunk:', dataString, e);
      payload = { raw: dataString };
    }

    const type = currentEvent || 'message';
    const chunk =
      payload && typeof payload === 'object' && !Array.isArray(payload)
        ? { type, ...payload }
        : { type, data: payload };

    dataBuffer = [];
    currentEvent = null;
    return chunk;
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      if (buffer.length > 0) {
        const trimmed = buffer.trim();
        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim() || null;
        } else if (trimmed.startsWith('data:')) {
          dataBuffer.push(trimmed.slice(5).trim());
        }
        buffer = '';
      }

      const finalChunk = flushEvent();
      if (finalChunk) {
        yield finalChunk;
      }
      break;
    }
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();

      if (line.length === 0) {
        const chunk = flushEvent();
        if (chunk) {
          yield chunk;
        }
        continue;
      }

      if (line.startsWith('event:')) {
        const chunk = flushEvent();
        if (chunk) {
          yield chunk;
        }
        currentEvent = line.slice(6).trim() || null;
        continue;
      }

      if (line.startsWith('data:')) {
        dataBuffer.push(line.slice(5).trim());
        continue;
      }

      // 기타 라인은 스트림 파싱을 방해하지 않도록 무시
    }
  }
}

/**
 * Check if backend is available
 */
export async function isBackendAvailable(): Promise<boolean> {
  return apiClient.healthCheck()
}
