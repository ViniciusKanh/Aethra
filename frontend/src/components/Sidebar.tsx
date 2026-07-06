import type { ConversationSummary, User, View } from '../types'
import { formatDate, initials } from '../utils'

interface Props {
  open: boolean
  companyName: string
  user: User
  conversations: ConversationSummary[]
  conversationId: string | null
  onClose: () => void
  onView: (view: View) => void
  onNew: () => void
  onOpenConversation: (id: string) => void
  onDeleteConversation: (id: string, title: string) => void
  onRefresh: () => void
  onLogout: () => void
}

export default function Sidebar({ open, companyName, user, conversations, conversationId, onClose, onView, onNew, onOpenConversation, onDeleteConversation, onRefresh, onLogout }: Props) {
  return (
    <>
      {open && <button className="mobile-overlay" type="button" aria-label="Fechar menu" onClick={onClose} />}
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="sidebar-head">
          <button className="brand brand-button" type="button" onClick={() => onView('chat')}>
            <span className="brand-symbol">A</span><span><strong>Aethra</strong><small>{companyName}</small></span>
          </button>
          <button className="icon-button mobile-only" type="button" onClick={onClose} aria-label="Fechar menu">×</button>
        </div>
        <button className="new-chat" type="button" onClick={onNew}><span>＋</span> Nova conversa <kbd>⌘ K</kbd></button>
        <div className="history-head"><span>Conversas</span><button type="button" onClick={onRefresh} title="Atualizar">↻</button></div>
        <nav className="conversation-list" aria-label="Histórico de conversas">
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`conversation-item${conversation.id === conversationId ? ' active' : ''}`}
              role="button"
              tabIndex={0}
              onClick={() => onOpenConversation(conversation.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') onOpenConversation(conversation.id)
              }}
            >
              <span><b>{conversation.title}</b><small>{formatDate(conversation.updated_at)} · {conversation.message_count} mensagens</small></span>
              <button
                type="button"
                className="conversation-delete"
                title="Excluir conversa"
                onClick={(event) => { event.stopPropagation(); onDeleteConversation(conversation.id, conversation.title) }}
              >×</button>
            </div>
          ))}
        </nav>
        {conversations.length === 0 && <div className="history-empty">Suas conversas aparecerão aqui.</div>}
        <div className="sidebar-bottom">
          {user.role === 'admin' && (
            <button className="admin-link" type="button" onClick={() => onView('admin')}>
              <span>⚙</span><span><b>Administração</b><small>Fontes, usuários e sistema</small></span>
            </button>
          )}
          <div className="profile-mini">
            <span className="avatar">{initials(user.display_name)}</span>
            <div><strong>{user.display_name}</strong><small>{user.role === 'admin' ? 'Administrador' : 'Usuário'}</small></div>
            <button className="icon-button" type="button" title="Sair" onClick={onLogout}>↗</button>
          </div>
        </div>
      </aside>
    </>
  )
}
