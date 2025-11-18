import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    strictPort: true,
    hmr: {
      clientPort: 80,
    },
    watch: {
      usePolling: true,
    },
    proxy: {},
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
