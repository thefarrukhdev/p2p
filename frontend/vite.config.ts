import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  const devTarget = process.env.VITE_BACKEND_TARGET || 'http://localhost:8000';
  const wsTarget = devTarget.replace(/^http/, 'ws');
  const vercelEnv = process.env.VITE_VERCEL_ENV || process.env.VERCEL_ENV || '';

  return {
    define: {
      'import.meta.env.VITE_VERCEL_ENV': JSON.stringify(vercelEnv),
    },
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: '0.0.0.0',
      proxy: {
        '/api': { target: devTarget, changeOrigin: true },
        '/ws': { target: wsTarget, ws: true, changeOrigin: true },
      },
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
    build: {
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            'vendor-query': ['@tanstack/react-query', 'axios'],
            'vendor-form': ['react-hook-form', '@hookform/resolvers', 'zod'],
            'vendor-i18n': ['i18next', 'react-i18next', 'i18next-browser-languagedetector'],
            'vendor-icons': ['lucide-react'],
          },
        },
      },
    },
  };
});
