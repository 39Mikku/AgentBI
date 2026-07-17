<template>
  <div class="brand-loader" role="status" aria-live="polite" aria-label="AgentBI 正在加载">
    <div class="brand-loader__mark" aria-hidden="true">
      <svg viewBox="0 0 256 256">
        <path class="stem" d="M24 220 116 32v140l-36 48H24Z" />
        <path class="cells" d="M136 38h57c24 0 43 18 43 41s-19 41-43 41h-57V38Zm0 100h57c24 0 43 18 43 41s-19 41-43 41h-57v-82Z" />
      </svg>
      <i></i>
    </div>
    <span>AGENTBI / LOADING WORKSPACE</span>
  </div>
</template>

<style scoped>
.brand-loader{position:fixed;z-index:9999;inset:0;display:grid;place-content:center;justify-items:center;background:#11110f;color:#efede6}.brand-loader::before{content:'';position:absolute;inset:0;opacity:.22;background-image:linear-gradient(#efede610 1px,transparent 1px),linear-gradient(90deg,#efede610 1px,transparent 1px);background-size:34px 34px}.brand-loader__mark{position:relative;width:86px;height:86px}.brand-loader svg{position:relative;z-index:1;width:100%;height:100%;overflow:visible}.stem{fill:#efede6;animation:brand-stem .72s cubic-bezier(.2,.8,.2,1) both}.cells{fill:#d9ff36;animation:brand-cells .72s .08s cubic-bezier(.2,.8,.2,1) both}.brand-loader__mark i{position:absolute;left:0;right:0;bottom:-17px;height:1px;overflow:hidden;background:#353532}.brand-loader__mark i::after{content:'';display:block;width:45%;height:100%;background:#d9ff36;animation:brand-scan 1s ease-in-out infinite}.brand-loader>span{position:relative;margin-top:34px;color:#716f69;font:8px 'DM Mono',monospace;letter-spacing:.18em}@keyframes brand-stem{from{opacity:0;transform:translateX(-22px)}to{opacity:1;transform:none}}@keyframes brand-cells{from{opacity:0;transform:translateX(22px)}to{opacity:1;transform:none}}@keyframes brand-scan{from{transform:translateX(-120%)}to{transform:translateX(330%)}}@media(prefers-reduced-motion:reduce){.stem,.cells,.brand-loader__mark i::after{animation:none}}
</style>
