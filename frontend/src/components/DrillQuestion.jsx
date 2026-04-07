import { useState } from 'react'
import MathText from './MathText.jsx'
import { TEST_IDS } from '../testing/testIds.ts'

const OPTION_LABELS = ['A', 'B', 'C', 'D', 'E']

const TABLE_SENTINEL = '[[TABLE]]'

/** Two-way contingency table for T-9P-03 */
function TwoWayTable({ params }) {
  const { table, row_labels: rows, col_labels: cols } = params
  if (!table || !rows || !cols) return null
  const total = table.a1b1 + table.a1b2 + table.a2b1 + table.a2b2
  return (
    <div className="overflow-x-auto my-3">
      <table className="border-collapse text-sm text-center mx-auto">
        <thead>
          <tr>
            <th className="border border-slate-300 px-3 py-1 bg-slate-100" />
            {cols.map(c => (
              <th key={c} className="border border-slate-300 px-4 py-1 bg-slate-100 font-semibold text-slate-700">{c}</th>
            ))}
            <th className="border border-slate-300 px-4 py-1 bg-slate-100 font-semibold text-slate-700">Total</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="border border-slate-300 px-3 py-1 bg-slate-50 font-semibold text-slate-700">{rows[0]}</td>
            <td className="border border-slate-300 px-4 py-1">{table.a1b1}</td>
            <td className="border border-slate-300 px-4 py-1">{table.a1b2}</td>
            <td className="border border-slate-300 px-4 py-1 text-slate-500">{table.a1b1 + table.a1b2}</td>
          </tr>
          <tr>
            <td className="border border-slate-300 px-3 py-1 bg-slate-50 font-semibold text-slate-700">{rows[1]}</td>
            <td className="border border-slate-300 px-4 py-1">{table.a2b1}</td>
            <td className="border border-slate-300 px-4 py-1">{table.a2b2}</td>
            <td className="border border-slate-300 px-4 py-1 text-slate-500">{table.a2b1 + table.a2b2}</td>
          </tr>
          <tr>
            <td className="border border-slate-300 px-3 py-1 bg-slate-100 font-semibold text-slate-700">Total</td>
            <td className="border border-slate-300 px-4 py-1 bg-slate-50 text-slate-600">{table.a1b1 + table.a2b1}</td>
            <td className="border border-slate-300 px-4 py-1 bg-slate-50 text-slate-600">{table.a1b2 + table.a2b2}</td>
            <td className="border border-slate-300 px-4 py-1 bg-slate-100 font-semibold text-slate-700">{total}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

/** Frequency table for T-8ST-01 */
function FrequencyTable({ params }) {
  const { values, frequencies } = params
  if (!Array.isArray(values) || !Array.isArray(frequencies)) return null
  return (
    <div className="overflow-x-auto my-3">
      <table className="border-collapse text-sm text-center mx-auto">
        <thead>
          <tr>
            <th className="border border-slate-300 px-4 py-1 bg-slate-100 font-semibold text-slate-700">Value</th>
            {values.map((v, i) => (
              <th key={i} className="border border-slate-300 px-4 py-1 bg-slate-100 font-semibold text-slate-700">{v}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="border border-slate-300 px-4 py-1 bg-slate-50 font-semibold text-slate-700">Frequency</td>
            {frequencies.map((f, i) => (
              <td key={i} className="border border-slate-300 px-4 py-1">{f}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

/** Render [[TABLE]] sentinel as the appropriate structured table */
function StructuredTable({ params }) {
  if (params?.table && params?.row_labels) return <TwoWayTable params={params} />
  if (Array.isArray(params?.values) && Array.isArray(params?.frequencies)) return <FrequencyTable params={params} />
  return null
}

/**
 * Split question_text on [[TABLE]] sentinel and return [before, after] parts.
 * Returns null if no sentinel present.
 */
function splitOnTableSentinel(text) {
  const idx = text.indexOf(TABLE_SENTINEL)
  if (idx === -1) return null
  return [text.slice(0, idx).trim(), text.slice(idx + TABLE_SENTINEL.length).trim()]
}

// NOTE: Parent uses key={question_id} so this component remounts on question change.
// Initial state from selectedAnswer is set via useState initialiser (no useEffect needed).
export default function DrillQuestion({ question, questionNumber, totalQuestions, selectedAnswer, onSelect }) {
  const isMultiSelect = question.question_type === 'multi_select'

  // Brief flash effect when answer changes on revisit
  const [flash, setFlash] = useState(false)

  // Multi-select local state — initialised from selectedAnswer if revisiting
  const [checkedSet, setCheckedSet] = useState(
    () => new Set(selectedAnswer?.selectedIndices ?? [])
  )

  // For single-select, derive from selectedAnswer prop
  const singleSelected = selectedAnswer?.selectedIndex ?? null

  function handleSingleSelect(index) {
    // Flash if changing an existing answer
    const isChange = singleSelected !== null && singleSelected !== index
    if (isChange) {
      setFlash(true)
      setTimeout(() => setFlash(false), 200)
    }
    // Auto-advance on first answer; stay on revisit change
    onSelect(index, { advance: !isChange && singleSelected === null })
  }

  function handleCheckboxToggle(index) {
    setCheckedSet(prev => {
      const next = new Set(prev)
      next.has(index) ? next.delete(index) : next.add(index)
      return next
    })
  }

  function handleConfirm() {
    if (checkedSet.size === 0) return
    const isChange = !!selectedAnswer?.selectedIndices
    if (isChange) {
      setFlash(true)
      setTimeout(() => setFlash(false), 200)
    }
    onSelect([...checkedSet].sort((a, b) => a - b), { advance: !isChange })
  }

  return (
    <div className={`bg-white rounded-2xl shadow-sm border border-slate-200 p-6 transition-opacity ${flash ? 'opacity-60' : 'opacity-100'}`}>
      <p className="text-xs font-medium text-indigo-500 uppercase tracking-wide mb-3">
        Question {questionNumber} of {totalQuestions}
      </p>

      {(() => {
        const parts = splitOnTableSentinel(question.question_text)
        if (parts) {
          const [before, after] = parts
          return (
            <>
              {before && (
                <MathText className="text-lg font-medium text-slate-800 leading-relaxed block">
                  {before}
                </MathText>
              )}
              <StructuredTable params={question.params} />
              {after && (
                <MathText className="text-lg font-medium text-slate-800 mb-6 leading-relaxed block">
                  {after}
                </MathText>
              )}
            </>
          )
        }
        return (
          <MathText className="text-lg font-medium text-slate-800 mb-6 leading-relaxed block">
            {question.question_text}
          </MathText>
        )
      })()}

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
                  'w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-colors cursor-pointer',
                  isChecked
                    ? 'bg-indigo-50 border-indigo-400 text-slate-800'
                    : 'bg-white border-slate-200 text-slate-800 hover:border-indigo-300 hover:bg-slate-50',
                ].join(' ')}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => handleCheckboxToggle(i)}
                  className="w-4 h-4 accent-indigo-600 flex-shrink-0"
                />
                <span className={[
                  'flex-shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold',
                  isChecked ? 'border-indigo-400 text-indigo-600' : 'border-slate-300 text-slate-500',
                ].join(' ')}>
                  {OPTION_LABELS[i]}
                </span>
                <MathText>{opt}</MathText>
              </label>
            )
          }

          // Single-select
          const isSelected = singleSelected === i
          return (
            <button
              key={i}
              data-testid={TEST_IDS.drill.optionBtn(i)}
              onClick={() => handleSingleSelect(i)}
              className={[
                'w-full text-left px-4 py-3 rounded-xl border-2 transition-colors flex items-center gap-3 cursor-pointer',
                isSelected
                  ? 'bg-indigo-600 border-indigo-600 text-white'
                  : 'bg-white border-slate-200 text-slate-800 hover:border-indigo-300 hover:bg-slate-50',
              ].join(' ')}
            >
              <span className={[
                'flex-shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold',
                isSelected ? 'border-white text-white' : 'border-slate-300 text-slate-500',
              ].join(' ')}>
                {OPTION_LABELS[i]}
              </span>
              <MathText>{opt}</MathText>
            </button>
          )
        })}
      </div>

      {isMultiSelect && (
        <button
          data-testid={TEST_IDS.drill.confirmBtn}
          onClick={handleConfirm}
          disabled={checkedSet.size === 0}
          className="mt-4 w-full bg-indigo-600 text-white py-3 rounded-xl font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-indigo-700 transition-colors"
        >
          {selectedAnswer?.selectedIndices ? 'Update Selection' : 'Confirm Selection'}
        </button>
      )}
    </div>
  )
}
