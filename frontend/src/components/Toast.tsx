interface Props {
  message: string
  error: boolean
}

export default function Toast({ message, error }: Props) {
  if (!message) return null
  return (
    <div className={`toast${error ? ' error' : ''}`} role="status">
      {message}
    </div>
  )
}
