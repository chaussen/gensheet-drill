import { CONTACT_EMAIL, CONTACT_FOOTER_TEXT } from '../config/contact.js'

export default function Footer() {
  return (
    <footer className="text-center text-xs text-slate-400 py-4 px-4">
      {CONTACT_FOOTER_TEXT.split(CONTACT_EMAIL).map((part, i, arr) =>
        i < arr.length - 1 ? (
          <span key={i}>
            {part}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-slate-400 hover:text-slate-600 underline underline-offset-2">
              {CONTACT_EMAIL}
            </a>
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </footer>
  )
}
