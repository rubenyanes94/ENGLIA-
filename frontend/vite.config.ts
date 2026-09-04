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

    // El frontend habla con el backend por /api en su MISMO origen, y es
    // este proxy (server-side, dentro del contenedor del frontend) quien
    // reenvía a la red interna de Docker.
    //
    // Por qué, y no una llamada directa a https://<codespace>-8000.app.github.dev:
    // en Codespaces los puertos reenviados nacen PRIVADOS, así que una
    // petición del navegador al puerto 8000 desde el origen del 5173 no
    // llega a FastAPI — GitHub la intercepta con un 302 a su pantalla de
    // login (pf-signin), que como es lógico no trae cabeceras CORS, y el
    // navegador lo reporta como "blocked by CORS policy" despistando por
    // completo sobre la causa real. Con el proxy no hay petición
    // cross-origin en absoluto: el puerto 8000 puede seguir privado.
    //
    // `backend` es el nombre del servicio en docker-compose.yml (los
    // contenedores se resuelven por nombre entre ellos), no "localhost":
    // localhost aquí dentro sería el propio contenedor del frontend.
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
