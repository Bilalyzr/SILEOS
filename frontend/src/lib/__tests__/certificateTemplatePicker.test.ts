/**
 * Review finding I2: instructor designer templates must be reachable from the
 * course editor's certificate picker, merged with the public list and deduped
 * by id.
 */
import { describe, it, expect } from 'vitest'
import {
  canUseDesignerTemplates,
  designerToPickerTemplate,
  mergeTemplateLists,
  type PickerTemplate,
  type DesignerTemplateLike,
} from '../certificateTemplatePicker'

const publicLegacy: PickerTemplate = {
  id: 1,
  name: 'Classic Gold',
  slug: 'classic-gold',
  thumbnail: '/certificate-files/thumbnails/classic-gold.png',
  template_type: 'legacy',
  bg_color: '#FFF8DC',
  title_color: '#8B6B21',
  font: 'Georgia',
}

const publicGlobal: PickerTemplate = {
  id: 7,
  name: 'Global Modern',
  slug: '',
  thumbnail: null,
  template_type: 'builder',
  bg_color: '#ffffff',
}

const ownDesigner: DesignerTemplateLike = {
  id: 42,
  name: 'My Private Design',
  background_color: '#101010',
  orientation: 'landscape',
  thumbnail: '/certificate-files/thumbnails/designer-42.png',
  is_global: false,
  is_own: true,
}

describe('canUseDesignerTemplates', () => {
  it('allows instructors, admins and superadmins', () => {
    expect(canUseDesignerTemplates('instructor')).toBe(true)
    expect(canUseDesignerTemplates('admin')).toBe(true)
    expect(canUseDesignerTemplates('superadmin')).toBe(true)
  })

  it('rejects students and unknown/absent roles', () => {
    expect(canUseDesignerTemplates('student')).toBe(false)
    expect(canUseDesignerTemplates(undefined)).toBe(false)
    expect(canUseDesignerTemplates(null)).toBe(false)
  })
})

describe('mergeTemplateLists', () => {
  it('surfaces an instructor own designer template the public list omits', () => {
    const merged = mergeTemplateLists([publicLegacy], [ownDesigner])

    expect(merged.map(t => t.id)).toEqual([1, 42])
    const own = merged.find(t => t.id === 42)!
    expect(own.name).toBe('My Private Design')
    expect(own.is_designer).toBe(true)
    expect(own.template_type).toBe('builder')
  })

  it('dedupes by id — a global template present in both lists appears once', () => {
    const alsoGlobal: DesignerTemplateLike = {
      id: 7,
      name: 'Global Modern',
      background_color: '#ffffff',
      is_global: true,
      is_own: false,
    }

    const merged = mergeTemplateLists([publicLegacy, publicGlobal], [alsoGlobal, ownDesigner])

    expect(merged.map(t => t.id)).toEqual([1, 7, 42])
    // The public entry wins — it carries the richer display metadata.
    expect(merged.find(t => t.id === 7)!.is_designer).toBeUndefined()
  })

  it('is a no-op on the public list when there are no designer templates', () => {
    expect(mergeTemplateLists([publicLegacy, publicGlobal], [])).toEqual([
      publicLegacy,
      publicGlobal,
    ])
  })

  it('tolerates empty/nullish inputs', () => {
    expect(mergeTemplateLists([], [])).toEqual([])
    expect(mergeTemplateLists(null as never, null as never)).toEqual([])
  })

  it('drops duplicate ids inside a single list', () => {
    const merged = mergeTemplateLists(
      [publicLegacy, { ...publicLegacy, name: 'Duplicate' }],
      [ownDesigner, { ...ownDesigner, name: 'Duplicate designer' }],
    )

    expect(merged.map(t => t.id)).toEqual([1, 42])
    expect(merged[0].name).toBe('Classic Gold')
    expect(merged[1].name).toBe('My Private Design')
  })
})

describe('designerToPickerTemplate', () => {
  it('maps designer fields onto the picker shape', () => {
    const mapped = designerToPickerTemplate(ownDesigner)

    expect(mapped).toMatchObject({
      id: 42,
      name: 'My Private Design',
      bg_color: '#101010',
      orientation: 'landscape',
      thumbnail: '/certificate-files/thumbnails/designer-42.png',
      template_type: 'builder',
      is_designer: true,
      is_own: true,
    })
  })

  it('nulls the thumbnail when the designer row has none', () => {
    const mapped = designerToPickerTemplate({ id: 5, name: 'No thumb' })
    expect(mapped.thumbnail).toBeNull()
  })
})
