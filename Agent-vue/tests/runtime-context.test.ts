import assert from 'node:assert/strict'
import { createRuntimeContext } from '../src/utils/runtime-context'

assert.deepEqual(
  createRuntimeContext('Elysi', 'zh-CN', 'Asia/Shanghai'),
  { userName: 'Elysi', locale: 'zh-CN', timezone: 'Asia/Shanghai' },
)
