import { describe, expect, it } from 'vitest'
import { errorLocations } from '../errorLocations'
import { codingEditorMode, identifiersFrom } from '../editorConfig'

describe('errorLocations', () => {
  it('reads a Python traceback line', () => {
    const stderr = 'Traceback (most recent call last):\n  File "script.py", line 3, in <module>\n    print(x)\nNameError: name \'x\' is not defined'
    expect(errorLocations('python', stderr)).toEqual([
      { line: 3, column: 1, message: 'in <module>' },
    ])
  })

  it('reads a JavaScript error location', () => {
    const stderr = 'script.js:2\n  console.log(y)\n          ^\nReferenceError: y is not defined'
    expect(errorLocations('javascript', stderr)[0]).toMatchObject({ line: 2, column: 1 })
  })

  it('reads a TypeScript error with line and column', () => {
    const stderr = "script.ts(1,7): error TS2322: Type 'string' is not assignable to type 'number'."
    expect(errorLocations('typescript', stderr)).toEqual([
      { line: 1, column: 7, message: "error TS2322: Type 'string' is not assignable to type 'number'." },
    ])
  })

  it('reads GCC and Clang style C and C++ errors', () => {
    const stderr = 'main.cpp:4:5: error: expected \';\' before \'}\' token\nmain.cpp:9:1: warning: unused variable'
    expect(errorLocations('cpp', stderr)).toEqual([
      { line: 4, column: 5, message: "error: expected ';' before '}' token" },
      { line: 9, column: 1, message: 'warning: unused variable' },
    ])
  })

  it('reads a javac error for Main.java', () => {
    const stderr = "Main.java:5: error: ';' expected"
    expect(errorLocations('java', stderr)[0]).toMatchObject({ line: 5, column: 1 })
  })

  it('ignores lines for a different file name', () => {
    expect(errorLocations('python', 'other.py:3: boom')).toEqual([])
  })

  it('ignores empty and location-free stderr', () => {
    expect(errorLocations('c', '')).toEqual([])
    expect(errorLocations('c', 'Killed')).toEqual([])
  })

  it('rejects line 0', () => {
    expect(errorLocations('python', 'File "script.py", line 0')).toEqual([])
  })
})

describe('codingEditorMode', () => {
  it('uses Monaco by default', () => {
    expect(codingEditorMode(undefined)).toBe('monaco')
    expect(codingEditorMode('')).toBe('monaco')
  })

  it('switches to the textarea only when asked', () => {
    expect(codingEditorMode('textarea')).toBe('textarea')
    expect(codingEditorMode('TEXTAREA')).toBe('monaco')
  })
})

describe('identifiersFrom', () => {
  it('returns unique identifiers of three or more characters', () => {
    expect(identifiersFrom('total = total + count\nx = 1')).toEqual(['total', 'count'])
  })
})
