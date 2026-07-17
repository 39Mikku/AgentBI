import { describe, expect, it } from 'vitest'

import { getLoginStepPresentation } from './login-presentation'

describe('getLoginStepPresentation', () => {
  it('returns email-entry copy for step one', () => {
    expect(getLoginStepPresentation(1)).toMatchObject({
      index: '01 / 02',
      title: '连接你的工作台',
      actionLabel: '发送验证码',
    })
  })

  it('returns verification copy for step two', () => {
    expect(getLoginStepPresentation(2)).toMatchObject({
      index: '02 / 02',
      title: '完成身份确认',
      actionLabel: '进入 AgentBI',
    })
  })
})
