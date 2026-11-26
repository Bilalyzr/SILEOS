import { useEffect, useRef } from 'react'
import * as monaco from 'monaco-editor/editor/editor.api.js'
import type * as MonacoTypes from 'monaco-editor'
import editorWorker from 'monaco-editor/editor/editor.worker.js?worker'
import tsWorker from 'monaco-editor/language/typescript/ts.worker.js?worker'
// Register only the six judge languages (plus JavaScript, which the TypeScript
// contribution provides) to keep the editor bundle small.
import 'monaco-editor/languages/definitions/python/register.js'
import 'monaco-editor/languages/definitions/java/register.js'
import 'monaco-editor/languages/definitions/cpp/register.js'
import 'monaco-editor/language/typescript/monaco.contribution.js'
import type { CodingLanguage } from '@/api/coding'
import { LANGUAGE_KEYWORDS, MONACO_LANGUAGE, identifiersFrom } from './editorConfig'
import type { ErrorLocation } from './errorLocations'

// Monaco runs its language services in workers. Only the TypeScript/JavaScript
// service needs its own worker; everything else shares the generic one.
const globalScope = self as unknown as { MonacoEnvironment?: MonacoTypes.Environment }
globalScope.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    return label === 'typescript' || label === 'javascript' ? new tsWorker() : new editorWorker()
  },
}

interface CodeEditorProps {
  language: CodingLanguage
  value: string
  starterCode: string
  onChange: (value: string) => void
  errors: ErrorLocation[]
  label: string
}

/**
 * Monaco editor for the coding workspace. Loaded lazily by the workspace page,
 * so the editor bundle only downloads on this page. Autocomplete offers the
 * language's keywords plus identifiers from the starter code. Errors from the
 * last run appear as markers on the lines they point to.
 */
export default function CodeEditor({ language, value, starterCode, onChange, errors, label }: CodeEditorProps) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const editorRef = useRef<MonacoTypes.editor.IStandaloneCodeEditor | null>(null)
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  useEffect(() => {
    if (!hostRef.current) return
    const editor = monaco.editor.create(hostRef.current, {
      value,
      language: MONACO_LANGUAGE[language],
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: false },
      fontSize: 14,
      lineHeight: 22,
      tabSize: 4,
      scrollBeyondLastLine: false,
      wordWrap: 'on',
      // Enter starts a new line. It should not accept a suggestion, or a learner
      // typing a line quickly can change a word they did not mean to.
      acceptSuggestionOnEnter: 'off',
      ariaLabel: label,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
    })
    editorRef.current = editor
    const changeSub = editor.onDidChangeModelContent(() => onChangeRef.current(editor.getValue()))
    return () => {
      changeSub.dispose()
      editor.dispose()
      editorRef.current = null
    }
    // Mount once. Language and value changes are applied to the live model below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const editor = editorRef.current
    const model = editor?.getModel()
    if (!editor || !model) return
    monaco.editor.setModelLanguage(model, MONACO_LANGUAGE[language])
  }, [language])

  useEffect(() => {
    const editor = editorRef.current
    if (!editor || editor.getValue() === value) return
    editor.setValue(value)
  }, [value])

  useEffect(() => {
    const model = editorRef.current?.getModel()
    if (!model) return
    monaco.editor.setModelMarkers(
      model,
      'judge',
      errors.map((error) => ({
        severity: monaco.MarkerSeverity.Error,
        message: error.message,
        startLineNumber: error.line,
        startColumn: error.column,
        endLineNumber: error.line,
        endColumn: model.getLineMaxColumn(Math.min(error.line, model.getLineCount())),
      })),
    )
  }, [errors])

  useEffect(() => {
    const words = identifiersFrom(starterCode)
    const keywords = LANGUAGE_KEYWORDS[language]
    const registration = monaco.languages.registerCompletionItemProvider(MONACO_LANGUAGE[language], {
      provideCompletionItems(model, position) {
        const word = model.getWordUntilPosition(position)
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        }
        const suggestions = [...new Set([...keywords, ...words])].map((text) => ({
          label: text,
          kind: keywords.includes(text) ? monaco.languages.CompletionItemKind.Keyword : monaco.languages.CompletionItemKind.Variable,
          insertText: text,
          range,
        }))
        return { suggestions }
      },
    })
    return () => registration.dispose()
  }, [language, starterCode])

  return <div ref={hostRef} className="min-h-[430px] flex-1 overflow-hidden rounded-xl border border-white/10 focus-within:border-violet-500" />
}
