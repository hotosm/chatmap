import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'build',
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    minify: 'terser'
  },
  server: {
    open: true,
    fs: {
        strict: false,
    },
    historyApiFallback: true,
  },
});



