import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // necesario para que sea accesible fuera del contenedor
    port: 5173,
    // Desde Vite 5.4, por seguridad (protección contra DNS rebinding) Vite
    // rechaza con 403 cualquier request cuyo header Host no esté en una
    // lista blanca. El navegador, al entrar por la URL pública de reenvío
    // de puertos de Codespaces (https://<nombre>-5173.app.github.dev),
    // manda justo ese Host — así que sin esto el frontend nunca cargaría
    // dentro de Codespaces, solo con "localhost" directo en el propio host.
    allowedHosts: ['.app.github.dev'],
  },
})
