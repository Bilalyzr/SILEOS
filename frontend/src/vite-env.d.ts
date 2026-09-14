/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_BACKEND_URL?: string
  readonly VITE_FRONTEND_URL?: string
  readonly VITE_RAZORPAY_KEY?: string
  readonly VITE_FIREBASE_API_KEY?: string
  readonly VITE_FIREBASE_AUTH_DOMAIN?: string
  readonly VITE_FIREBASE_PROJECT_ID?: string
  readonly VITE_FIREBASE_STORAGE_BUCKET?: string
  readonly VITE_FIREBASE_MESSAGING_SENDER_ID?: string
  readonly VITE_FIREBASE_APP_ID?: string
  readonly VITE_DEBUG_API?: string
  readonly DEV?: boolean
  readonly MODE?: string
  readonly PROD?: boolean
  readonly SSR?: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
