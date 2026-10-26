/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import axios from 'axios';
import { router } from './router';
import ErrorBoundary from './ErrorBoundary';
import { ToastContainer } from '@/shared/ui';

// Create a client for React Query operations with optimized default stale times
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (axios.isAxiosError(error) && error.response?.status) {
          if ([400, 401, 403, 404, 422].includes(error.response.status)) return false;
        }
        return failureCount < 2;
      },
      staleTime: 1000 * 30, // 30 seconds
    },
  },
});

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastContainer />
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
