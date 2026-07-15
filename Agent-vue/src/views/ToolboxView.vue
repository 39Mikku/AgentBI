<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <main class="toolbox-home">
    <div class="grain"></div>
    <header class="toolbox-nav">
      <button class="wordmark" @click="router.push('/chat')"><i></i>AGENTBI <span>/ TOOLBOX</span></button>
      <nav>
        <button @click="router.push('/chat')">Studio</button>
        <button @click="router.push('/live')">Live</button>
        <button class="active">Toolbox</button>
      </nav>
    </header>

    <section class="toolbox-intro">
      <div>
        <p>LOCAL UTILITIES · 001</p>
        <h1>把小工具，<br><em>放回手边。</em></h1>
      </div>
      <aside>
        <span>不经过大模型</span>
        <span>不保留生成文件</span>
        <span>即开 · 即用 · 即关</span>
      </aside>
    </section>

    <section class="tool-grid">
      <button class="voice-card" @click="router.push('/toolbox/voice')">
        <span class="card-index">01 / VOICE</span>
        <div class="voice-graphic" aria-hidden="true">
          <i v-for="height in [18, 41, 27, 65, 48, 82, 31, 57, 24, 70, 38, 54]" :key="height" :style="{ height: `${height}%` }"></i>
        </div>
        <div class="card-copy">
          <p>多供应商语音合成工作台</p>
          <h2>VOICE<br>LAB</h2>
          <span>MiniMax · CosyVoice · MiMo · Doubao</span>
        </div>
        <b>进入工作台 ↗</b>
      </button>

      <article class="manifest-card">
        <span>TOOLBOX / MANIFEST</span>
        <strong>一套容器，<br>装下那些高频而具体的动作。</strong>
        <p>工具之间不共享运行产物；配置留在本机，结果由你决定是否保存。</p>
        <ol><li><b>01</b>VOICE LAB <i>READY</i></li><li><b>02</b>MEDIA KIT <i>PLANNED</i></li><li><b>03</b>DATA UTILS <i>PLANNED</i></li></ol>
      </article>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
*{box-sizing:border-box}.toolbox-home{--ink:#11110f;--paper:#efede6;--acid:#d9ff36;position:relative;min-height:100vh;overflow:hidden;background:var(--ink);color:var(--paper);padding:0 clamp(22px,5vw,76px) 70px;font-family:Manrope,sans-serif}.grain{position:fixed;inset:0;pointer-events:none;opacity:.13;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.22'/%3E%3C/svg%3E")}.toolbox-nav{height:78px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #30302d}.toolbox-nav button{border:0;background:transparent;color:inherit;cursor:pointer}.wordmark{display:flex;align-items:center;gap:9px;font:700 11px 'DM Mono';letter-spacing:.14em}.wordmark i{width:17px;height:17px;border:1px solid var(--acid);position:relative}.wordmark i:after{content:'';position:absolute;width:5px;height:5px;right:-3px;bottom:-3px;background:var(--acid)}.wordmark span{color:#686760;font-weight:400}.toolbox-nav nav{display:flex;gap:2px}.toolbox-nav nav button{padding:9px 13px;color:#686760;font:9px 'DM Mono';letter-spacing:.08em}.toolbox-nav nav button:hover{color:var(--paper)}.toolbox-nav nav .active{background:var(--acid);color:#10110d}.toolbox-intro{display:grid;grid-template-columns:1fr auto;align-items:end;gap:40px;padding:74px 0 52px}.toolbox-intro p{margin:0 0 16px;color:var(--acid);font:9px 'DM Mono';letter-spacing:.17em}.toolbox-intro h1{margin:0;font:600 clamp(52px,7.5vw,110px)/.86 'Playfair Display';letter-spacing:-.065em}.toolbox-intro h1 em{color:#76736b}.toolbox-intro aside{display:grid;gap:9px;min-width:190px;padding-bottom:8px;color:#77746d;font:8px 'DM Mono';letter-spacing:.09em}.toolbox-intro aside span:before{content:'—';color:var(--acid);margin-right:9px}.tool-grid{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(280px,.72fr);gap:1px;max-width:1280px;background:#3a3934;border:1px solid #3a3934}.voice-card,.manifest-card{min-height:440px}.voice-card{position:relative;overflow:hidden;border:0;background:var(--paper);color:var(--ink);padding:27px;text-align:left;cursor:pointer}.voice-card:after{content:'';position:absolute;inset:0;background:linear-gradient(120deg,transparent 60%,rgba(217,255,54,.28));opacity:0;transition:opacity .35s}.voice-card:hover:after{opacity:1}.card-index,.manifest-card>span{font:8px 'DM Mono';letter-spacing:.14em}.voice-graphic{position:absolute;left:27px;right:27px;top:74px;height:152px;display:flex;align-items:center;gap:clamp(4px,1vw,14px);border-top:1px solid #c5c2b9;border-bottom:1px solid #c5c2b9}.voice-graphic i{flex:1;min-width:3px;background:#151513;transform-origin:center;transition:height .5s cubic-bezier(.2,.8,.2,1)}.voice-card:hover .voice-graphic i:nth-child(2n){height:88%!important}.card-copy{position:absolute;left:27px;bottom:29px;z-index:1}.card-copy p{margin:0 0 10px;color:#6f6c64;font-size:10px}.card-copy h2{margin:0;font:700 clamp(45px,6vw,82px)/.77 Manrope;letter-spacing:-.08em}.card-copy span{display:block;margin-top:17px;color:#68655e;font:8px 'DM Mono'}.voice-card>b{position:absolute;right:25px;bottom:27px;z-index:1;font:9px 'DM Mono'}.manifest-card{padding:27px;background:#191917}.manifest-card>span{color:var(--acid)}.manifest-card>strong{display:block;margin-top:48px;font:600 24px/1.18 'Playfair Display';letter-spacing:-.035em}.manifest-card>p{max-width:300px;margin:20px 0;color:#77746d;font-size:10px;line-height:1.7}.manifest-card ol{list-style:none;padding:0;margin:54px 0 0;border-top:1px solid #353531}.manifest-card li{display:grid;grid-template-columns:26px 1fr auto;padding:14px 0;border-bottom:1px solid #353531;color:#aba89f;font:8px 'DM Mono'}.manifest-card li>b{color:#55534e}.manifest-card li i{color:#55534e;font-style:normal}.manifest-card li:first-child i{color:var(--acid)}@media(max-width:780px){.toolbox-nav nav button:not(.active){display:none}.toolbox-intro{grid-template-columns:1fr;padding-top:55px}.toolbox-intro aside{grid-template-columns:1fr 1fr}.tool-grid{grid-template-columns:1fr}.voice-card{min-height:480px}.manifest-card{min-height:auto}.voice-card>b{left:27px;right:auto;bottom:16px}.card-copy{bottom:52px}}
</style>
