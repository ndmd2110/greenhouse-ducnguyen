import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Bind-mounted folders on Windows/macOS don't emit file events into the container.
    watch: { usePolling: process.env.CHOKIDAR_USEPOLLING === 'true' },
  },
})