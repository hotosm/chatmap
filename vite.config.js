import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/chatmap/',
  plugins: [react()],
  build: {
    outDir: 'build',
    sourcemap: true,
  },
  server: {
    open: true,
    fs: {
        strict: false,
    },
    historyApiFallback: true,
  },
});



