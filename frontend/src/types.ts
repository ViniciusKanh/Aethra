export type Role = 'admin' | 'user'
export type View = 'chat' | 'admin'

export interface User {
  id: string
  email: string
  display_name: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface AuthStatus {
  enabled: boolean
  registration_enabled: boolean
  storage_configured: boolean
  storage_online: boolean
  requires_setup: boolean
  admin_email: string | null
  company_name: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_at: string
  user: User
}

export interface Health {
  status: string
  api: string
  provider: string
  provider_status: string
  default_chat_model: string
}

export interface Citation {
  index: number
  file_id: string
  file_name: string
  file_type: string
  location: string
  page: number | null
  excerpt: string
  web_url: string
}

export interface StoredMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  created_at: string
  pending?: boolean
}

export interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ConversationDetail extends ConversationSummary {
  messages: StoredMessage[]
}

export interface ChatResponse {
  status: string
  model: string
  resposta: string
  conversation_id: string
  used_knowledge: boolean
  citations: Citation[]
  metadados: Record<string, unknown>
}

export interface AdminConfig {
  environment: string
  provider: string
  chat_model: string
  embedding_model: string
  request_timeout: number
  company_name: string
  registration_enabled: boolean
  turso_database_url: string | null
  turso_token_configured: boolean
  turso_online: boolean
  knowledge_enabled: boolean
  knowledge_folder_id: string | null
  knowledge_credentials_configured: boolean
  knowledge_service_account_email: string | null
  knowledge_embedding_model: string
  knowledge_top_k: number
  knowledge_chunk_size: number
  knowledge_chunk_overlap: number
}

export interface KnowledgeStatus {
  status: 'pending' | 'indexing' | 'ready' | 'error'
  enabled: boolean
  configured: boolean
  folder_id: string | null
  service_account_email: string | null
  embedding_model: string | null
  last_sync_at: string | null
  document_count: number
  page_count: number
  chunk_count: number
  error: string | null
}

export interface KnowledgeSync extends KnowledgeStatus {
  files: string[]
}
