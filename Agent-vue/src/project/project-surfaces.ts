export interface ProjectModule {
  index: string
  name: 'Studio' | 'Live' | 'Test' | 'Toolbox'
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

export const AUTHOR_PARAGRAPHS = [
  '一名把“这功能要是能直接用就好了”当成开发需求的普通大学生。',
  '平时折腾大模型、Agent、AIGC，以及各种不一定有用、但做出来会很开心的小工具。作为一个长期重度使用 AI 产品的人，也经常被分散的功能、割裂的工作流和不顺手的交互折磨，于是干脆做了这个本地 Web 工作台。',
  '这里集成了对话、知识库、多模态处理、内容生成、网页搜索和一些日常工具。它不是什么宏大的商业项目，也暂时没有严肃的开源计划，只是一个按照个人需求不断生长的私人工作空间。',
  '哪里用着不爽，就改哪里；缺什么功能，就再塞一个进去。',
  'Built for myself, expanded by curiosity.',
] as const

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
    name: 'Toolbox',
    description: '即开即用的本地小型工作台',
    detail: '收纳语音、表情包、百科归档和文件处理等不必对话的小工具。',
    to: '/toolbox',
    accent: '#b8a8ff',
  },
]

export const PROJECT_LINKS: readonly ProjectLink[] = [
  { label: 'About', href: '/about', external: false },
  { label: 'GitHub', href: 'https://github.com/39Mikku/AgentBI', external: true },
  { label: 'elysiareal.me', href: 'http://elysiareal.me/', external: true },
]

export function getNotFoundPrimaryAction(authenticated: boolean): ProjectAction {
  return authenticated
    ? { label: '返回工作台', to: '/home' }
    : { label: '进入 AgentBI', to: '/login' }
}
