import type { CodingLanguage } from '@/api/coding'

/**
 * Editor settings for the Utporul coding workspace.
 *
 * `VITE_CODING_EDITOR=textarea` turns Monaco off at build time and keeps the
 * plain textarea. Anything else (including unset) uses Monaco. The flag is
 * read at build time because the frontend is baked into its image.
 */
export type CodingEditorMode = 'monaco' | 'textarea'

export function codingEditorMode(raw: string | undefined = import.meta.env.VITE_CODING_EDITOR): CodingEditorMode {
  return raw === 'textarea' ? 'textarea' : 'monaco'
}

/** Monaco language id for each judge language. */
export const MONACO_LANGUAGE: Record<CodingLanguage, string> = {
  python: 'python',
  javascript: 'javascript',
  typescript: 'typescript',
  java: 'java',
  cpp: 'cpp',
  c: 'c',
}

/** Filename the judge uses for each language. Error messages refer to it. */
export const SOURCE_FILENAME: Record<CodingLanguage, string> = {
  python: 'script.py',
  javascript: 'script.js',
  typescript: 'script.ts',
  java: 'Main.java',
  cpp: 'main.cpp',
  c: 'main.c',
}

/** Keywords offered as completions, on top of identifiers found in the starter code. */
export const LANGUAGE_KEYWORDS: Record<CodingLanguage, string[]> = {
  python: ['def', 'class', 'return', 'import', 'from', 'for', 'while', 'if', 'elif', 'else', 'print', 'input', 'range', 'len', 'list', 'dict', 'set', 'int', 'str', 'float', 'sorted', 'enumerate', 'zip', 'map', 'filter', 'True', 'False', 'None'],
  javascript: ['function', 'const', 'let', 'var', 'return', 'if', 'else', 'for', 'while', 'class', 'console', 'log', 'require', 'process', 'Math', 'Array', 'Object', 'Number', 'String', 'JSON', 'Map', 'Set'],
  typescript: ['function', 'const', 'let', 'return', 'interface', 'type', 'number', 'string', 'boolean', 'console', 'log', 'Array', 'Map', 'Set', 'Math', 'JSON'],
  java: ['public', 'class', 'static', 'void', 'int', 'long', 'double', 'String', 'System', 'out', 'println', 'return', 'new', 'for', 'while', 'if', 'else', 'import'],
  cpp: ['#include', 'int', 'long', 'double', 'std', 'cout', 'cin', 'endl', 'vector', 'string', 'return', 'for', 'while', 'if', 'else', 'using', 'namespace'],
  c: ['#include', 'int', 'long', 'double', 'char', 'printf', 'scanf', 'return', 'for', 'while', 'if', 'else', 'void', 'main'],
}

/** Words to suggest from the starter code: identifiers, longer than two characters, unique. */
export function identifiersFrom(source: string): string[] {
  const words = source.match(/[A-Za-z_][A-Za-z0-9_]{2,}/g) ?? []
  return Array.from(new Set(words))
}
