import { useCallback, useEffect, useRef, useState } from 'react'
import { api, clearAuth, getToken, saveAuth } from './api'
import AdminView from './components/AdminView'
import AuthScreen, { type AuthView } from './components/AuthScreen'
import ChatView from './components/ChatView'
import Sidebar from './components/Sidebar'
import Toast from './components/Toast'
import type { AuthResponse, AuthStatus, ChatResponse, ConversationDetail, ConversationSummary, Health, KnowledgeStatus, StoredMessage, User, View } from './types'

export default function App() {
  const [booting, setBooting] = useState(true)
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null)
  const [authView, setAuthView] = useState<AuthView>('login')
  const [authBusy, setAuthBusy] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [view, setView] = useState<View>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [health, setHealth] = useState<Health | null>(null)
  const [knowledge, setKnowledge] = useState<KnowledgeStatus | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<StoredMessage[]>([])
  const [chatBusy, setChatBusy] = useState(false)
  const [toast, setToast] = useState({ message: '', error: false })
  const toastTimer = useRef<number | null>(null)

  const showToast = useCallback((message: string, error = false) => {
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
    setToast({ message, error })
    toastTimer.current = window.setTimeout(() => setToast({ message: '', error: false }), 4600)
  }, [])

  const loadConversations = useCallback(async () => {
    try { setConversations(await api<ConversationSummary[]>('/conversations')) }
    catch (error) { showToast((error as Error).message, true) }
  }, [showToast])

  const loadRuntime = useCallback(async () => {
    const results = await Promise.allSettled([api<Health>('/health'), api<KnowledgeStatus>('/knowledge/status')])
    if (results[0].status === 'fulfilled') setHealth(results[0].value)
    if (results[1].status === 'fulfilled') setKnowledge(results[1].value)
  }, [])

  const launch = useCallback(async (nextUser: User) => {
    setUser(nextUser)
    setView('chat')
    setConversationId(null)
    setMessages([])
    await Promise.all([loadConversations(), loadRuntime()])
  }, [loadConversations, loadRuntime])

  useEffect(() => {
    let active = true
    async function boot() {
      try {
        const status = await api<AuthStatus>('/auth/status')
        if (!active) return
        setAuthStatus(status)
        if (getToken()) {
          try {
            const current = await api<User>('/auth/me')
            if (active) await launch(current)
            return
          } catch {
            clearAuth()
          }
        }
        setAuthView(status.requires_setup ? 'setup' : 'login')
      } catch (error) {
        showToast(`Backend indisponível: ${(error as Error).message}`, true)
      } finally {
        if (active) setBooting(false)
      }
    }
    void boot()
    const unauthorized = () => { setUser(null); setAuthView('login') }
    window.addEventListener('aethra:unauthorized', unauthorized)
    return () => { active = false; window.removeEventListener('aethra:unauthorized', unauthorized) }
  }, [launch, showToast])

  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && user) {
        event.preventDefault(); newConversation()
      }
    }
    document.addEventListener('keydown', shortcut)
    return () => document.removeEventListener('keydown', shortcut)
  })

  function newConversation() {
    setConversationId(null)
    setMessages([])
    setView('chat')
    setSidebarOpen(false)
  }

  async function authenticate(action: () => Promise<AuthResponse>): Promise<AuthResponse> {
    setAuthBusy(true)
    try {
      const auth = await action()
      saveAuth(auth)
      await launch(auth.user)
      return auth
    } catch (error) {
      showToast((error as Error).message, true)
      throw error
    } finally { setAuthBusy(false) }
  }

  async function logout() {
    await api('/auth/logout', { method: 'POST' }).catch(() => undefined)
    clearAuth()
    setUser(null)
    setConversations([])
    setConversationId(null)
    setMessages([])
    setAuthView('login')
  }

  async function openConversation(id: string) {
    if (chatBusy) return
    try {
      const conversation = await api<ConversationDetail>(`/conversations/${encodeURIComponent(id)}`)
      setConversationId(conversation.id)
      setMessages(conversation.messages)
      setView('chat')
      setSidebarOpen(false)
    } catch (error) { showToast((error as Error).message, true) }
  }

  async function deleteConversation(id: string, title: string) {
    if (!window.confirm(`Excluir a conversa “${title}”?`)) return
    try {
      await api(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' })
      setConversations((current) => current.filter((item) => item.id !== id))
      if (conversationId === id) newConversation()
      showToast('Conversa excluída.')
    } catch (error) { showToast((error as Error).message, true) }
  }

  async function sendMessage(question: string) {
    if (chatBusy) return
    const now = new Date().toISOString()
    const userMessage: StoredMessage = { id: `local-user-${Date.now()}`, role: 'user', content: question, citations: [], created_at: now }
    const pending: StoredMessage = { id: `local-pending-${Date.now()}`, role: 'assistant', content: '', citations: [], created_at: now, pending: true }
    setMessages((current) => [...current, userMessage, pending])
    setChatBusy(true)
    try {
      const result = await api<ChatResponse>('/assistant/chat', { method: 'POST', body: { pergunta: question, conversation_id: conversationId } })
      setConversationId(result.conversation_id)
      setMessages((current) => current.map((message) => message.id === pending.id ? {
        id: `assistant-${Date.now()}`, role: 'assistant', content: result.resposta,
        citations: result.citations, created_at: new Date().toISOString(),
      } : message))
      await Promise.all([loadConversations(), loadRuntime()])
    } catch (error) {
      const message = (error as Error).message
      setMessages((current) => current.map((item) => item.id === pending.id ? {
        ...item, pending: false, content: `Não consegui concluir a análise. ${message}`,
      } : item))
      showToast(message, true)
    } finally { setChatBusy(false) }
  }

  if (booting) return <div className="app-loading"><div className="aethra-orb"><span>A</span><i /></div><p>Inicializando a inteligência documental...</p></div>

  if (!user) {
    return <><AuthScreen
      status={authStatus}
      view={authView}
      busy={authBusy}
      onView={setAuthView}
      onLogin={(email, password) => authenticate(() => api<AuthResponse>('/auth/login', { method: 'POST', body: { email, password } }))}
      onRegister={(display_name, email, password) => authenticate(() => api<AuthResponse>('/auth/register', { method: 'POST', body: { display_name, email, password } }))}
      onSetup={(payload) => authenticate(() => api<AuthResponse>('/auth/setup', { method: 'POST', body: payload }))}
    /><Toast {...toast} /></>
  }

  const currentConversation = conversations.find((item) => item.id === conversationId)
  return (
    <div className="app-shell">
      <Sidebar
        open={sidebarOpen}
        companyName={authStatus?.company_name ?? 'Intelligence'}
        user={user}
        conversations={conversations}
        conversationId={conversationId}
        onClose={() => setSidebarOpen(false)}
        onView={(next) => { setView(next); setSidebarOpen(false) }}
        onNew={newConversation}
        onOpenConversation={(id) => void openConversation(id)}
        onDeleteConversation={(id, title) => void deleteConversation(id, title)}
        onRefresh={() => void loadConversations()}
        onLogout={() => void logout()}
      />
      <main className="workspace">
        {view === 'chat' ? (
          <ChatView user={user} health={health} title={currentConversation?.title ?? 'Nova conversa'} messages={messages} busy={chatBusy} documentCount={knowledge?.document_count ?? 0} onMenu={() => setSidebarOpen(true)} onSend={sendMessage} />
        ) : (
          <AdminView currentUser={user} onBack={() => setView('chat')} onToast={showToast} />
        )}
      </main>
      <Toast {...toast} />
    </div>
  )
}
