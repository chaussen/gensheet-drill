import { useMemo } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const KATEX_OPTS = { throwOnError: false, errorColor: '#cc0000', displayMode: false }

// Split "text $expr$ more" into segments.
// Odd-indexed segments are math; even-indexed are plain text.
// \$ in source is an escaped dollar sign (currency) — rendered as literal "$".
const DOLLAR_ESC = '\uFFFD'
const DOLLAR_ESC_RE = new RegExp(DOLLAR_ESC, 'g')

function latexSegments(text) {
  if (!text) return []
  const safe = String(text).replace(/\\\$/g, DOLLAR_ESC)
  const parts = safe.split(/\$([^$]+)\$/g)
  return parts.map((part, i) => ({ math: i % 2 === 1, text: part.replace(DOLLAR_ESC_RE, '$') }))
}

export default function MathText({ children, className }) {
  const segments = useMemo(() => latexSegments(children), [children])
  return (
    <span className={className}>
      {segments.map((seg, i) => {
        if (!seg.math) return seg.text || null
        try {
          const html = katex.renderToString(seg.text, KATEX_OPTS)
          return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />
        } catch {
          return <span key={i}>{seg.text}</span>
        }
      })}
    </span>
  )
}
