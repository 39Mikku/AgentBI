export interface SettingsResources<P, R> {
  providers: P[]
  routes: R[]
  providerError: string
  routeError: string
}

function errorMessage(reason: unknown) {
  return reason instanceof Error ? reason.message : '未知错误'
}

export async function loadSettingsResources<P, R>(
  loadProviders: () => Promise<P[]>,
  loadRoutes: () => Promise<R[]>,
): Promise<SettingsResources<P, R>> {
  const [providerResult, routeResult] = await Promise.allSettled([loadProviders(), loadRoutes()])
  return {
    providers: providerResult.status === 'fulfilled' ? providerResult.value : [],
    routes: routeResult.status === 'fulfilled' ? routeResult.value : [],
    providerError:
      providerResult.status === 'rejected'
        ? `提供商加载失败：${errorMessage(providerResult.reason)}`
        : '',
    routeError:
      routeResult.status === 'rejected'
        ? `后台模型路由加载失败：${errorMessage(routeResult.reason)}`
        : '',
  }
}
