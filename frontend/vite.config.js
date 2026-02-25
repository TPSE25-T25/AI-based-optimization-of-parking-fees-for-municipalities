import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/load_city': 'http://localhost:8000',
      '/optimize': 'http://localhost:8000',
      '/results': 'http://localhost:8000',
      '/reverse-geocode': 'http://localhost:8000',
      '/select_best_solution_by_weight': 'http://localhost:8000',
    },
  },
})
