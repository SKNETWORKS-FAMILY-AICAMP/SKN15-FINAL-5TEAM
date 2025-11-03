import React, { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console (or error reporting service)
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null
    });
    // Reload the page to reset the app state
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
            {/* Error Icon */}
            <div className="text-6xl mb-6">⚠️</div>

            {/* Error Title */}
            <h2 className="text-2xl font-bold text-gray-800 mb-3">
              문제가 발생했습니다
            </h2>

            {/* Error Message */}
            <p className="text-gray-600 mb-6">
              예상치 못한 오류가 발생했습니다.<br />
              페이지를 새로고침하면 문제가 해결될 수 있습니다.
            </p>

            {/* Error Details (development only) */}
            {import.meta.env.DEV && this.state.error && (
              <div className="bg-red-50 rounded-lg p-4 mb-6 text-left">
                <p className="text-xs font-mono text-red-800 break-all">
                  {this.state.error.toString()}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-3">
              <button
                onClick={this.handleReset}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 transition-all shadow-lg hover:shadow-xl"
              >
                홈으로 돌아가기
              </button>

              <button
                onClick={() => window.location.reload()}
                className="w-full px-6 py-3 bg-white text-gray-700 border border-gray-300 rounded-xl font-semibold hover:bg-gray-50 transition-all"
              >
                페이지 새로고침
              </button>
            </div>

            {/* Help Text */}
            <p className="text-xs text-gray-500 mt-6">
              문제가 계속되면 브라우저 캐시를 삭제하거나<br />
              나중에 다시 시도해주세요.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
