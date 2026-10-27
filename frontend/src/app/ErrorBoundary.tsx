import { Component, ErrorInfo, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/shared/ui';
import i18n from '@/shared/lib/i18n';

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
            <h1 className="text-xl font-bold text-[#FFFFFF]">{i18n.t('common.systemError')}</h1>
            <p className="text-sm text-[#B0BEC5]">
              {i18n.t('common.systemErrorDesc')}
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
                <RefreshCw className="h-4 w-4" /> {i18n.t('common.refreshPage')}
              </Button>
              <Button
                variant="secondary"
                onClick={this.handleReset}
                className="flex-1"
              >
                {i18n.t('common.backToHome')}
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function RootRouteError() {
  const { t } = useTranslation();
  const handleReload = () => window.location.reload();
  const handleHome = () => { window.location.href = '/dashboard'; };

  return (
    <div className="min-h-screen bg-[#1E2A38] text-white flex flex-col items-center justify-center p-6 text-center select-none font-sans">
      <div className="border-2 border-black bg-[#2A3442] rounded-3xl max-w-md w-full p-8 flex flex-col items-center gap-5 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
        <div className="h-16 w-16 rounded-2xl bg-[#34495E] border-2 border-black flex items-center justify-center text-[#FF9B9B] shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
          <AlertTriangle className="h-8 w-8" />
        </div>
        <div className="space-y-1">
          <h1 className="text-xl font-black font-montserrat uppercase tracking-tight text-white">
            {t('common.systemError')}
          </h1>
          <p className="text-xs text-[#B0BEC5] leading-relaxed">
            {t('common.systemErrorDesc')}
          </p>
        </div>
        <div className="flex gap-3 w-full pt-2">
          <Button variant="primary" onClick={handleReload} className="flex-1 justify-center gap-2">
            <RefreshCw className="h-4 w-4" /> {t('common.refreshPage')}
          </Button>
          <Button variant="secondary" onClick={handleHome} className="flex-1 justify-center">
            {t('common.backToHome')}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ErrorBoundary;

