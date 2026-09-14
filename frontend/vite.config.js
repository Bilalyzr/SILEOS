import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { offlinePlugin } from './vite-plugin-offline.js'
import { versionPlugin } from './vite-plugin-version.js'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // loadEnv reads .env.local / .env.development etc. so the proxy target
  // can be overridden from a file (process.env alone doesn't see them —
  // Vite only injects env files into the client bundle, not the config).
  const fileEnv = loadEnv(mode, __dirname, 'VITE_')
  // Dev-server port; override with VITE_DEV_PORT when 3000 is taken by another checkout.
  const devPort = Number(process.env.VITE_DEV_PORT || fileEnv.VITE_DEV_PORT || 3000)

  return {
    plugins: [react(), versionPlugin(), offlinePlugin()],
    server: {
      host: '0.0.0.0',
      port: devPort,
      strictPort: true,
      allowedHosts: 'all',
      hmr: {
        clientPort: devPort,
      },
      watch: {
        // Native file events avoid continuously scanning the large lab catalog.
        // Docker/network mounts can opt into polling when file events are absent.
        usePolling: process.env.VITE_USE_POLLING === 'true',
        ignored: ['**/dist/**', '**/public/labs/**', '**/*.log'],
      },
      // Only use proxy in development mode when API_URL is not set
      ...(mode !== 'production' && !fileEnv.VITE_API_URL && !process.env.VITE_API_URL && {
        proxy: {
          '/api/v1': {
            // Host `npm run dev` runs OUTSIDE docker, so the docker-internal
            // hostname `backend` doesn't resolve — point at the published
            // localhost port. Override with VITE_PROXY_TARGET (shell env or
            // .env.local) e.g. http://backend:8000 inside the docker network,
            // or https://sashainfinity.com when no local backend exists.
            target: process.env.VITE_PROXY_TARGET || fileEnv.VITE_PROXY_TARGET || 'http://localhost:8000',
            changeOrigin: true,
            secure: false,
            followRedirects: true,
            // Don't rewrite - backend expects /api/v1 prefix
            configure: (proxy, options) => {
              proxy.on('error', (err, req, res) => {
                console.log('proxy error', err);
              });
              proxy.on('proxyReq', (proxyReq, req, res) => {
                // FastAPI handles trailing slashes automatically with redirects
                // Don't modify URLs - let FastAPI handle them
                console.log('Sending Request to the Target:', req.method, req.url);
              });
              proxy.on('proxyRes', (proxyRes, req, res) => {
                console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
              });
            },
          },
          '/uploads': {
            target: process.env.VITE_PROXY_TARGET || fileEnv.VITE_PROXY_TARGET || 'http://localhost:8000',
            changeOrigin: true,
            secure: false,
          },
          '/certificate-files': {
            target: process.env.VITE_PROXY_TARGET || fileEnv.VITE_PROXY_TARGET || 'http://localhost:8000',
            changeOrigin: true,
            secure: false,
          },
        },
      }),
    },
  resolve: {
    // Deduplicate three.js — @react-three/drei and @react-three/fiber can
    // each pull their own copy, causing the "Multiple instances of Three.js"
    // console warning (and subtle bugs with `instanceof` checks).
    dedupe: ['three', 'react', 'react-dom'],
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/pages': path.resolve(__dirname, './src/pages'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/utils': path.resolve(__dirname, './src/utils'),
      '@/types': path.resolve(__dirname, './src/types'),
      '@/store': path.resolve(__dirname, './src/store'),
      '@/api': path.resolve(__dirname, './src/api'),
      '@/assets': path.resolve(__dirname, './src/assets'),
      '@/styles': path.resolve(__dirname, './src/styles'),
    },
  },
  define: {
    // Only expose VITE_-prefixed (public) vars + NODE_ENV to the client bundle.
    // Inlining the whole `process.env` leaked backend secrets into shipped JS.
    'process.env': Object.fromEntries(
      Object.entries(process.env).filter(([k]) => k.startsWith('VITE_') || k === 'NODE_ENV')
    ),
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
        input: { main: path.resolve(__dirname, "index.html"), offline: path.resolve(__dirname, "offline.html") },
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['@headlessui/react', '@heroicons/react', 'lucide-react'],
          query: ['@tanstack/react-query'],
          form: ['react-hook-form', '@hookform/resolvers', 'zod'],
          motion: ['framer-motion'],
        },
        // Add aggressive cache-busting to filenames
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/index-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      'zustand',
      'axios',
      'three'
    ],
  },
  }
})
