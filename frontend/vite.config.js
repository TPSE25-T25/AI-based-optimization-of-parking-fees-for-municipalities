import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  // 1. Prefer value from .env file
  // 2. Fall back to Docker build-arg (process.env set via ENV in Dockerfile)
  // 3. Default to local backend for `npm start` with no .env file
  const API_TARGET = env.VITE_API_BASE_URL
    || process.env.VITE_API_BASE_URL
    || 'http://localhost:6173';

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/load_city': API_TARGET,
        '/optimize': API_TARGET,
        '/results': API_TARGET,
        '/reverse-geocode': API_TARGET,
        '/select_best_solution_by_weight': API_TARGET,
        '/optimization-settings': API_TARGET,
        '/health': API_TARGET,
      },
    },
  };
})
