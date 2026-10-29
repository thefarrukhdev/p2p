import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@/shared/lib/i18n';
import { initFrontendTelemetry } from '@/shared/lib/telemetry';
import App from './app/App';
import './index.css';

initFrontendTelemetry();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
