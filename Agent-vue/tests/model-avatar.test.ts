import assert from 'node:assert/strict'
import { resolveModelBrand } from '../src/utils/model-avatar'

assert.equal(resolveModelBrand('gpt-4.1').name, 'OpenAI')
assert.equal(resolveModelBrand('claude-sonnet-4').name, 'Anthropic')
assert.equal(resolveModelBrand('gemini-2.5-pro').name, 'Google Gemini')
assert.equal(resolveModelBrand('DeepSeek-V3').name, 'DeepSeek')
assert.equal(resolveModelBrand('Qwen3-235B').name, 'Alibaba Cloud')
assert.equal(resolveModelBrand('mistral-large').name, 'Mistral AI')
assert.equal(resolveModelBrand('llama-4-scout').name, 'Meta')
assert.equal(resolveModelBrand('xai-grok-3').name, 'AI')
