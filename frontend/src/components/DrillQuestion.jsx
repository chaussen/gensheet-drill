import { useState } from 'react'
import { InlineMath } from 'react-katex'
import MathText from './MathText.jsx'
import { toLatex } from '../utils/math.js'
import { TEST_IDS } from '../testing/testIds.ts'

const OPTION_LABELS = ['A', 'B', 'C', 'D', 'E']

export default function DrillQuestion({ question, questionNumber, totalQuestions, onAnswer }) {
  const isMultiSelect = question.question_type === 'multi_select'

  // Single-select state
  const [selected, setSelected] = useState(null)
  const [locked, setLocked]     = useState(false)

  // Multi-select state
  const [checkedSet, setCheckedSet] = useState(new Set())
  const [confirmed, setConfirmed]   = useState(false)

  function handleSingleSelect(index) {
    if (locked) return
    setSelected(index)
    setLocked(true)
    setTimeout(() => onAnswer(index), 300)
  }

  function handleCheckboxToggle(index) {
    if (confirmed) return
    setCheckedSet(prev => {
      const next = new Set(prev)
      next.has(index) ? next.delete(index) : next.add(index)
      return next
    })
  }

  function handleConfirm() {
    if (confirmed || checkedSet.size === 0) return
    setConfirmed(true)
    onAnswer([...checkedSet].sort((a, b) => a - b))
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
      <p className="text-xs font-medium text-indigo-500 uppercase tracking-wide mb-3">
        Question {questionNumber} of {totalQuestions}
      </p>

      <MathText
        text={question.question_text}
        latex={!!question.latex_notation}
        className="text-lg font-medium text-slate-800 mb-6 leading-relaxed block"
      />

      {isMultiSelect && (
        <p data-testid={TEST_IDS.drill.multiWarning} className="text-xs font-medium text-amber-600 uppercase tracking-wide mb-3">
          Select all that apply
        </p>
      )}

      <div className="space-y-3">
        {question.options.map((opt, i) => {
          if (isMultiSelect) {
            const isChecked = checkedSet.has(i)
            return (
              <label
                key={i}
                data-testid={TEST_IDS.drill.optionLabel(i)}
                className={[
                  'w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-colors',
                  isChecked
                    ? 'bg-indigo-50 border-indigo-400 text-slate-800'
                    : 'bg-white border-slate-200 text-slate-800 hover:border-indigo-300 hover:bg-slate-50',
                  confirmed ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer',
                ].join(' ')}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => handleCheckboxToggle(i)}
                  disabled={confirmed}
                  className="w-4 h-4 accent-indigo-600 flex-shrink-0"
                />
                <span className={[
                  'flex-shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold',
                  isChecked ? 'border-indigo-400 text-indigo-600' : 'border-slate-300 text-slate-500',
                ].join(' ')}>
                  {OPTION_LABELS[i]}
                </span>
                {question.latex_notation
                  ? <InlineMath math={toLatex(opt)} renderError={() => <span>{opt}</span>} />
                  : <span>{opt}</span>}
              </label>
            )
          }

          // Single-select (original behaviour)
          const isSelected = selected === i
          return (
            <button
              key={i}
              data-testid={TEST_IDS.drill.optionBtn(i)}
              onClick={() => handleSingleSelect(i)}
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
              {question.latex_notation
                ? <InlineMath math={toLatex(opt)} renderError={() => <span>{opt}</span>} />
                : <span>{opt}</span>}
            </button>
          )
        })}
      </div>

      {isMultiSelect && (
        <button
          data-testid={TEST_IDS.drill.confirmBtn}
          onClick={handleConfirm}
          disabled={checkedSet.size === 0 || confirmed}
          className="mt-4 w-full bg-indigo-600 text-white py-3 rounded-xl font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-indigo-700 transition-colors"
        >
          Confirm Selection
        </button>
      )}
    </div>
  )
}
