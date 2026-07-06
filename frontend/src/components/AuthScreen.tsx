import { type FormEvent, useEffect, useState } from 'react'
import type { AuthResponse, AuthStatus } from '../types'

export type AuthView = 'login' | 'register' | 'setup'

interface Props {
  status: AuthStatus | null
  view: AuthView
  busy: boolean
  onView: (view: AuthView) => void
  onLogin: (email: string, password: string) => Promise<AuthResponse>
  onRegister: (name: string, email: string, password: string) => Promise<AuthResponse>
  onSetup: (payload: Record<string, string>) => Promise<AuthResponse>
}

function PasswordField({ id, value, onChange, placeholder, required, current }: {
  id: string
  value: string
  onChange: (value: string) => void
  placeholder: string
  required?: boolean
  current?: boolean
}) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="password-field">
      <input
        id={id}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={current ? 'current-password' : 'new-password'}
        placeholder={placeholder}
        required={required ?? true}
      />
      <button type="button" className="password-toggle" onClick={() => setVisible((current) => !current)} aria-label="Exibir senha">
        {visible ? '○' : '◉'}
      </button>
    </div>
  )
}

export default function AuthScreen({ status, view, busy, onView, onLogin, onRegister, onSetup }: Props) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tursoUrl, setTursoUrl] = useState('')
  const [tursoToken, setTursoToken] = useState('')

  useEffect(() => {
    if (view === 'setup' && status?.admin_email) setEmail(status.admin_email)
  }, [status, view])

  const copy = {
    login: ['Acesso seguro', 'Bem-vindo de volta', 'Entre para conversar com o conhecimento da empresa.'],
    register: ['Novo acesso', 'Crie sua conta', 'Use seu e-mail corporativo e uma senha forte.'],
    setup: ['Configuração inicial', 'Prepare sua Aethra', 'Conecte o armazenamento e crie o primeiro administrador.'],
  }[view]

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (view === 'login') await onLogin(email.trim(), password)
    if (view === 'register') await onRegister(name.trim(), email.trim(), password)
    if (view === 'setup') {
      const payload: Record<string, string> = { display_name: name.trim(), email: email.trim(), password }
      if (tursoUrl.trim() && tursoToken.trim()) {
        payload.turso_database_url = tursoUrl.trim()
        payload.turso_auth_token = tursoToken.trim()
      }
      await onSetup(payload)
    }
    setPassword('')
    setTursoToken('')
  }

  return (
    <section className="auth-screen">
      <div className="auth-visual">
        <div className="auth-image" aria-hidden="true" />
        <div className="auth-shade" aria-hidden="true" />
        <a className="brand brand-light" href="#">
          <span className="brand-symbol">A</span><span><strong>Aethra</strong><small>Inteligência documental</small></span>
        </a>
        <div className="auth-story">
          <span className="eyebrow"><i /> IA privada com fontes verificáveis</span>
          <h1>O conhecimento da empresa,<br /><em>pronto para conversar.</em></h1>
          <p>Encontre respostas em documentos corporativos com contexto preservado, correlação entre fontes e referências em cada análise.</p>
          <div className="trust-row"><span>Modelo local</span><span>Google Drive</span><span>Respostas citadas</span></div>
        </div>
        <small className="auth-footer">PRIVATE BY DESIGN · GROUNDED BY SOURCES</small>
      </div>

      <div className="auth-entry">
        <div className="auth-card">
          <div className="mobile-brand"><span className="brand-symbol">A</span><strong>Aethra</strong></div>
          <span className="card-kicker">{copy[0]}</span>
          <h2>{copy[1]}</h2>
          <p>{copy[2]}</p>

          <form className={`auth-form${view === 'setup' ? ' setup-form' : ''}`} onSubmit={(event) => void submit(event)}>
            {view === 'setup' && (
              <>
                <div className="setup-note"><b>Primeiro acesso</b><span>Configure o armazenamento seguro e crie o administrador.</span></div>
                <label htmlFor="setup-turso-url">URL do Turso</label>
                <input
                  id="setup-turso-url"
                  value={tursoUrl}
                  onChange={(event) => setTursoUrl(event.target.value)}
                  required={!status?.storage_online}
                  placeholder={status?.storage_online ? 'Armazenamento já configurado' : 'libsql://seu-banco.turso.io'}
                />
                <label htmlFor="setup-turso-token">Novo token do Turso</label>
                <PasswordField id="setup-turso-token" value={tursoToken} onChange={setTursoToken} required={!status?.storage_online} placeholder={status?.storage_online ? 'Não é necessário informar novamente' : 'Cole um token recém-criado'} />
                <p className="field-help">O token vai ao backend criptografado e nunca fica salvo no navegador.</p>
                <div className="form-divider"><span>Administrador</span></div>
              </>
            )}

            {view !== 'login' && <><label htmlFor="auth-name">Nome</label><input id="auth-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} required placeholder="Seu nome" /></>}
            <label htmlFor="auth-email">E-mail</label>
            <input id="auth-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} readOnly={view === 'setup' && Boolean(status?.admin_email)} required placeholder="voce@empresa.com" autoComplete="email" />
            <label htmlFor="auth-password">Senha</label>
            <PasswordField id="auth-password" value={password} onChange={setPassword} current={view === 'login'} placeholder={view === 'login' ? 'Sua senha' : 'Mínimo de 12 caracteres'} />
            <button className="button button-primary button-wide" disabled={busy} type="submit">
              <span>{busy ? 'Aguarde...' : view === 'login' ? 'Entrar' : view === 'register' ? 'Criar conta' : 'Ativar Aethra'}</span><b>→</b>
            </button>
            {view === 'login' && status?.registration_enabled && <p className="auth-switch">Ainda não tem acesso? <button type="button" onClick={() => onView('register')}>Criar conta</button></p>}
            {view === 'register' && <p className="auth-switch">Já tem acesso? <button type="button" onClick={() => onView('login')}>Entrar</button></p>}
          </form>
        </div>
      </div>
    </section>
  )
}
