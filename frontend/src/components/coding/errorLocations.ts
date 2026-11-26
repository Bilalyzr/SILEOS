import type { CodingLanguage } from '@/api/coding'
import { SOURCE_FILENAME } from './editorConfig'

export interface ErrorLocation {
  line: number
  column: number
  message: string
}

/**
 * Pulls line and column numbers out of judge stderr so the editor can mark them.
 *
 * Covers the message formats the judge's compilers and interpreters use:
 *   Python      File "script.py", line 3
 *   JavaScript  script.js:3
 *   TypeScript  script.ts(3,5): error TS...
 *   C / C++     main.cpp:3:5: error: ...
 *   Java        Main.java:3: error: ...
 * Lines that carry no location are dropped. Stderr from other sources is
 * ignored rather than guessed at.
 */
export function errorLocations(language: CodingLanguage, text: string): ErrorLocation[] {
  const file = escapeRegExp(SOURCE_FILENAME[language])
  const patterns: RegExp[] = [
    new RegExp(`File "${file}", line (\\d+)`),
    new RegExp(`${file}\\((\\d+)(?:,(\\d+))?\\)`),
    new RegExp(`${file}:(\\d+)(?::(\\d+))?`),
  ]
  const found: ErrorLocation[] = []
  for (const rawLine of text.split(/\r?\n/)) {
    for (const pattern of patterns) {
      const match = pattern.exec(rawLine)
      if (!match) continue
      const line = Number(match[1])
      if (!Number.isInteger(line) || line < 1) break
      found.push({
        line,
        column: Math.max(1, Number(match[2] ?? 1)),
        message: rawLine.slice(match.index + match[0].length).replace(/^[\s:,)]+/, '').trim() || rawLine.trim(),
      })
      break
    }
  }
  return found
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
