import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/shared/ui';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught render-level error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/dashboard';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#1E2A38] text-[#FFFFFF] flex flex-col items-center justify-center p-6 text-center">
          <div className="border border-[#FF9B9B]/30 bg-[#FF9B9B]/5 rounded-2xl max-w-md p-8 flex flex-col items-center gap-4 shadow-[0_0_24px_rgba(255,82,82,0.1)]">
            <div className="h-16 w-16 rounded-full bg-[#34495E] border-2 border-black flex items-center justify-center text-[#FF9B9B]">
              <AlertTriangle className="h-8 w-8" />
            </div>
            <h1 className="text-xl font-bold text-[#FFFFFF]">Tizim Xatosi</h1>
            <p className="text-sm text-[#B0BEC5]">
              Kutilmagan texnik nosozlik yuz berdi. Iltimos, sahifani yangilang yoki tizimga qayta kiring.
            </p>
            {this.state.error && import.meta.env.DEV && (
              <pre className="text-left w-full overflow-x-auto text-xs text-[#B0BEC5] bg-[#1E2A38] p-3 rounded border-2 border-black font-mono max-h-32">
                {this.state.error.message}
              </pre>
            )}
            <div className="flex gap-3 w-full">
              <Button
                variant="primary"
                onClick={() => window.location.reload()}
                className="flex-1"
              >
                <RefreshCw className="h-4 w-4" /> Sahifani yangilash
              </Button>
              <Button
                variant="secondary"
                onClick={this.handleReset}
                className="flex-1"
              >
                Asosiyga qaytish
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
export default ErrorBoundary;
