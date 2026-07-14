import {
  siAlibabacloud,
  siAnthropic,
  siDeepseek,
  siGooglegemini,
  siMeta,
  siMistralai,
  type SimpleIcon,
} from 'simple-icons'

export type ModelBrand = {
  name: string
  icon?: SimpleIcon
  accent: string
  fallback: string
}

const generic: ModelBrand = { name: 'AI', accent: '#111111', fallback: 'AI' }

export function resolveModelBrand(model?: string | null): ModelBrand {
  const value = (model || '').toLowerCase()
  if (/gpt|openai|^o[1-9]|chatgpt/.test(value)) return { name: 'OpenAI', accent: '#111111', fallback: 'OA' }
  if (/claude|anthropic/.test(value)) return { name: 'Anthropic', icon: siAnthropic, accent: '#d97757', fallback: 'AN' }
  if (/gemini|google/.test(value)) return { name: 'Google Gemini', icon: siGooglegemini, accent: '#4285f4', fallback: 'GM' }
  if (/deepseek/.test(value)) return { name: 'DeepSeek', icon: siDeepseek, accent: '#4d6bfe', fallback: 'DS' }
  if (/qwen|tongyi|alibaba/.test(value)) return { name: 'Alibaba Cloud', icon: siAlibabacloud, accent: '#ff6a00', fallback: 'QW' }
  if (/mistral/.test(value)) return { name: 'Mistral AI', icon: siMistralai, accent: '#ff7000', fallback: 'MI' }
  if (/llama|meta/.test(value)) return { name: 'Meta', icon: siMeta, accent: '#0866ff', fallback: 'ME' }
  return generic
}
