// Axios 인스턴스 + 인터셉터 설정

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import {
  getAccessToken,
  getRefreshToken,
  getTokenType,
  setTokens,
  clearTokens,
  isTokenExpired,
  isTokenExpiringSoon,
} from './authUtils';

// API 베이스 URL (백엔드 환경 변수와 통일)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Axios 인스턴스 생성
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 90000, // 90초 (LLM 응답 시간 고려)
});

// 토큰 갱신 중인지 추적
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

// 토큰 갱신 완료 시 대기 중인 요청들에 새 토큰 전달
const onTokenRefreshed = (newToken: string) => {
  refreshSubscribers.forEach((callback) => callback(newToken));
  refreshSubscribers = [];
};

// 토큰 갱신 대기 큐에 추가
const addRefreshSubscriber = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};

// 토큰 갱신 함수
const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
      refresh_token: refreshToken,
    });

    if (response.data.access_token) {
      // 새 액세스 토큰만 업데이트
      localStorage.setItem('access_token', response.data.access_token);
      return response.data.access_token;
    }

    return null;
  } catch (error) {
    console.error('토큰 갱신 실패:', error);
    clearTokens();
    window.location.href = '/'; // 로그인 페이지로 리다이렉트
    return null;
  }
};

// 요청 인터셉터: 모든 요청에 액세스 토큰 자동 추가
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const accessToken = getAccessToken();

    if (accessToken) {
      // 토큰이 곧 만료되는지 확인
      if (isTokenExpiringSoon(accessToken) && !isRefreshing) {
        isRefreshing = true;
        try {
          const newToken = await refreshAccessToken();
          if (newToken) {
            config.headers.Authorization = `${getTokenType()} ${newToken}`;
            onTokenRefreshed(newToken);
          }
        } catch (error) {
          console.error('토큰 갱신 실패:', error);
        } finally {
          isRefreshing = false;
        }
      } else if (!isTokenExpired(accessToken)) {
        // 만료되지 않은 토큰 사용
        config.headers.Authorization = `${getTokenType()} ${accessToken}`;
      } else if (isRefreshing) {
        // 토큰 갱신 중이면 대기
        return new Promise((resolve) => {
          addRefreshSubscriber((newToken: string) => {
            config.headers.Authorization = `${getTokenType()} ${newToken}`;
            resolve(config);
          });
        });
      }
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터: 401 에러 시 토큰 갱신 시도
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 401 에러이고 재시도하지 않은 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (!isRefreshing) {
        isRefreshing = true;

        try {
          const newToken = await refreshAccessToken();

          if (newToken) {
            // 원래 요청에 새 토큰 적용
            originalRequest.headers.Authorization = `${getTokenType()} ${newToken}`;
            onTokenRefreshed(newToken);

            // 원래 요청 재시도
            return apiClient(originalRequest);
          }
        } catch (refreshError) {
          console.error('토큰 갱신 실패:', refreshError);
          clearTokens();
          window.location.href = '/';
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        // 이미 토큰 갱신 중이면 대기
        return new Promise((resolve) => {
          addRefreshSubscriber((newToken: string) => {
            originalRequest.headers.Authorization = `${getTokenType()} ${newToken}`;
            resolve(apiClient(originalRequest));
          });
        });
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
