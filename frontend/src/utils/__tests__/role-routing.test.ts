import { describe, expect, it } from 'vitest'
import { roleHomePath, roleSatisfies } from '../role-routing'

describe('route role hierarchy', () => {
  it('keeps superadmin-only routes exclusive', () => {
    expect(roleSatisfies('admin', 'superadmin')).toBe(false)
    expect(roleSatisfies('superadmin', 'superadmin')).toBe(true)
  })

  it('lets superadmins inherit only the admin control plane', () => {
    expect(roleSatisfies('superadmin', 'admin')).toBe(true)
    expect(roleSatisfies('superadmin', 'student')).toBe(false)
    expect(roleSatisfies('superadmin', 'company')).toBe(false)
  })

  it('keeps audited view-as roles out of the admin shortcut', () => {
    expect(roleSatisfies('admin', 'instructor')).toBe(true)
    expect(roleSatisfies('admin', 'student')).toBe(false)
    expect(roleSatisfies('admin', 'company')).toBe(false)
    expect(roleSatisfies('admin', 'spoc')).toBe(false)
  })

  it('makes the consolidated control center the admin home', () => {
    expect(roleHomePath('admin')).toBe('/admin/operations')
    expect(roleHomePath('superadmin')).toBe('/superadmin/dashboard')
  })
})
