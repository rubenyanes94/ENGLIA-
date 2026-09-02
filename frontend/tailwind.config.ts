import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        // Inter primero (cargada en index.html); -apple-system/San
        // Francisco como fallback nativo en macOS/iOS antes de caer al
        // stack genérico — así en un Mac/iPhone real se ve SF Pro de
        // verdad, y en cualquier otro sitio, Inter (visualmente casi
        // idéntica, con el mismo espíritu geométrico y limpio).
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
} satisfies Config
