export interface LoginStepPresentation {
  index: string
  eyebrow: string
  title: string
  description: string
  actionLabel: string
}

const presentations: Record<1 | 2, LoginStepPresentation> = {
  1: {
    index: '01 / 02',
    eyebrow: 'IDENTITY CHANNEL',
    title: '连接你的工作台',
    description: '输入邮箱，我们会发送一枚仅本次登录有效的验证码。',
    actionLabel: '发送验证码',
  },
  2: {
    index: '02 / 02',
    eyebrow: 'VERIFY ACCESS',
    title: '完成身份确认',
    description: '输入邮件中的验证码，继续进入你的 AgentBI 工作空间。',
    actionLabel: '进入 AgentBI',
  },
}

export function getLoginStepPresentation(step: 1 | 2): LoginStepPresentation {
  return presentations[step]
}
