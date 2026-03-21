import { useState, useEffect } from 'react'

const OPTION_LABELS = ['A', 'B', 'C', 'D']

export default function DrillQuestion({ question, questionNumber, totalQuestions, onAnswer }) {
  const [selected, setSelected] = useState(null)
  const [locked, setLocked]     = useState(false)

  useEffect(() => {
    setSelected(null)
    setLocked(false)
  }, [question.question_id])

  function handleSelect(index) {
    if (locked) return
    setSelected(index)
    setLocked(true)
    setTimeout(() => onAnswer(index), 300)
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
      <p className="text-xs font-medium text-indigo-500 uppercase tracking-wide mb-3">
        Question {questionNumber} of {totalQuestions}
      </p>

      <p className="text-lg font-medium text-slate-800 mb-6 leading-relaxed">
        {question.question_text}
      </p>

      <div className="space-y-3">
        {question.options.map((opt, i) => {
          const isSelected = selected === i
          return (
            <button
              key={i}
              onClick={() => handleSelect(i)}
              disabled={locked && !isSelected}
              className={[
                'w-full text-left px-4 py-3 rounded-xl border-2 transition-colors flex items-center gap-3',
                isSelected
                  ? 'bg-indigo-600 border-indigo-600 text-white'
                  : 'bg-white border-slate-200 text-slate-800 hover:border-indigo-300 hover:bg-slate-50',
                locked && !isSelected ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer',
              ].join(' ')}
            >
              <span className={[
                'flex-shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold',
                isSelected ? 'border-white text-white' : 'border-slate-300 text-slate-500',
              ].join(' ')}>
                {OPTION_LABELS[i]}
              </span>
              <span>{opt}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
