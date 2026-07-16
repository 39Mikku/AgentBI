export function authenticatedDestination(redirect: unknown): string {
  if (
    typeof redirect === 'string' &&
    redirect.startsWith('/') &&
    !redirect.startsWith('//') &&
    redirect !== '/' &&
    redirect !== '/login'
  ) return redirect
  return '/home'
}
