import { type FormEvent, useEffect, useRef, useState } from 'react'
import type { Citation, Health, StoredMessage, User } from '../types'
import { firstName, formatDate, initials } from '../utils'
import MarkdownAnswer from './MarkdownAnswer'

interface Props {
  user: User
  health: Health | null
  title: string
  messages: StoredMessage[]
  busy: boolean
  documentCount: number
  onMenu: () => void
  onSend: (question: string) => Promise<void>
}

function Citations({ items }: { items: Citation[] }) {
  if (!items.length) return null
  return (
    <section className="citations">
      <span className="citations-title">{items.length} fonte{items.length === 1 ? '' : 's'} consultada{items.length === 1 ? '' : 's'}</span>
      {items.map((source) => (
        <a className="citation" href={source.web_url} target="_blank" rel="noopener noreferrer" key={`${source.file_id}-${source.index}-${source.location}`}>
          <span className="citation-index">[{source.index}]</span>
          <div><strong>{source.file_name}</strong><p>{source.excerpt}</p></div>
          <small>{source.file_type} · {source.location}</small>
        </a>
      ))}
    </section>
  )
}

export default function ChatView({ user, health, title, messages, busy, documentCount, onMenu, onSend }: Props) {
  const [prompt, setPrompt] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const online = health?.provider_status === 'online'

  useEffect(() => {
    const area = textareaRef.current
    if (!area) return
    area.style.height = 'auto'
    area.style.height = `${Math.min(area.scrollHeight, 150)}px`
  }, [prompt])

  useEffect(() => {
    const element = scrollRef.current
    if (element) element.scrollTop = element.scrollHeight
  }, [messages])

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const question = prompt.trim()
    if (!question || busy) return
    setPrompt('')
    await onSend(question)
    textareaRef.current?.focus()
  }

  const suggestions = [
    ['01 · VISÃO GERAL', 'Quais são os temas mais importantes e como eles se relacionam?', 'Correlacione os principais temas encontrados nos documentos e explique como eles se relacionam.'],
    ['02 · PROCESSOS', 'Mapeie processos, papéis e dependências', 'Mapeie os processos, responsáveis e dependências descritos nos documentos, correlacionando fontes diferentes.'],
    ['03 · ANÁLISE', 'Encontre riscos, contradições e lacunas', 'Identifique riscos, contradições, lacunas e prazos nos documentos e compare as evidências.'],
  ]

  return (
    <section className="view chat-view">
      <header className="topbar">
        <button className="icon-button mobile-only" type="button" onClick={onMenu} aria-label="Abrir menu">☰</button>
        <div className="conversation-title"><span className="live-dot" /><strong>{title}</strong></div>
        <div className="runtime-badge"><span className={online ? 'online' : ''} /><b>{online ? 'IA online' : 'IA indisponível'}</b><small>{health?.default_chat_model ?? 'modelo local'}</small></div>
      </header>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-chat">
            <div className="aethra-orb"><span>A</span><i /></div>
            <span className="eyebrow blue"><i /> Conhecimento correlacionado</span>
            <h1>Olá, <span>{firstName(user.display_name)}</span></h1>
            <p>Faça perguntas complexas. A Aethra cruza evidências entre documentos, estrutura a análise e mostra as fontes utilizadas.</p>
            <div className="suggestion-grid">
              {suggestions.map(([label, text, question]) => (
                <button type="button" key={label} onClick={() => void onSend(question)}><span>{label}</span><b>{text}</b><i>→</i></button>
              ))}
            </div>
          </div>
        )}
        <div className="chat-messages" aria-live="polite">
          {messages.map((message) => (
            <article className={`message ${message.role}`} key={message.id}>
              <span className="message-avatar">{message.role === 'assistant' ? 'A' : initials(user.display_name)}</span>
              <div className="message-main">
                <div className="message-meta"><b>{message.role === 'assistant' ? 'Aethra' : user.display_name}</b><span>{message.pending ? 'analisando fontes' : formatDate(message.created_at, true)}</span></div>
                {message.pending ? <div className="typing"><i /><i /><i /></div> : message.role === 'assistant' ? <MarkdownAnswer>{message.content}</MarkdownAnswer> : <div className="message-content">{message.content}</div>}
                <Citations items={message.citations} />
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="composer-wrap">
        <form className="composer" onSubmit={(event) => void submit(event)}>
          <textarea
            ref={textareaRef}
            rows={1}
            maxLength={2000}
            required
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit() }
            }}
            placeholder="Pergunte e peça para correlacionar os documentos..."
          />
          <div className="composer-bottom"><span><i /> {documentCount} documento{documentCount === 1 ? '' : 's'} conectado{documentCount === 1 ? '' : 's'}</span><small>Enter para enviar · Shift + Enter para quebrar linha</small><button disabled={busy || !prompt.trim()} type="submit" aria-label="Enviar pergunta">↑</button></div>
        </form>
        <p className="disclaimer">A Aethra pode cometer erros. Confirme informações críticas nas fontes citadas.</p>
      </div>
    </section>
  )
}
