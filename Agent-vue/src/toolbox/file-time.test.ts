import { describe, expect, it } from 'vitest'

import { fileTimeProgress, requiresDateRange, requiresOutput } from './file-time'


describe('file time workbench state', () => {
  it('requires output only for operations that move files', () => {
    expect(requiresOutput('filename_to_creation')).toBe(true)
    expect(requiresOutput('move_by_creation_range')).toBe(true)
    expect(requiresOutput('creation_from_modified')).toBe(false)
    expect(requiresOutput('modified_from_creation')).toBe(false)
  })

  it('requires dates only for date range moves', () => {
    expect(requiresDateRange('move_by_creation_range')).toBe(true)
    expect(requiresDateRange('filename_to_creation')).toBe(false)
  })

  it('calculates clamped progress', () => {
    expect(fileTimeProgress({ processed_files: 0, total_files: 0 })).toBe(0)
    expect(fileTimeProgress({ processed_files: 2, total_files: 4 })).toBe(50)
    expect(fileTimeProgress({ processed_files: 7, total_files: 4 })).toBe(100)
  })
})

