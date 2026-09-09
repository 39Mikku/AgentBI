export interface ProjectModule {
  index: string
  name: 'Studio' | 'Live' | 'Test' | 'Playground' | 'Toolbox'
  description: string
  detail: string
  to: string
  accent: string
}

export interface ProjectLink {
  label: string
  href: string
  external: boolean
}

export interface ProjectAction {
  label: string
  to: string
}

export const PROJECT_AUTHOR = '骑士'

export const PROJECT_MODULES: readonly ProjectModule[] = [
  {
    index: '01',
    name: 'Studio',
    description: '完整上下文、助手、工具与多模态工作台',
    detail: '把对话、记忆、检索、附件与代理能力组织在同一条时间线上。',
    to: '/chat',
    accent: '#ccff24',
  },
  {
    index: '02',
    name: 'Live',
    description: '实时语音、角色与流式转写空间',
    detail: '让声音、字幕、角色记忆与可打断的实时模型自然地待在一起。',
    to: '/live',
    accent: '#80f4db',
  },
  {
    index: '03',
    name: 'Test',
    description: '知识测试与趣味测试实验室',
    detail: '从结构化出题、连续作答到模型分析，保留每一次测试结果。',
    to: '/test',
    accent: '#ff775e',
  },
  {
    index: '04',
    name: 'Playground',
    description: '角色、世界书与长篇叙事空间',
    detail: '把角色卡、模块化提示词、世界书、状态与长会话精炼收进一条沉浸式故事线。',
    to: '/playground',
    accent: '#d7ff3f',
  },
  {
    index: 'U1',
    name: 'Toolbox',
    description: '即开即用的本地小型工作台',
    detail: '收纳语音、表情包、百科归档和文件处理等不必对话的小工具。',
    to: '/toolbox',
    accent: '#b8a8ff',
  },
]

export const PROJECT_LINKS: readonly ProjectLink[] = [
  { label: '官网', href: 'https://agentbi.39miku.tech/', external: true },
  { label: 'GitHub', href: 'https://github.com/39Mikku/AgentBI', external: true },
]

export function getNotFoundPrimaryAction(): ProjectAction {
  return { label: '返回工作台', to: '/' }
}
