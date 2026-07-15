const path = require('path')

const musicApi = require('@neteasecloudmusicapienhanced/api')

async function start() {
  const packageRoot = path.dirname(
    require.resolve('@neteasecloudmusicapienhanced/api/package.json'),
  )
  const moduleDefinitions = await musicApi.getModulesDefinitions(
    path.join(packageRoot, 'module'),
  )
  moduleDefinitions.push({
    identifier: 'agentbi_health',
    route: '/health',
    module: async () => ({
      status: 200,
      body: { status: 'ok' },
    }),
  })

  await musicApi.serveNcmApi({
    port: Number(process.env.NCM_API_PORT || 3300),
    host: '127.0.0.1',
    checkVersion: false,
    moduleDefs: moduleDefinitions,
  })
}

start().catch((error) => {
  console.error(`music api failed: ${error?.message || 'unknown error'}`)
  process.exitCode = 1
})
