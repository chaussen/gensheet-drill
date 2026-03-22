import { InlineMath } from 'react-katex'
import { toLatex } from '../utils/math.js'

// Matches math tokens that need KaTeX rendering:
// √N, √(expr), ∛N, ∛(expr), N², N³, N⁴, N/M, × ÷
const MATH_TOKEN_RE = /√(?:\([^)]+\)|\d+(?:\.\d+)?)|∛(?:\([^)]+\)|\d+(?:\.\d+)?)|[²³⁴]|\d+\/\d+|[×÷]/g

export default function MathText({ text, latex, className }) {
  if (!latex) return <span className={className}>{text}</span>

  const segments = []
  let lastIndex = 0

  for (const match of text.matchAll(MATH_TOKEN_RE)) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    segments.push({ type: 'math', content: toLatex(match[0]) })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) })
  }

  if (segments.length === 0) return <span className={className}>{text}</span>

  return (
    <span className={className}>
      {segments.map((seg, i) =>
        seg.type === 'math'
          ? <InlineMath key={i} math={seg.content} renderError={() => <span>{seg.content}</span>} />
          : <span key={i}>{seg.content}</span>
      )}
    </span>
  )
}
