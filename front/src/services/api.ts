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

export interface MemoryEvent {
  event_type: 'saved' | 'recalled'
  character_name: string
  memory_type: string
  memory_content: string
  importance: number
  count?: number
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
  memory_events?: MemoryEvent[]
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

export interface RecentSession {
  session_id: string
  scenario_id: string
  scenario_title?: string
  scenario_thumbnail?: string
  current_stage?: string
  turn_count: number
  created_at?: string
  updated_at?: string
  conversation_summary?: string
  last_message_speaker?: string
  last_message_content?: string
}

export interface UserInfo {
  user_id: string
  username: string
  display_name: string | null
}

export interface UserCredits {
  bubble_count: number
  total_purchased: number
  total_consumed: number
  last_updated?: string
}

export interface ConsumeCreditsResult {
  success?: boolean  // Optional for backward compatibility
  message?: string
  remaining_credits?: number
  // Backend returns CreditTransactionResponse
  transaction_id?: string
  user_id?: string
  amount?: number
  transaction_type?: string
  balance_after?: number
  description?: string
  created_at?: string
}

export interface CreditTransaction {
  transaction_id: string
  user_id: string
  amount: number
  transaction_type: 'purchase' | 'consume' | 'refund' | 'bonus' | 'initial'
  balance_after: number
  description?: string
  created_at: string
}

export interface CreditStats {
  total_transactions: number
  by_type: {
    [key: string]: {
      count: number
      total_amount: number
    }
  }
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

export interface LongTermMemory {
  memory_id: number
  memory_key: string
  memory_value: string
  memory_type: string
  importance: number | null
  access_count: number
  last_accessed_at: string | null
  created_at: string | null
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

export interface UserSettings {
  sound_enabled: boolean
  bgm_volume: number
  sfx_volume: number
  auto_save: boolean
  language: string
  font_size: 'small' | 'medium' | 'large'
  animation_speed: 'slow' | 'normal' | 'fast'
  created_at?: string
  updated_at?: string
}

export type UserSettingsUpdate = Partial<Omit<UserSettings, 'created_at' | 'updated_at'>>

// Comment interfaces
export interface Comment {
  id: number
  comment_id: string  // Alias for id (backward compatibility)
  scenario_id: string
  user_id: string
  username: string
  display_name: string
  content: string
  parent_comment_id: number | null
  like_count: number
  reply_count: number
  is_liked: boolean
  is_owner: boolean
  is_edited: boolean
  created_at: string
  updated_at: string
}

export interface CommentCreate {
  content: string
  parent_comment_id?: number | null
}

export interface CommentUpdate {
  content: string
}

export interface CommentListResponse {
  items: Comment[]
  next_cursor: string | null
  total_count: number
}

// Alias for backward compatibility
export type ScenarioComment = Comment

// Live Stats interface
export interface LiveStats {
  total_likes: number
  total_comments: number
  total_chats: number
  avg_affinity_score: number
  last_updated?: string
}

export interface UserStatistics {
  total_play_time_minutes: number
  total_sessions: number
  total_messages: number
  rank: {
    rank_code: string
    rank_name_ko: string
    rank_icon: string
    level: number
    experience_points: number
    next_rank_xp: number | null
  }
  scenario_progress: {
    completed_count: number
    total_count: number
    total_completions: number
  }
  top_affinity_characters: Array<{
    character_name: string
    affinity_score: number  // 글로벌 친밀도 (0~1000)
    affinity_level: number  // 친밀도 레벨 (1~10)
    total_interactions: number  // 총 상호작용 횟수
  }>
  frequent_scenarios: Array<{
    scenario_id: string
    title: string
    play_count: number
    total_messages: number
  }>
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
   * Send chat message and get response with streaming (SSE)
   * Requires authentication (JWT token)
   */
  async sendMessage(
    request: ChatRequest,
    onDialogue?: (dialogue: ChatMessage, index: number) => void
  ): Promise<ChatResponse> {
    return new Promise((resolve, reject) => {
      try {
        // Get access token (required for authentication)
        let accessToken = localStorage.getItem('access_token')
        if (!accessToken) {
          reject(new Error('Authentication required. Please log in.'))
          return
        }

        // Check if token is expired
        try {
          const payload = JSON.parse(atob(accessToken.split('.')[1]))
          const expirationTime = payload.exp * 1000 // Convert to milliseconds
          const currentTime = Date.now()

          if (currentTime >= expirationTime) {
            console.warn('Access token expired, user needs to re-login')
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
            reject(new Error('Session expired. Please log in again.'))
            return
          }
        } catch (tokenError) {
          console.error('Failed to decode token:', tokenError)
          reject(new Error('Invalid token. Please log in again.'))
          return
        }

        // Prepare request body
        const requestBody = JSON.stringify(request)

        // EventSource doesn't support POST with body,
        // so we use fetch with streaming
        const url = `${this.baseUrl}/api/chat`

        fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
          },
          body: requestBody,
        })
          .then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`)
            }

            const reader = response.body?.getReader()
            if (!reader) {
              throw new Error('No response body')
            }

            const decoder = new TextDecoder()
            let buffer = ''

            // Response accumulator
            let metadata: any = null
            const dialogues: ChatMessage[] = []

            const readStream = () => {
              reader.read().then(({ done, value }) => {
                if (done) {
                  // Stream ended, resolve with final response
                  if (metadata) {
                    resolve({
                      session_id: metadata.session_id,
                      turn_count: metadata.turn_count,
                      dialogues: dialogues,
                      current_stage: metadata.current_stage,
                      affinity_scores: metadata.affinity_scores || {},
                      is_ended: metadata.is_ended || false,
                      has_more: metadata.has_more || false,
                      current_image: metadata.current_image,
                      output: metadata.output || {},
                      memory_events: metadata.memory_events || [],
                    })
                  } else {
                    reject(new Error('No metadata received'))
                  }
                  return
                }

                // Decode chunk
                buffer += decoder.decode(value, { stream: true })

                // Process complete SSE messages
                const lines = buffer.split('\n\n')
                buffer = lines.pop() || '' // Keep incomplete message in buffer

                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.substring(6)
                    try {
                      const parsed = JSON.parse(data)

                      if (parsed.type === 'metadata') {
                        metadata = parsed
                      } else if (parsed.type === 'dialogue') {
                        const dialogue = parsed.dialogue
                        dialogues.push(dialogue)
                        // Call callback for real-time UI update
                        if (onDialogue) {
                          onDialogue(dialogue, parsed.index)
                        }
                      } else if (parsed.type === 'done') {
                        // Stream complete - update metadata with final state including affinity scores
                        metadata = {
                          ...metadata,
                          turn_count: parsed.turn_count,
                          current_stage: parsed.current_stage,
                          affinity_scores: parsed.affinity_scores || {},
                          is_ended: parsed.is_ended || false,
                          output: parsed.output || {},
                          memory_events: parsed.memory_events || [],
                        }
                      } else if (parsed.type === 'error') {
                        reject(new Error(parsed.message))
                        return
                      }
                    } catch (parseError) {
                      console.error('Error parsing SSE data:', parseError, data)
                    }
                  }
                }

                // Continue reading
                readStream()
              }).catch((err) => {
                reject(err)
              })
            }

            // Start reading stream
            readStream()
          })
          .catch((error) => {
            console.error('Error sending message:', error)
            reject(error)
          })
      } catch (error) {
        console.error('Error in sendMessage:', error)
        reject(error)
      }
    })
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
   * Finalize session: Extract remaining memories and deactivate session
   * Should be called when user finishes a scenario or leaves the chat
   */
  async finalizeSession(sessionId: string): Promise<{
    success: boolean
    memories_created: number
    message: string
  }> {
    try {
      const response = await authenticatedApiClient.post(`/api/chat/${sessionId}/finalize`)
      console.log(`Session finalized: ${sessionId}, memories created: ${response.data.memories_created}`)
      return response.data
    } catch (error) {
      console.error('Error finalizing session:', error)
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
      const response = await authenticatedApiClient.get('/api/sessions/last', { params })

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
   * Get user's sessions (with JWT authentication)
   * Can filter by scenario_id
   */
  async getUserSessions(scenarioId?: string, limit: number = 20, offset: number = 0): Promise<RecentSession[]> {
    try {
      const params: any = { limit, offset }
      if (scenarioId) {
        params.scenario_id = scenarioId
      }
      const response = await authenticatedApiClient.get('/api/sessions', {
        params
      })
      return response.data.sessions || []
    } catch (error) {
      console.error('Error getting user sessions:', error)
      return []
    }
  }

  /**
   * Get user's recent sessions (with JWT authentication)
   */
  async getRecentSessions(limit: number = 4): Promise<RecentSession[]> {
    try {
      const response = await authenticatedApiClient.get('/api/sessions/recent', {
        params: { limit }
      })
      return response.data
    } catch (error) {
      console.error('Error getting recent sessions:', error)
      return []
    }
  }

  /**
   * Get session dialogue history (with JWT authentication)
   */
  async getSessionDialogues(sessionId: string, limit: number = 100): Promise<ChatMessage[]> {
    try {
      const response = await authenticatedApiClient.get(`/api/sessions/${sessionId}/dialogues`, {
        params: { limit }
      })
      return response.data.dialogues.map((d: any) => ({
        speaker: d.speaker,
        text: d.content,
        emotion: d.emotion,
        emotion_intensity: d.emotion_intensity,
        timestamp: d.created_at
      }))
    } catch (error) {
      console.error('Error getting session dialogues:', error)
      return []
    }
  }

  /**
   * Get current user information (with JWT authentication)
   */
  async getCurrentUser(): Promise<UserInfo> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me')
      return response.data
    } catch (error) {
      console.error('Error getting current user:', error)
      throw error
    }
  }

  /**
   * Update current user profile (display name/email)
   */
  async updateUserProfile(profile: { display_name?: string | null; email?: string | null }): Promise<UserInfo> {
    try {
      const response = await authenticatedApiClient.put('/api/users/me', profile)
      return response.data
    } catch (error: any) {
      console.error('Error updating user profile:', error)
      throw new Error(error.response?.data?.detail || '프로필 업데이트에 실패했습니다.')
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
   * Change password for logged-in user (requires authentication)
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await authenticatedApiClient.post('/api/auth/password-change', {
        current_password: currentPassword,
        new_password: newPassword
      })
      return response.data
    } catch (error: any) {
      console.error('Error changing password:', error)
      throw new Error(error.response?.data?.detail || '비밀번호 변경에 실패했습니다.')
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
  async consumeCredits(amount: number, description: string): Promise<ConsumeCreditsResult> {
    try {
      const params = new URLSearchParams()
      params.append('amount', amount.toString())
      if (description) {
        params.append('description', description)
      }

      const response = await authenticatedApiClient.post(`/api/users/me/credits/consume?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error consuming credits:', error)
      throw error
    }
  }

  /**
   * Purchase credits
   */
  async purchaseCredits(amount: number, description?: string): Promise<CreditTransaction> {
    try {
      const params = new URLSearchParams()
      params.append('amount', amount.toString())
      if (description) {
        params.append('description', description)
      }
      const response = await authenticatedApiClient.post(`/api/users/me/credits/purchase?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error purchasing credits:', error)
      throw error
    }
  }

  /**
   * Get credit transactions
   */
  async getCreditTransactions(transactionType?: string, limit: number = 20): Promise<CreditTransaction[]> {
    try {
      const params: any = { limit }
      if (transactionType) {
        params.transaction_type = transactionType
      }
      const response = await authenticatedApiClient.get('/api/users/me/credits/transactions', { params })
      return response.data
    } catch (error) {
      console.error('Error getting credit transactions:', error)
      throw error
    }
  }

  /**
   * Get credit transaction statistics
   */
  async getCreditStats(): Promise<CreditStats> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/credits/stats')
      return response.data
    } catch (error) {
      console.error('Error getting credit stats:', error)
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
   * Get user long-term memories
   */
  async getUserLongTermMemories(memoryType?: string, limit: number = 50): Promise<LongTermMemory[]> {
    try {
      const params = new URLSearchParams()
      if (memoryType) {
        params.append('memory_type', memoryType)
      }
      params.append('limit', limit.toString())

      const response = await authenticatedApiClient.get(`/api/users/me/long-term-memories?${params}`)
      return response.data
    } catch (error) {
      console.error('Error getting long-term memories:', error)
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
   * Get all scenarios (public API, no JWT required)
   */
  async getScenarios(): Promise<ScenarioCard[]> {
    try {
      const response = await axios.get(`${this.baseUrl}/api/scenarios`)
      return response.data.scenarios || []
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
  async toggleScenarioLike(scenarioId: string): Promise<{ liked: boolean; like_count: number }> {
    try {
      const response = await authenticatedApiClient.post(`/api/scenarios/${scenarioId}/like`)
      return response.data
    } catch (error) {
      console.error(`Error toggling like for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Check if user has liked a scenario (requires JWT)
   */
  async checkScenarioLike(scenarioId: string): Promise<{ liked: boolean }> {
    try {
      const response = await authenticatedApiClient.get(`/api/scenarios/${scenarioId}/like`)
      return response.data
    } catch (error) {
      console.error(`Error checking like for scenario ${scenarioId}:`, error)
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

  // ============================================================
  // User Settings Methods
  // ============================================================

  /**
   * Get user settings (requires JWT)
   */
  async getUserSettings(): Promise<UserSettings> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/settings')
      return response.data
    } catch (error) {
      console.error('Error getting user settings:', error)
      throw error
    }
  }

  /**
   * Update user settings (requires JWT)
   */
  async updateUserSettings(settings: UserSettingsUpdate): Promise<{ success: boolean; message: string }> {
    try {
      const response = await authenticatedApiClient.put('/api/users/me/settings', settings)
      return response.data
    } catch (error) {
      console.error('Error updating user settings:', error)
      throw error
    }
  }

  /**
   * Get user statistics (requires JWT)
   */
  async getUserStatistics(): Promise<UserStatistics> {
    try {
      const response = await authenticatedApiClient.get('/api/users/me/statistics')
      return response.data
    } catch (error) {
      console.error('Error getting user statistics:', error)
      throw error
    }
  }

  // ============================================================
  // Gallery API Methods
  // ============================================================

  /**
   * Get unlocked images for the current user
   */
  async getUnlockedImages(scenario_id?: string): Promise<any> {
    try {
      const params = scenario_id ? { scenario_id } : {}
      const response = await authenticatedApiClient.get('/api/gallery/my-images', { params })
      return response.data
    } catch (error) {
      console.error('Error getting unlocked images:', error)
      throw error
    }
  }

  /**
   * Get all images with unlock status
   */
  async getAllImagesWithStatus(scenario_id?: string): Promise<any> {
    try {
      const params = scenario_id ? { scenario_id } : {}
      const response = await authenticatedApiClient.get('/api/gallery/all-images', { params })
      return response.data
    } catch (error) {
      console.error('Error getting all images:', error)
      throw error
    }
  }

  /**
   * Get gallery statistics
   */
  async getGalleryStats(scenario_id?: string): Promise<any> {
    try {
      const params = scenario_id ? { scenario_id } : {}
      const response = await authenticatedApiClient.get('/api/gallery/stats', { params })
      return response.data
    } catch (error) {
      console.error('Error getting gallery stats:', error)
      throw error
    }
  }

  /**
   * Get live statistics for scenarios
   */
  async getLiveStats(): Promise<LiveStats> {
    try {
      const response = await authenticatedApiClient.get('/api/scenarios/live-stats')
      return response.data
    } catch (error) {
      console.error('Error getting live stats:', error)
      throw error
    }
  }

  /**
   * Manually unlock an image (admin/testing)
   */
  async unlockImage(image_id: string): Promise<any> {
    try {
      const response = await authenticatedApiClient.post(`/api/gallery/unlock/${image_id}`)
      return response.data
    } catch (error) {
      console.error('Error unlocking image:', error)
      throw error
    }
  }

  // ============================================================
  // Comment API Methods
  // ============================================================

  /**
   * Get comments for a scenario (public API, auth optional)
   */
  async getScenarioComments(
    scenarioId: string,
    params?: { limit?: number; cursor?: string; sortBy?: 'recent' | 'popular' }
  ): Promise<CommentListResponse> {
    try {
      const sortParam =
        params?.sortBy === 'recent'
          ? 'created_at'
          : params?.sortBy === 'popular'
            ? 'like_count'
            : 'like_count'

      const queryParams: any = {
        limit: params?.limit || 50,
        sort_by: sortParam,
        offset: params?.cursor ? Number(params.cursor) || 0 : 0
      }

      const normalizeResponse = (data: any): CommentListResponse => {
        if (data?.items && typeof data?.total_count === 'number') {
          return data
        }

        return {
          items: data?.comments || [],
          total_count:
            typeof data?.total === 'number'
              ? data.total
              : Array.isArray(data?.comments)
                ? data.comments.length
                : 0,
          next_cursor: data?.next_cursor || null
        }
      }

      // Try with auth first if user is logged in
      try {
        const response = await authenticatedApiClient.get(`/api/scenarios/${scenarioId}/comments`, {
          params: queryParams
        })
        return normalizeResponse(response.data)
      } catch (authError) {
        // Fallback to public API if not authenticated
        const response = await axios.get(`${this.baseUrl}/api/scenarios/${scenarioId}/comments`, {
          params: queryParams
        })
        return normalizeResponse(response.data)
      }
    } catch (error) {
      console.error(`Error getting comments for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Get replies for a comment (public API, auth optional)
   */
  async getCommentReplies(scenarioId: string, commentId: number): Promise<Comment[]> {
    try {
      // Try with auth first if user is logged in
      try {
        const response = await authenticatedApiClient.get(
          `/api/scenarios/${scenarioId}/comments/${commentId}/replies`
        )
        return response.data
      } catch (authError) {
        // Fallback to public API if not authenticated
        const response = await axios.get(
          `${this.baseUrl}/api/scenarios/${scenarioId}/comments/${commentId}/replies`
        )
        return response.data
      }
    } catch (error) {
      console.error(`Error getting replies for comment ${commentId}:`, error)
      throw error
    }
  }

  /**
   * Create a comment (requires JWT)
   */
  async createComment(scenarioId: string, commentData: CommentCreate): Promise<Comment> {
    try {
      const response = await authenticatedApiClient.post(
        `/api/scenarios/${scenarioId}/comments`,
        commentData
      )
      return response.data
    } catch (error) {
      console.error(`Error creating comment for scenario ${scenarioId}:`, error)
      throw error
    }
  }

  /**
   * Update a comment (requires JWT, owner only)
   */
  async updateComment(
    scenarioId: string,
    commentId: number,
    commentData: CommentUpdate
  ): Promise<{ success: boolean }> {
    try {
      const response = await authenticatedApiClient.put(
        `/api/scenarios/${scenarioId}/comments/${commentId}`,
        commentData
      )
      return response.data
    } catch (error) {
      console.error(`Error updating comment ${commentId}:`, error)
      throw error
    }
  }

  /**
   * Delete a comment (requires JWT, owner only)
   */
  async deleteComment(scenarioId: string, commentId: number | string): Promise<{ success: boolean }> {
    try {
      const response = await authenticatedApiClient.delete(
        `/api/scenarios/${scenarioId}/comments/${commentId}`
      )
      return response.data
    } catch (error) {
      console.error(`Error deleting comment ${commentId}:`, error)
      throw error
    }
  }

  /**
   * Alias for createComment (backward compatibility)
   */
  async createScenarioComment(scenarioId: string, commentData: CommentCreate): Promise<Comment> {
    return this.createComment(scenarioId, commentData)
  }

  /**
   * Alias for deleteComment (backward compatibility)
   */
  async deleteScenarioComment(scenarioId: string, commentId: number | string): Promise<{ success: boolean }> {
    return this.deleteComment(scenarioId, commentId)
  }

  /**
   * Toggle like on a comment (requires JWT)
   */
  async toggleCommentLike(
    scenarioId: string,
    commentId: number
  ): Promise<{ liked: boolean; like_count: number }> {
    try {
      const response = await authenticatedApiClient.post(
        `/api/scenarios/${scenarioId}/comments/${commentId}/like`
      )
      return response.data
    } catch (error) {
      console.error(`Error toggling like for comment ${commentId}:`, error)
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
export async function sendChatMessage(
  scenarioId: string,
  userInput: string,
  sessionId?: string,
  userName?: string
): Promise<ChatResponse> {
  return apiClient.sendMessage({
    session_id: sessionId,
    scenario_id: scenarioId,
    user_input: userInput,
    user_name: userName,
  })
}

/**
 * Check if backend is available
 */
export async function isBackendAvailable(): Promise<boolean> {
  return apiClient.healthCheck()
}
