export function initials(name = 'Aethra'): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export function formatDate(value?: string | null, includeTime = false): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(
    'pt-BR',
    includeTime
      ? { dateStyle: 'short', timeStyle: 'short' }
      : { day: '2-digit', month: 'short', year: 'numeric' },
  ).format(date)
}

export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] || 'como posso ajudar?'
}
