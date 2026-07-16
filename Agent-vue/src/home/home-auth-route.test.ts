import { describe, expect, it } from 'vitest'
import { authenticatedDestination } from './home-auth-route'

describe('authenticated home destination', () => {
  it('returns a safe explicit redirect', () => {
    expect(authenticatedDestination('/attachments?source=home')).toBe('/attachments?source=home')
  })

  it('uses the authenticated home for absent or unsafe redirects', () => {
    expect(authenticatedDestination(undefined)).toBe('/home')
    expect(authenticatedDestination('https://example.com')).toBe('/home')
    expect(authenticatedDestination('//example.com')).toBe('/home')
    expect(authenticatedDestination('/login')).toBe('/home')
    expect(authenticatedDestination('/')).toBe('/home')
  })
})
