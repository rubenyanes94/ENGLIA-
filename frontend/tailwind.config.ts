import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      // Paleta de la marca, sacada del logotipo de Espikin.
      //
      // `brand` es el violeta del logo: el 600 es el tono vivo de la
      // burbuja (#6A2BE0 en el manual) y se usa como color principal; los
      // claros (200-300) son la lavanda del degradado del wordmark.
      //
      // `ink` es el azul marino casi negro del fondo del logo. Sustituye
      // al slate-900 genérico en las superficies oscuras (cabeceras,
      // reproductor, botones oscuros): con slate, el oscuro de la app era
      // gris azulado y no casaba con el violeta.
      //
      // Contraste comprobado: blanco sobre brand-600 y brand-600 sobre
      // blanco superan 4.5:1 (AA para texto normal).
      colors: {
        brand: {
          50: '#F5F2FF',
          100: '#EDE7FF',
          200: '#DCD1FF',
          300: '#C2B0FF',
          400: '#A184FB',
          500: '#8559F4',
          600: '#6D3BE6',
          700: '#5B2CCB',
          800: '#4B25A5',
          900: '#3D2184',
          950: '#241254',
        },
        ink: {
          700: '#2B2270',
          800: '#1D1754',
          900: '#120E3A',
          950: '#0A0824',
        },
      },
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
