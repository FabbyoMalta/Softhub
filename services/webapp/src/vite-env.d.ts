/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_FEATURE_ADMIN?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
