import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        // Main API endpoints
        '/api': {
          target: 'http://127.0.0.1:5001',
          changeOrigin: true,
        },
        // Auth API (not page routes)
        '/auth/api': {
          target: 'http://127.0.0.1:5001',
          changeOrigin: true,
        },
        // Wealth API endpoints only (not /wealth page route)
        '/wealth/api': {
          target: 'http://127.0.0.1:5001',
          changeOrigin: true,
        },
        // Reports API endpoints only
        '/reports/api': {
          target: 'http://127.0.0.1:5001',
          changeOrigin: true,
        },
        '/reports/simulation/api': {
          target: 'http://127.0.0.1:5001',
          changeOrigin: true,
        },
        // Logic Studio API endpoints only
        '/logic-studio/api': {
          target: 'http://127.0.0.1:5001',
          changeOrigin: true,
        },
      },
    },
    plugins: [react()],
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      }
    }
  };
});
