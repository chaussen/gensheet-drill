/**
 * Convert plain-text math symbols to LaTeX commands.
 * Applied to math tokens before passing to KaTeX.
 */
export function toLatex(text) {
  return String(text)
    .replace(/√\(([^)]+)\)/g, '\\sqrt{$1}')        // √(expr) → \sqrt{expr}
    .replace(/√(\d+(?:\.\d+)?)/g, '\\sqrt{$1}')    // √N → \sqrt{N}
    .replace(/∛\(([^)]+)\)/g, '\\sqrt[3]{$1}')     // ∛(expr) → \sqrt[3]{expr}
    .replace(/∛(\d+(?:\.\d+)?)/g, '\\sqrt[3]{$1}') // ∛N → \sqrt[3]{N}
    .replace(/(\d)\^(\d+)/g, '$1^{$2}')             // N^M → N^{M}
    .replace(/([a-z])\^(\d+)/g, '$1^{$2}')          // x^M → x^{M}
    .replace(/(\d)[²]/g, '$1^{2}')                  // N² → N^{2}
    .replace(/(\d)[³]/g, '$1^{3}')                  // N³ → N^{3}
    .replace(/(\d)[⁴]/g, '$1^{4}')                  // N⁴ → N^{4}
    .replace(/(\d+)\/(\d+)/g, '\\frac{$1}{$2}')    // N/M → \frac{N}{M}
    .replace(/×/g, '\\times')                        // × → \times
    .replace(/÷/g, '\\div')                          // ÷ → \div
}
