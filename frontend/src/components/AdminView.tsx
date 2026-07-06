import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { AdminConfig, KnowledgeStatus, KnowledgeSync, User } from '../types'
import { formatDate, initials } from '../utils'

type Tab = 'knowledge' | 'users' | 'system'

interface Props {
  currentUser: User
  onBack: () => void
  onToast: (message: string, error?: boolean) => void
}

const initialKnowledge: KnowledgeStatus = {
  status: 'pending', enabled: false, configured: false, folder_id: null,
  service_account_email: null, embedding_model: null, last_sync_at: null,
  document_count: 0, page_count: 0, chunk_count: 0, error: null,
}

export default function AdminView({ currentUser, onBack, onToast }: Props) {
  const [tab, setTab] = useState<Tab>('knowledge')
  const [config, setConfig] = useState<AdminConfig | null>(null)
  const [knowledge, setKnowledge] = useState<KnowledgeStatus>(initialKnowledge)
  const [users, setUsers] = useState<User[]>([])
  const [busy, setBusy] = useState('')
  const [folder, setFolder] = useState('')
  const [credential, setCredential] = useState('')
  const [embedding, setEmbedding] = useState('qwen3-embedding:0.6b')
  const [topK, setTopK] = useState(8)
  const [chunkSize, setChunkSize] = useState(1200)
  const [overlap, setOverlap] = useState(180)
  const [tursoUrl, setTursoUrl] = useState('')
  const [tursoToken, setTursoToken] = useState('')

  const applyConfig = useCallback((next: AdminConfig) => {
    setConfig(next)
    setFolder(next.knowledge_folder_id ?? '')
    setCredential('')
    setEmbedding(next.knowledge_embedding_model || 'qwen3-embedding:0.6b')
    setTopK(next.knowledge_top_k || 8)
    setChunkSize(next.knowledge_chunk_size || 1200)
    setOverlap(next.knowledge_chunk_overlap ?? 180)
    setTursoUrl(next.turso_database_url ?? '')
    setTursoToken('')
  }, [])

  const load = useCallback(async () => {
    try {
      const [nextConfig, nextKnowledge, nextUsers] = await Promise.all([
        api<AdminConfig>('/admin/config'),
        api<KnowledgeStatus>('/admin/knowledge/status'),
        api<User[]>('/admin/users'),
      ])
      applyConfig(nextConfig)
      setKnowledge(nextKnowledge)
      setUsers(nextUsers)
    } catch (error) {
      onToast((error as Error).message, true)
    }
  }, [applyConfig, onToast])

  useEffect(() => { void load() }, [load])

  async function saveKnowledge(event: FormEvent) {
    event.preventDefault()
    setBusy('knowledge-save')
    try {
      const body: Record<string, unknown> = {
        enabled: true, folder_id: folder.trim(), embedding_model: embedding.trim(),
        top_k: topK, chunk_size: chunkSize, chunk_overlap: overlap,
      }
      if (credential.trim()) body.service_account_json = credential.trim()
      applyConfig(await api<AdminConfig>('/admin/knowledge/config', { method: 'PUT', body }))
      onToast('Configuração documental salva.')
    } catch (error) { onToast((error as Error).message, true) }
    finally { setBusy('') }
  }

  async function testKnowledge() {
    setBusy('knowledge-test')
    try {
      const result = await api<{ folder_name?: string; status?: string }>('/admin/knowledge/test', { method: 'POST' })
      onToast(`Google Drive conectado: ${result.folder_name ?? result.status ?? 'acesso confirmado'}.`)
    } catch (error) { onToast((error as Error).message, true) }
    finally { setBusy('') }
  }

  async function syncKnowledge() {
    setBusy('knowledge-sync')
    setKnowledge((current) => ({ ...current, status: 'indexing', error: null }))
    try {
      const result = await api<KnowledgeSync>('/admin/knowledge/sync', { method: 'POST' })
      setKnowledge(result)
      onToast(`${result.document_count} documento(s) sincronizado(s).`)
    } catch (error) {
      const message = (error as Error).message
      setKnowledge((current) => ({ ...current, status: 'error', error: message }))
      onToast(message, true)
    } finally { setBusy('') }
  }

  async function saveTurso(event: FormEvent) {
    event.preventDefault()
    setBusy('turso-save')
    try {
      const body: Record<string, string> = { database_url: tursoUrl.trim() }
      if (tursoToken.trim()) body.auth_token = tursoToken.trim()
      applyConfig(await api<AdminConfig>('/admin/turso/config', { method: 'PUT', body }))
      onToast('Armazenamento atualizado.')
    } catch (error) { onToast((error as Error).message, true) }
    finally { setBusy('') }
  }

  async function testTurso() {
    setBusy('turso-test')
    try {
      await api('/admin/turso/test', { method: 'POST' })
      onToast('Conexão com o Turso confirmada.')
    } catch (error) { onToast((error as Error).message, true) }
    finally { setBusy('') }
  }

  async function updateUser(userId: string, patch: { role?: string; is_active?: boolean }) {
    try {
      await api(`/admin/users/${encodeURIComponent(userId)}`, { method: 'PATCH', body: patch })
      setUsers(await api<User[]>('/admin/users'))
      onToast('Acesso atualizado.')
    } catch (error) { onToast((error as Error).message, true); await load() }
  }

  const badgeLabel = { pending: 'Aguardando', indexing: 'Indexando', ready: 'Pronto', error: 'Com erro' }[knowledge.status]

  return (
    <section className="view admin-view">
      <header className="admin-header">
        <button className="icon-button mobile-only" type="button" onClick={onBack}>←</button>
        <div><span className="eyebrow blue"><i /> Área restrita</span><h1>Administração</h1><p>Configure a base de conhecimento e os acessos da empresa.</p></div>
        <button className="button button-secondary" type="button" onClick={onBack}>Voltar ao chat</button>
      </header>
      <div className="admin-tabs" role="tablist">
        <button className={tab === 'knowledge' ? 'active' : ''} type="button" onClick={() => setTab('knowledge')}>Base de conhecimento</button>
        <button className={tab === 'users' ? 'active' : ''} type="button" onClick={() => setTab('users')}>Usuários</button>
        <button className={tab === 'system' ? 'active' : ''} type="button" onClick={() => setTab('system')}>Sistema</button>
      </div>

      {tab === 'knowledge' && (
        <div className="admin-panel">
          <article className="config-card config-feature">
            <div className="card-heading"><div className="card-icon">G</div><div><span className="card-kicker">Fonte documental</span><h2>Google Drive</h2><p>A pasta é lida em modo somente leitura e transformada em uma base pesquisável pela IA.</p></div><span className={`status-badge${knowledge.status === 'ready' ? '' : knowledge.status === 'error' ? ' error' : ' muted'}`}>{badgeLabel}</span></div>
            <form className="config-form" onSubmit={(event) => void saveKnowledge(event)}>
              <label htmlFor="knowledge-folder">ID ou link da pasta</label><input id="knowledge-folder" value={folder} onChange={(event) => setFolder(event.target.value)} required />
              <label htmlFor="knowledge-service-json">Credencial da service account</label><textarea id="knowledge-service-json" rows={4} value={credential} onChange={(event) => setCredential(event.target.value)} placeholder={config?.knowledge_credentials_configured ? 'Credencial configurada — cole outro JSON apenas para substituir' : 'Cole o JSON da service account'} />
              <p className="field-help">{config?.knowledge_service_account_email ? `Pasta compartilhada com ${config.knowledge_service_account_email}` : 'Compartilhe a pasta como leitor com o e-mail da service account.'}</p>
              <div className="form-grid three">
                <div><label htmlFor="knowledge-embedding">Modelo de embedding</label><input id="knowledge-embedding" value={embedding} onChange={(event) => setEmbedding(event.target.value)} required /></div>
                <div><label htmlFor="knowledge-top-k">Profundidade da busca</label><input id="knowledge-top-k" type="number" min={4} max={20} value={topK} onChange={(event) => setTopK(Number(event.target.value))} /></div>
                <div><label htmlFor="knowledge-chunk-size">Tamanho dos trechos</label><input id="knowledge-chunk-size" type="number" min={300} max={4000} value={chunkSize} onChange={(event) => setChunkSize(Number(event.target.value))} /></div>
              </div>
              <input type="hidden" value={overlap} onChange={(event) => setOverlap(Number(event.target.value))} />
              <div className="format-row"><span>PDF</span><span>DOCX</span><span>TXT</span><span>MD</span><span>CSV</span><span>JSON</span><span>HTML</span><span>YAML</span></div>
              <div className="form-actions">
                <button className="button button-secondary" disabled={Boolean(busy)} type="submit">{busy === 'knowledge-save' ? 'Salvando...' : 'Salvar configuração'}</button>
                <button className="button button-ghost" disabled={Boolean(busy)} type="button" onClick={() => void testKnowledge()}>{busy === 'knowledge-test' ? 'Testando...' : 'Testar acesso'}</button>
                <button className="button button-primary" disabled={Boolean(busy)} type="button" onClick={() => void syncKnowledge()}>{busy === 'knowledge-sync' ? 'Indexando em lotes...' : 'Sincronizar documentos'}</button>
              </div>
            </form>
          </article>
          <div className="metric-grid">
            <article><span>Documentos</span><strong>{knowledge.document_count}</strong><small>arquivos indexados</small></article>
            <article><span>Páginas</span><strong>{knowledge.page_count}</strong><small>conteúdo processado</small></article>
            <article><span>Trechos</span><strong>{knowledge.chunk_count}</strong><small>unidades pesquisáveis</small></article>
            <article><span>Última sincronização</span><strong className="metric-date">{formatDate(knowledge.last_sync_at, true)}</strong><small>{knowledge.error ?? (knowledge.configured ? 'Base documental pronta' : 'Aguardando configuração')}</small></article>
          </div>
        </div>
      )}

      {tab === 'users' && (
        <div className="admin-panel"><article className="config-card">
          <div className="card-heading"><div className="card-icon">U</div><div><span className="card-kicker">Controle de acesso</span><h2>Usuários</h2><p>Gerencie perfis e bloqueie acessos sem apagar o histórico.</p></div></div>
          <div className="table-wrap"><table><thead><tr><th>Usuário</th><th>Perfil</th><th>Status</th><th>Criado em</th><th>Ação</th></tr></thead><tbody>
            {users.map((user) => <tr key={user.id}>
              <td><div className="user-cell"><span className="avatar">{initials(user.display_name)}</span><span><b>{user.display_name}</b><small>{user.email}</small></span></div></td>
              <td><select className="role-select" disabled={user.id === currentUser.id} value={user.role} onChange={(event) => void updateUser(user.id, { role: event.target.value })}><option value="user">Usuário</option><option value="admin">Administrador</option></select></td>
              <td><span className={`status-badge${user.is_active ? '' : ' error'}`}>{user.is_active ? 'Ativo' : 'Bloqueado'}</span></td>
              <td>{formatDate(user.created_at)}</td>
              <td><button className={`status-toggle ${user.is_active ? 'inactive' : 'active'}`} disabled={user.id === currentUser.id} type="button" onClick={() => void updateUser(user.id, { is_active: !user.is_active })}>{user.is_active ? 'Bloquear' : 'Reativar'}</button></td>
            </tr>)}
          </tbody></table></div>
        </article></div>
      )}

      {tab === 'system' && (
        <div className="admin-panel"><div className="system-grid">
          <article className="config-card"><div className="card-heading"><div className="card-icon">T</div><div><span className="card-kicker">Persistência</span><h2>Turso</h2><p>Usuários, sessões e conversas ficam armazenados com segurança.</p></div><span className={`status-badge${config?.turso_online ? '' : ' error'}`}>{config?.turso_online ? 'Online' : 'Indisponível'}</span></div>
            <form className="config-form" onSubmit={(event) => void saveTurso(event)}><label htmlFor="turso-url">URL do banco</label><input id="turso-url" required value={tursoUrl} onChange={(event) => setTursoUrl(event.target.value)} /><label htmlFor="turso-token">Novo token</label><input id="turso-token" type="password" value={tursoToken} onChange={(event) => setTursoToken(event.target.value)} placeholder="Deixe vazio para manter o atual" /><p className="field-help">O token atual nunca é exibido.</p><div className="form-actions"><button className="button button-primary" disabled={Boolean(busy)} type="submit">{busy === 'turso-save' ? 'Salvando...' : 'Salvar'}</button><button className="button button-ghost" disabled={Boolean(busy)} type="button" onClick={() => void testTurso()}>{busy === 'turso-test' ? 'Testando...' : 'Testar conexão'}</button></div></form>
          </article>
          <article className="config-card runtime-card"><div className="card-heading"><div className="card-icon">AI</div><div><span className="card-kicker">Execução local</span><h2>Runtime da IA</h2><p>Diagnóstico sem expor segredos.</p></div></div><dl><div><dt>Provider</dt><dd>{config?.provider ?? '—'}</dd></div><div><dt>Modelo de chat</dt><dd>{config?.chat_model ?? '—'}</dd></div><div><dt>Modelo vetorial</dt><dd>{config?.embedding_model ?? '—'}</dd></div><div><dt>Ambiente</dt><dd>{config?.environment ?? '—'}</dd></div></dl></article>
        </div></div>
      )}
    </section>
  )
}
