import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { API_BASE_URL } from './src/components/Constants';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/load_city': API_BASE_URL,
      '/optimize': API_BASE_URL,
      '/results': API_BASE_URL,
      '/reverse-geocode': API_BASE_URL,
      '/select_best_solution_by_weight': API_BASE_URL,
    },
  },
})
