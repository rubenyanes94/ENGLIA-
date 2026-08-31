import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // necesario para que sea accesible fuera del contenedor
    port: 5173,
  },
})
