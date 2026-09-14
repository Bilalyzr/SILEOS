// Firebase client config for Google OAuth sign-in.
// Lazy initialization to avoid crashes when env vars are missing.

import { initializeApp, getApps, type FirebaseApp } from 'firebase/app'
import { GoogleAuthProvider, getAuth, type Auth } from 'firebase/auth'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export const isFirebaseConfigured =
  Boolean(firebaseConfig.apiKey) && Boolean(firebaseConfig.projectId)

let _app: FirebaseApp | null = null
let _auth: Auth | null = null
let _provider: GoogleAuthProvider | null = null

function getOrInitApp(): FirebaseApp {
  if (!_app) {
    if (!isFirebaseConfigured) {
      throw new Error(
        'Google sign-in is not configured. Set VITE_FIREBASE_API_KEY and VITE_FIREBASE_PROJECT_ID env vars.'
      )
    }
    _app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig)
  }
  return _app
}

// Export function to get auth instance
export function getAuthInstance(): Auth {
  if (!_auth) {
    _auth = getAuth(getOrInitApp())
  }
  return _auth
}

// Export function to get provider instance (real object, not proxy)
export function getGoogleProviderInstance(): GoogleAuthProvider {
  if (!_provider) {
    _provider = new GoogleAuthProvider()
    _provider.setCustomParameters({ prompt: 'select_account' })
    _provider.addScope('email')
    _provider.addScope('profile')
  }
  return _provider
}

// Backwards-compatible named exports using Proxy
export const auth: Auth = new Proxy({} as Auth, {
  get(_target, prop) {
    return getAuthInstance()[prop as keyof Auth]
  },
  has(_target, prop) {
    return prop in getAuthInstance()
  },
})

// NOTE: googleProvider is a Proxy but for signInWithPopup you should
// use getGoogleProviderInstance() to get the real object
export const googleProvider: GoogleAuthProvider = new Proxy({} as GoogleAuthProvider, {
  get(_target, prop) {
    return getGoogleProviderInstance()[prop as keyof GoogleAuthProvider]
  },
  has(_target, prop) {
    return prop in getGoogleProviderInstance()
  },
})
