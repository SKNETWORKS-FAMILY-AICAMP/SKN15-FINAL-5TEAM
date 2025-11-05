// JWT 토큰 관리 유틸리티

export interface TokenData {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserData {
  user_id: string;
  username: string;
  display_name: string;
  email?: string;
}

// 토큰을 localStorage에 저장
export const setTokens = (tokens: TokenData): void => {
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  localStorage.setItem('token_type', tokens.token_type);
};

// 액세스 토큰 가져오기
export const getAccessToken = (): string | null => {
  return localStorage.getItem('access_token');
};

// 리프레시 토큰 가져오기
export const getRefreshToken = (): string | null => {
  return localStorage.getItem('refresh_token');
};

// 토큰 타입 가져오기
export const getTokenType = (): string => {
  return localStorage.getItem('token_type') || 'bearer';
};

// 모든 토큰 삭제 (로그아웃)
export const clearTokens = (): void => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('token_type');
  localStorage.removeItem('user_data');
};

// 사용자 데이터 저장
export const setUserData = (userData: UserData): void => {
  localStorage.setItem('user_data', JSON.stringify(userData));
};

// 사용자 데이터 가져오기
export const getUserData = (): UserData | null => {
  const data = localStorage.getItem('user_data');
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
};

// 로그인 상태 확인
export const isAuthenticated = (): boolean => {
  const accessToken = getAccessToken();
  return !!accessToken;
};

// JWT 토큰 디코딩 (payload만)
export const decodeToken = (token: string): any => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
};

// 토큰 만료 여부 확인
export const isTokenExpired = (token: string): boolean => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;

  const currentTime = Math.floor(Date.now() / 1000);
  return decoded.exp < currentTime;
};

// 액세스 토큰이 곧 만료되는지 확인 (5분 이내)
export const isTokenExpiringSoon = (token: string): boolean => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;

  const currentTime = Math.floor(Date.now() / 1000);
  const fiveMinutes = 5 * 60;
  return decoded.exp - currentTime < fiveMinutes;
};
