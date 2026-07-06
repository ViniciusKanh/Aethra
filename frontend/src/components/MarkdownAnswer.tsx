import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  children: string
}

export default function MarkdownAnswer({ children }: Props) {
  return (
    <div className="markdown-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          a: ({ children: label, href }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {label}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
