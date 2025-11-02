/**
 * API Service Layer
 * Handles all backend communication for KIME Chat
 */

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
