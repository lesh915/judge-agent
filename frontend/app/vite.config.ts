import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 29173,
    strictPort: true,
    host: '0.0.0.0',
  },
});
