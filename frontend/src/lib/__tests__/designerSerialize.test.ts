import { describe, it, expect } from 'vitest'
import {
  toServerElement,
  toServerElements,
  fromServerElement,
  fromServerElements,
  serverElementsEqual,
} from '../designerSerialize'
import type { DesignerElement } from '../certificateDesignerTypes'

describe('designerSerialize', () => {
  it('toServerElement strips the client-only id field', () => {
    const el: DesignerElement = {
      id: 'el-1',
      type: 'text',
      x: 10,
      y: 20,
      width: 100,
      height: 40,
      z_index: 0,
      content: 'Hello',
    }
    const server = toServerElement(el)
    expect(server).not.toHaveProperty('id')
    expect(server.type).toBe('text')
    expect(server.content).toBe('Hello')
  })

  it('toServerElement drops undefined fields', () => {
    const el: DesignerElement = {
      id: 'el-1',
      type: 'rect',
      x: 0,
      y: 0,
      width: 10,
      height: 10,
      z_index: 0,
      rotation: undefined,
    }
    const server = toServerElement(el)
    expect('rotation' in server).toBe(false)
  })

  it('fromServerElement assigns a fresh client-only id', () => {
    const raw = { type: 'text', x: 1, y: 2, width: 3, height: 4, z_index: 0, content: 'hi' }
    const a = fromServerElement(raw)
    const b = fromServerElement(raw)
    expect(a.id).toBeTruthy()
    expect(b.id).toBeTruthy()
    expect(a.id).not.toBe(b.id) // each call gets a distinct id
    expect(a.type).toBe('text')
    expect(a.content).toBe('hi')
  })

  it('preserves unknown/extra fields through a server round-trip', () => {
    const raw = {
      type: 'rect',
      x: 5,
      y: 5,
      width: 50,
      height: 50,
      z_index: 1,
      background_color: '#ff0000',
      border: { width: 2, style: 'solid', color: '#000000' },
    }
    const el = fromServerElement(raw)
    const backToServer = toServerElement(el)
    expect(backToServer).toEqual(raw)
  })

  it('list round-trip (server -> client -> server) is content-stable', () => {
    const rawList = [
      { type: 'student_name', x: 0, y: 0, width: 300, height: 40, z_index: 0, font_size: 24 },
      { type: 'qr_code', x: 400, y: 400, width: 120, height: 120, z_index: 5 },
      {
        type: 'image',
        x: 10,
        y: 10,
        width: 200,
        height: 100,
        z_index: 2,
        image_url: '/uploads/certificates/logo.png',
      },
    ]
    const elements = fromServerElements(rawList)
    expect(elements).toHaveLength(3)
    elements.forEach((el) => expect(el.id).toBeTruthy())

    const backToServer = toServerElements(elements)
    expect(serverElementsEqual(backToServer, rawList as any)).toBe(true)
  })

  it('serverElementsEqual detects a real difference', () => {
    const a = [{ type: 'text', x: 0, y: 0, width: 10, height: 10, z_index: 0 }]
    const b = [{ type: 'text', x: 1, y: 0, width: 10, height: 10, z_index: 0 }]
    expect(serverElementsEqual(a as any, b as any)).toBe(false)
  })

  it('serverElementsEqual detects a length mismatch', () => {
    const a = [{ type: 'text', x: 0, y: 0, width: 10, height: 10, z_index: 0 }]
    const b: typeof a = []
    expect(serverElementsEqual(a as any, b as any)).toBe(false)
  })

  it('fromServerElements handles an empty/undefined list', () => {
    expect(fromServerElements([])).toEqual([])
    // @ts-expect-error - defensive runtime check
    expect(fromServerElements(undefined)).toEqual([])
  })
})
