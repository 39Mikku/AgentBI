<script setup lang="ts">
import { useRouter } from 'vue-router'


const router = useRouter()
</script>

<template>
  <main class="toolbox-home">
    <div class="grain" aria-hidden="true"></div>
    <header class="toolbox-nav">
      <button class="wordmark" @click="router.push('/chat')"><i></i>AGENTBI <span>/ TOOLBOX</span></button>
      <nav aria-label="工作模式">
        <button @click="router.push('/chat')">Studio</button>
        <button @click="router.push('/live')">Live</button>
        <button class="active">Toolbox</button>
      </nav>
    </header>

    <section class="toolbox-intro">
      <div>
        <p>LOCAL UTILITIES · 004</p>
        <h1>把小工具，<br><em>放回手边。</em></h1>
      </div>
      <aside>
        <span>不经过大模型</span>
        <span>配置与执行留在本机</span>
        <span>即开 · 即用 · 即关</span>
      </aside>
    </section>

    <section class="tool-grid">
      <button class="tool-card voice-card" @click="router.push('/toolbox/voice')">
        <span class="card-index">01 / VOICE</span>
        <div class="voice-graphic" aria-hidden="true"><i v-for="height in [18, 41, 27, 65, 48, 82, 31, 57, 24, 70, 38, 54]" :key="height" :style="{ height: `${height}%` }"></i></div>
        <div class="card-copy"><p>多供应商语音合成工作台</p><h2>VOICE<br>LAB</h2><span>MiniMax · CosyVoice · MiMo · Doubao</span></div>
        <b>进入工作台 ↗</b>
      </button>

      <button class="tool-card time-card" @click="router.push('/toolbox/file-time')">
        <span class="card-index">02 / FILE SYSTEM</span>
        <div class="time-graphic" aria-hidden="true">
          <div class="dial"><i></i><b></b><span v-for="n in 12" :key="n" :style="{ transform: `rotate(${n * 30}deg)` }"></span></div>
          <code>2026—07—15<br>22:18:42</code>
        </div>
        <div class="card-copy"><p>批量校准与迁移文件时间</p><h2>FILE<br>TIME</h2><span>CREATED · MODIFIED · MOVE</span></div>
        <b>管理文件 ↗</b>
      </button>

      <button class="tool-card type-card" @click="router.push('/toolbox/auto-input')">
        <span class="card-index">03 / KEYBOARD</span>
        <div class="type-graphic" aria-hidden="true"><span>AUTO INPUT SEQUENCE_</span><i></i><small>UNICODE / WIN32 / LOCAL</small></div>
        <div class="card-copy"><p>把文本序列逐字送入当前窗口</p><h2>AUTO<br>TYPE</h2><span>COUNTDOWN · PROGRESS · CANCEL</span></div>
        <b>启动序列 ↗</b>
      </button>

      <button class="tool-card moe-card" @click="router.push('/toolbox/moegirl')">
        <span class="card-index">04 / KNOWLEDGE</span>
        <div class="moe-graphic" aria-hidden="true">
          <span>萌</span>
          <div><i></i><i></i><i></i><i></i><i></i></div>
          <small>HTML → CLEAN MARKDOWN</small>
        </div>
        <div class="card-copy"><p>萌娘百科正文清洗与本地归档</p><h2>MOE<br>ARCHIVE</h2><span>FETCH · PREVIEW · SAVE · DOWNLOAD</span></div>
        <b>打开知识台 ↗</b>
      </button>

      <article class="manifest-card">
        <span>TOOLBOX / MANIFEST</span>
        <strong>一套容器，<br>装下高频而具体的动作。</strong>
        <p>工具之间不共享运行产物；配置留在本机，结果由你决定是否保存。</p>
        <ol>
          <li><b>01</b>VOICE LAB <i>READY</i></li>
          <li><b>02</b>FILE TIME <i>READY</i></li>
          <li><b>03</b>AUTO TYPE <i>READY</i></li>
          <li><b>04</b>MOE ARCHIVE <i>READY</i></li>
        </ol>
      </article>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@500;600;700&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');
*{box-sizing:border-box}.toolbox-home{--ink:#11110f;--paper:#efede6;--acid:#d9ff36;--cyan:#8fffe4;--coral:#ff684c;position:relative;min-height:100vh;overflow:hidden;background:var(--ink);color:var(--paper);padding:0 clamp(22px,5vw,76px) 70px;font-family:Manrope,sans-serif}.grain{position:fixed;inset:0;pointer-events:none;opacity:.12;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.22'/%3E%3C/svg%3E")}.toolbox-nav{height:78px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #30302d}.toolbox-nav button{border:0;background:transparent;color:inherit;cursor:pointer}.wordmark{display:flex;align-items:center;gap:9px;font:700 11px 'DM Mono';letter-spacing:.14em}.wordmark i{width:17px;height:17px;border:1px solid var(--acid);position:relative}.wordmark i:after{content:'';position:absolute;width:5px;height:5px;right:-3px;bottom:-3px;background:var(--acid)}.wordmark span{color:#686760;font-weight:400}.toolbox-nav nav{display:flex;gap:2px}.toolbox-nav nav button{padding:9px 13px;color:#686760;font:9px 'DM Mono';letter-spacing:.08em}.toolbox-nav nav button:hover{color:var(--paper)}.toolbox-nav nav .active{background:var(--acid);color:#10110d}.toolbox-intro{display:grid;grid-template-columns:1fr auto;align-items:end;gap:40px;padding:74px 0 52px}.toolbox-intro p{margin:0 0 16px;color:var(--acid);font:9px 'DM Mono';letter-spacing:.17em}.toolbox-intro h1{margin:0;font:600 clamp(52px,7.5vw,110px)/.86 'Playfair Display';letter-spacing:-.065em}.toolbox-intro h1 em{color:#76736b}.toolbox-intro aside{display:grid;gap:9px;min-width:210px;padding-bottom:8px;color:#77746d;font:8px 'DM Mono';letter-spacing:.09em}.toolbox-intro aside span:before{content:'—';color:var(--acid);margin-right:9px}.tool-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;max-width:1500px;margin:auto;background:#3a3934;border:1px solid #3a3934}.tool-card,.manifest-card{min-height:440px}.tool-card{position:relative;overflow:hidden;border:0;background:var(--paper);color:var(--ink);padding:27px;text-align:left;cursor:pointer}.tool-card:after{content:'';position:absolute;inset:0;opacity:0;transition:opacity .35s}.tool-card:hover:after{opacity:1}.card-index,.manifest-card>span{position:relative;z-index:2;font:8px 'DM Mono';letter-spacing:.14em}.card-copy{position:absolute;left:27px;bottom:29px;z-index:2}.card-copy p{margin:0 0 10px;color:#6f6c64;font-size:10px}.card-copy h2{margin:0;font:700 clamp(41px,4.7vw,72px)/.77 Manrope;letter-spacing:-.08em}.card-copy span{display:block;margin-top:17px;color:#68655e;font:8px 'DM Mono'}.tool-card>b{position:absolute;right:25px;bottom:27px;z-index:2;font:9px 'DM Mono'}.voice-card:after{background:linear-gradient(125deg,transparent 55%,rgba(217,255,54,.35))}.voice-graphic{position:absolute;left:27px;right:27px;top:74px;height:135px;display:flex;align-items:center;gap:clamp(3px,.8vw,11px);border-top:1px solid #c5c2b9;border-bottom:1px solid #c5c2b9}.voice-graphic i{flex:1;min-width:3px;background:#151513;transform-origin:center;transition:height .5s cubic-bezier(.2,.8,.2,1)}.voice-card:hover .voice-graphic i:nth-child(2n){height:88%!important}.time-card{background:#d9d8cf}.time-card:after{background:radial-gradient(circle at 55% 30%,rgba(255,104,76,.45),transparent 42%)}.time-graphic{position:absolute;left:27px;right:27px;top:66px;height:160px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #b8b7ae}.dial{position:relative;width:132px;height:132px;border:1px solid #85867d;border-radius:50%}.dial span{position:absolute;left:65px;top:4px;width:1px;height:6px;background:#77786f;transform-origin:0 61px}.dial i,.dial b{position:absolute;left:65px;top:65px;width:2px;background:#121310;transform-origin:bottom}.dial i{height:43px;transform:translateY(-43px) rotate(48deg)}.dial b{height:31px;transform:translateY(-31px) rotate(142deg);background:var(--coral)}.time-graphic code{text-align:right;font:500 clamp(12px,1.2vw,18px)/1.7 'DM Mono';letter-spacing:.08em}.type-card{background:#161714;color:#eeede5}.type-card:after{background:linear-gradient(135deg,transparent 40%,rgba(143,255,228,.2))}.type-card .card-copy p,.type-card .card-copy span{color:#777c74}.type-graphic{position:absolute;left:27px;right:27px;top:75px;height:135px;border-top:1px solid #3e423c;border-bottom:1px solid #3e423c;padding-top:32px}.type-graphic>span{font:500 clamp(12px,1.3vw,17px) 'DM Mono';letter-spacing:.05em}.type-graphic i{display:inline-block;width:9px;height:21px;margin-left:4px;vertical-align:middle;background:var(--cyan);animation:blink 1s steps(1) infinite}.type-graphic small{display:block;margin-top:28px;color:#657069;font:7px 'DM Mono';letter-spacing:.14em}.type-card>b{color:var(--cyan)}.manifest-card{grid-column:1/-1;min-height:auto;padding:27px;background:#191917}.manifest-card>span{color:var(--acid)}.manifest-card>strong{display:block;margin-top:35px;font:600 clamp(23px,3vw,38px)/1.08 'Playfair Display';letter-spacing:-.035em}.manifest-card>p{max-width:480px;margin:18px 0;color:#77746d;font-size:10px;line-height:1.7}.manifest-card ol{display:grid;grid-template-columns:repeat(4,1fr);list-style:none;padding:0;margin:30px 0 0;border-top:1px solid #353531}.manifest-card li{display:grid;grid-template-columns:26px 1fr;gap:5px;padding:14px 16px 14px 0;border-right:1px solid #353531;color:#aba89f;font:8px 'DM Mono'}.manifest-card li>b{color:#55534e}.manifest-card li i{grid-column:2;color:var(--acid);font-style:normal}.manifest-card li:last-child i{color:#55534e}@keyframes blink{50%{opacity:0}}@media(max-width:1050px){.tool-grid{grid-template-columns:1fr 1fr}.type-card{grid-column:1/-1}.type-card .card-copy h2{font-size:64px}.manifest-card{grid-column:1/-1}}@media(max-width:720px){.toolbox-nav nav button:not(.active){display:none}.toolbox-intro{grid-template-columns:1fr;padding-top:55px}.toolbox-intro aside{grid-template-columns:1fr 1fr}.tool-grid{grid-template-columns:1fr}.tool-card,.type-card{grid-column:auto;min-height:480px}.tool-card>b{left:27px;right:auto;bottom:16px}.card-copy{bottom:52px}.manifest-card{grid-column:auto}.manifest-card ol{grid-template-columns:1fr 1fr}.time-graphic{justify-content:flex-start;gap:40px}}@media(max-width:450px){.toolbox-home{padding-inline:14px}.toolbox-intro aside{grid-template-columns:1fr}.manifest-card ol{grid-template-columns:1fr}.manifest-card li{border-right:0}}
.tool-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.moe-card{background:var(--acid)}.moe-card:after{background:linear-gradient(145deg,transparent 42%,rgba(17,17,15,.17))}.moe-graphic{position:absolute;left:27px;right:27px;top:66px;height:156px;border-top:1px solid rgba(17,17,15,.45);border-bottom:1px solid rgba(17,17,15,.45)}.moe-graphic>span{position:absolute;top:5px;left:0;font:700 80px/1 Manrope;letter-spacing:-.1em}.moe-graphic>div{position:absolute;left:92px;right:0;top:29px;display:grid;gap:8px}.moe-graphic i{display:block;height:2px;background:#171713;transform-origin:left;transition:transform .3s}.moe-graphic i:nth-child(2){transform:scaleX(.72)}.moe-graphic i:nth-child(3){transform:scaleX(.88)}.moe-graphic i:nth-child(4){transform:scaleX(.58)}.moe-graphic i:nth-child(5){transform:scaleX(.8)}.moe-card:hover .moe-graphic i{transform:scaleX(1)}.moe-graphic small{position:absolute;bottom:8px;right:0;font:7px 'DM Mono';letter-spacing:.12em}.moe-card .card-copy p,.moe-card .card-copy span{color:#4a501f}.manifest-card li:last-child i{color:var(--acid)}@media(max-width:1050px){.tool-grid{grid-template-columns:1fr 1fr}.type-card{grid-column:auto}}@media(max-width:720px){.tool-grid{grid-template-columns:1fr}}
</style>
