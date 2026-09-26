import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import 'maplibre-gl/dist/maplibre-gl.css';
import './index.css';
import App from './App';
import { EvidenceProvider } from '@/components/evidence';
import { GhostCursorProvider } from '@/components/GhostCursor';

if (import.meta.env.VITE_FIXTURES === '1') (await import('./dev/mockApi')).installMockApi();

const qc = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, staleTime: 30_000, retry: 1 } } });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <EvidenceProvider>
          <GhostCursorProvider>
            <App />
          </GhostCursorProvider>
        </EvidenceProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
