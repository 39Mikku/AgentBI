<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AppModeSwitcher from '@/components/AppModeSwitcher.vue'
import { useAuthStore } from '@/stores/auth'
import { useLiveStore } from '@/stores/live'
import type { LiveModelId, LiveVoiceId } from '@/api/live-types'

const auth = useAuthStore()
const live = useLiveStore()
const settingsOpen = ref(false)
const transcriptRail = ref<HTMLElement | null>(null)
const userId = computed(() => auth.email || 'local-user')
const userName = computed(
  () => auth.profile?.username || userId.value.split('@')[0] || userId.value,
)
const userInitials = computed(() => userName.value.slice(0, 2).toUpperCase())
const phaseCode = computed(() => live.state.phase.toUpperCase().padEnd(10, '·'))
const modelTier = computed(() =>
  live.preferences.model.endsWith('plus') ? 'PLUS' : 'FLASH',
)
const callDurationLabel = ref('00:00')
let durationTimer: ReturnType<typeof setInterval> | null = null
let startedAt = 0

const models: Array<{ id: LiveModelId; label: string; note: string }> = [
  { id: 'qwen-audio-3.0-realtime-flash', label: 'Flash', note: '低延迟实时通话' },
  { id: 'qwen-audio-3.0-realtime-plus', label: 'Plus', note: '更强语音理解' },
]
const voices: Array<{ id: LiveVoiceId; label: string; code: string }> = [
  { id: 'longanqian', label: '芊', code: 'QIAN' },
  { id: 'longanlingxin', label: '灵心', code: 'LINGXIN' },
  { id: 'longanlingxi', label: '灵犀', code: 'LINGXI' },
  { id: 'longanxiaoxin', label: '小新', code: 'XIAOXIN' },
  { id: 'longanlufeng', label: '鹿风', code: 'LUFENG' },
]

function updateDuration() {
  const seconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000))
  callDurationLabel.value = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

function startDuration() {
  startedAt = Date.now()
  callDurationLabel.value = '00:00'
  if (durationTimer) clearInterval(durationTimer)
  durationTimer = setInterval(updateDuration, 1000)
}

function stopDuration() {
  if (durationTimer) clearInterval(durationTimer)
  durationTimer = null
  callDurationLabel.value = '00:00'
}

async function toggleCall() {
  if (live.isActive) {
    await live.endCall()
    stopDuration()
    return
  }
  startDuration()
  await live.startCall(userId.value)
  if (live.state.phase === 'error') stopDuration()
}

async function saveSettings() {
  await live.persistPreferences(userId.value)
  settingsOpen.value = false
}

watch(
  () => live.state.transcripts.map((item) => `${item.id}:${item.text}:${item.stash}`).join('|'),
  async () => {
    await nextTick()
    transcriptRail.value?.scrollTo({
      top: transcriptRail.value.scrollHeight,
      behavior: 'smooth',
    })
  },
)

onMounted(() => live.loadPreferences(userId.value))
onBeforeUnmount(() => {
  stopDuration()
  if (live.isActive) void live.endCall()
})
</script>

<template>
  <div class="live-shell" :data-phase="live.state.phase">
    <aside class="live-rail">
      <div class="live-brand"><span class="brand-mark"><i></i></span><span>OBSIDIAN</span><b>LIVE</b></div>
      <AppModeSwitcher active="live" />

      <section class="channel-card">
        <span class="section-code">CH / 001</span>
        <div class="channel-avatar">
          <img v-if="auth.profile?.avatar_data_url" :src="auth.profile.avatar_data_url" alt="" />
          <span v-else>{{ userInitials }}</span>
          <i :class="{ online: live.isActive }"></i>
        </div>
        <p>VOICE CHANNEL</p>
        <strong>{{ userName }}</strong>
        <small>{{ userId }}</small>
      </section>

      <dl class="signal-spec">
        <div><dt>UPLINK</dt><dd>PCM · 16 kHz</dd></div>
        <div><dt>DOWNLINK</dt><dd>PCM · 24 kHz</dd></div>
        <div><dt>TURN MODE</dt><dd>SMART TURN</dd></div>
        <div><dt>ENGINE</dt><dd>QWEN AUDIO 3</dd></div>
      </dl>

      <div class="rail-spacer"></div>
      <button class="rail-settings" @click="settingsOpen = true">
        <span>CONTROL DECK</span><strong>语音配置</strong><i>↗</i>
      </button>
      <RouterLink class="back-studio" to="/chat">返回文字工作台 <span>→</span></RouterLink>
    </aside>

    <main class="live-console">
      <header class="console-head">
        <div>
          <span class="eyebrow">FULL-DUPLEX AUDIO SESSION</span>
          <h1>Live <em>signal</em></h1>
        </div>
        <div class="head-metrics">
          <span><i></i>{{ live.isActive ? callDurationLabel : 'STANDBY' }}</span>
          <span class="tier">{{ modelTier }}</span>
          <button @click="settingsOpen = true">配置 <b>⌘</b></button>
        </div>
      </header>

      <div class="console-body">
        <section class="voice-stage">
          <div class="stage-coordinates"><span>34°N / 108°E</span><span>{{ phaseCode }}</span></div>
          <div class="orbital-field" :class="{ muted: live.muted }">
            <div class="orbit orbit-a"></div>
            <div class="orbit orbit-b"></div>
            <div class="orbit orbit-c"></div>
            <div class="voice-core">
              <div class="core-grid"></div>
              <div class="wave-bars" aria-hidden="true">
                <i v-for="index in 19" :key="index" :style="{ '--bar': index }"></i>
              </div>
              <span>{{ live.muted ? 'MUTED' : modelTier }}</span>
            </div>
          </div>
          <div class="stage-status" aria-live="polite">
            <span class="status-pulse"></span>
            <div><small>CHANNEL STATUS</small><strong>{{ live.statusLabel }}</strong></div>
            <code>{{ live.state.phase === 'idle' ? 'READY' : phaseCode }}</code>
          </div>
          <p v-if="live.state.error" class="live-error">{{ live.state.error }}</p>
        </section>

        <section class="transcript-panel">
          <header>
            <div><span>LIVE TRANSCRIPT</span><strong>实时字幕</strong></div>
            <button
              :disabled="live.isActive || !live.state.transcripts.length"
              @click="live.clearTranscripts"
            >清空</button>
          </header>
          <div ref="transcriptRail" class="transcript-list">
            <div v-if="!live.state.transcripts.length" class="transcript-empty">
              <span>NO SIGNAL YET</span>
              <p>开始通话后，双方字幕会<br />在这里随声音逐字出现。</p>
              <i></i>
            </div>
            <article
              v-for="item in live.state.transcripts"
              :key="item.id"
              :class="[item.role, { interrupted: item.interrupted }]"
            >
              <div class="speaker-line">
                <span>{{ item.role === 'user' ? userName : 'QWEN AUDIO' }}</span>
                <code>{{ item.role === 'user' ? 'IN' : 'OUT' }}</code>
              </div>
              <p>{{ item.text }}<span v-if="item.stash" class="stash">{{ item.stash }}</span><i v-if="!item.final"></i></p>
              <small v-if="item.interrupted">INTERRUPTED / 已打断</small>
            </article>
          </div>
        </section>
      </div>

      <footer class="call-dock">
        <div class="dock-note"><span>01</span><p>佩戴耳机可获得更稳定的<br />全双工打断体验</p></div>
        <div class="call-controls">
          <button
            class="mute-button"
            :class="{ active: live.muted }"
            :disabled="!live.isActive || live.state.phase === 'ending'"
            :title="live.muted ? '恢复麦克风' : '静音麦克风'"
            @click="live.toggleMute"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm-7-3a7 7 0 0 0 14 0M12 18v3M8 21h8"/></svg>
            <span>{{ live.muted ? '恢复' : '静音' }}</span>
          </button>
          <button
            class="call-button"
            :class="{ active: live.isActive }"
            :disabled="live.state.phase === 'connecting' || live.state.phase === 'ending'"
            @click="toggleCall"
          >
            <span class="call-icon"><i></i></span>
            <strong>{{ live.isActive ? '结束通话' : '开始通话' }}</strong>
            <small>{{ live.isActive ? 'END SESSION' : 'OPEN CHANNEL' }}</small>
          </button>
          <button class="deck-button" @click="settingsOpen = true">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M10 14v6"/></svg>
            <span>配置</span>
          </button>
        </div>
        <div class="dock-note right"><p>{{ live.preferences.voice }}<br />{{ modelTier }} PROFILE</p><span>02</span></div>
      </footer>
    </main>

    <Transition name="deck">
      <div v-if="settingsOpen" class="deck-backdrop" @click.self="settingsOpen = false">
        <aside class="settings-deck">
          <header><div><span>LIVE / CONTROL DECK</span><h2>塑造这通声音</h2></div><button @click="settingsOpen = false">×</button></header>
          <p class="deck-intro">配置会保存到当前用户，并在下一次建立实时连接时生效。</p>

          <section class="deck-section">
            <label>01 · 推理档位</label>
            <div class="model-options">
              <button
                v-for="model in models"
                :key="model.id"
                :class="{ active: live.preferences.model === model.id }"
                :disabled="!live.canEditSettings"
                @click="live.preferences.model = model.id"
              ><span>{{ model.label }}</span><small>{{ model.note }}</small><i></i></button>
            </div>
          </section>

          <section class="deck-section">
            <label>02 · 系统音色</label>
            <div class="voice-options">
              <button
                v-for="voice in voices"
                :key="voice.id"
                :class="{ active: live.preferences.voice === voice.id }"
                :disabled="!live.canEditSettings"
                @click="live.preferences.voice = voice.id"
              ><strong>{{ voice.label }}</strong><small>{{ voice.code }}</small></button>
            </div>
          </section>

          <section class="deck-section prompt-section">
            <label>03 · 系统提示词 <span>{{ live.preferences.instructions.length }} / 12000</span></label>
            <textarea
              v-model="live.preferences.instructions"
              maxlength="12000"
              :disabled="!live.canEditSettings"
              placeholder="描述角色、语气和回应方式…"
            ></textarea>
            <small>Live 只使用这一段系统提示词，不拼接工具、记忆或 RAG 配置。</small>
          </section>

          <p v-if="!live.canEditSettings" class="deck-lock">结束当前通话后才能更换模型、音色和提示词。</p>
          <footer>
            <button class="cancel" @click="settingsOpen = false">取消</button>
            <button
              class="save"
              :disabled="live.saving || !live.canEditSettings || !live.preferences.instructions.trim()"
              @click="saveSettings"
            >{{ live.saving ? '保存中…' : '保存配置' }}</button>
          </footer>
        </aside>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700&family=Syne:wght@500;600;700&display=swap');
.live-shell {
  --void: #070a09;
  --panel: #0d1110;
  --panel-2: #111715;
  --mist: #dce8e2;
  --muted: #6e7974;
  --signal: #8df9d2;
  --signal-deep: #28a983;
  --danger: #ff6b5d;
  width: 100%;
  height: 100dvh;
  overflow: hidden;
  display: grid;
  grid-template-columns: 264px minmax(0, 1fr);
  color: var(--mist);
  background: var(--void);
  font-family: Manrope, sans-serif;
  position: relative;
}
.live-shell::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 20;
  opacity: 0.14;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.22'/%3E%3C/svg%3E");
  mix-blend-mode: soft-light;
}
button, textarea { font: inherit; }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: 0.42; }
.live-rail {
  min-height: 0;
  padding: 26px 18px 19px;
  border-right: 1px solid rgba(141, 249, 210, 0.12);
  background: #0a0d0c;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  z-index: 2;
}
.live-rail::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(0deg, transparent 0 31px, rgba(141,249,210,.025) 31px 32px);
}
.live-brand { display: flex; align-items: center; gap: 8px; padding: 0 7px 4px; font: 700 12px Syne; letter-spacing: .13em; }
.live-brand b { color: var(--signal); font: 500 9px 'DM Mono'; margin-left: auto; }
.brand-mark { width: 18px; height: 18px; border: 1px solid var(--signal); border-radius: 50%; display: grid; place-items: center; }
.brand-mark i { width: 6px; height: 6px; border-radius: 50%; background: var(--signal); box-shadow: 0 0 12px var(--signal); }
.channel-card { border: 1px solid rgba(255,255,255,.1); padding: 18px; background: rgba(255,255,255,.025); position: relative; }
.section-code { position: absolute; right: 10px; top: 9px; font: 8px 'DM Mono'; color: #4d5b55; }
.channel-avatar { width: 54px; height: 54px; margin-bottom: 16px; position: relative; }
.channel-avatar img, .channel-avatar > span { width: 100%; height: 100%; border-radius: 4px; object-fit: cover; display: grid; place-items: center; background: var(--signal); color: #07100d; font: 700 14px Syne; }
.channel-avatar i { position: absolute; width: 9px; height: 9px; right: -3px; bottom: -3px; border-radius: 50%; background: #3a423e; border: 2px solid #0d1110; }
.channel-avatar i.online { background: var(--signal); box-shadow: 0 0 12px rgba(141,249,210,.8); }
.channel-card p { margin: 0 0 6px; font: 8px 'DM Mono'; color: var(--signal); letter-spacing: .12em; }
.channel-card strong { display: block; font: 600 16px Syne; }
.channel-card small { display: block; margin-top: 4px; color: #68736e; font: 9px 'DM Mono'; overflow: hidden; text-overflow: ellipsis; }
.signal-spec { margin: 0; display: grid; gap: 0; }
.signal-spec div { display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,.07); padding: 9px 2px; }
.signal-spec dt, .signal-spec dd { margin: 0; font: 8px 'DM Mono'; letter-spacing: .08em; }
.signal-spec dt { color: #47524d; } .signal-spec dd { color: #9aa59f; }
.rail-spacer { flex: 1; }
.rail-settings { position: relative; z-index: 1; display: grid; grid-template-columns: 1fr auto; text-align: left; padding: 13px; border: 1px solid rgba(141,249,210,.18); background: rgba(141,249,210,.045); color: var(--mist); }
.rail-settings span { font: 7px 'DM Mono'; color: var(--signal); letter-spacing: .12em; } .rail-settings strong { grid-column: 1; margin-top: 4px; font-size: 11px; } .rail-settings i { grid-column: 2; grid-row: 1/3; align-self: center; font-style: normal; color: var(--signal); }
.back-studio { position: relative; z-index: 1; display: flex; justify-content: space-between; color: #69736e; text-decoration: none; font-size: 10px; padding: 3px 2px; }
.back-studio:hover { color: var(--signal); }
.live-console { min-width: 0; min-height: 0; display: grid; grid-template-rows: 92px minmax(0,1fr) 108px; position: relative; background-image: linear-gradient(rgba(141,249,210,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(141,249,210,.035) 1px, transparent 1px); background-size: 44px 44px; }
.live-console::before { content: ''; position: absolute; inset: 0; pointer-events: none; background: radial-gradient(circle at 42% 45%, rgba(48,160,125,.1), transparent 34%); }
.console-head { z-index: 1; display: flex; justify-content: space-between; align-items: center; padding: 19px 30px; border-bottom: 1px solid rgba(255,255,255,.08); background: rgba(7,10,9,.76); backdrop-filter: blur(14px); }
.eyebrow { display: block; color: #53605a; font: 8px 'DM Mono'; letter-spacing: .16em; margin-bottom: 4px; }
.console-head h1 { margin: 0; font: 600 26px/1 Syne; letter-spacing: -.04em; } .console-head h1 em { color: var(--signal); font-style: normal; font-weight: 500; }
.head-metrics { display: flex; align-items: center; gap: 10px; }
.head-metrics > span, .head-metrics button { height: 32px; display: inline-flex; align-items: center; gap: 7px; padding: 0 11px; border: 1px solid rgba(255,255,255,.1); background: #0b0f0e; color: #7c8983; font: 8px 'DM Mono'; letter-spacing: .08em; }
.head-metrics span i { width: 5px; height: 5px; border-radius: 50%; background: #414b46; }.live-shell:not([data-phase='idle']) .head-metrics span i { background: var(--signal); box-shadow: 0 0 9px var(--signal); }
.head-metrics .tier { color: var(--signal); }.head-metrics button b { color: #45504b; }
.console-body { z-index: 1; min-height: 0; display: grid; grid-template-columns: minmax(430px, 1fr) minmax(320px, 38%); }
.voice-stage { min-height: 0; position: relative; display: grid; place-items: center; border-right: 1px solid rgba(255,255,255,.08); overflow: hidden; }
.stage-coordinates { position: absolute; inset: 18px 22px auto; display: flex; justify-content: space-between; color: #36413c; font: 8px 'DM Mono'; letter-spacing: .12em; }
.orbital-field { width: clamp(270px, 32vw, 430px); aspect-ratio: 1; display: grid; place-items: center; position: relative; }
.orbit { position: absolute; border-radius: 50%; border: 1px solid rgba(141,249,210,.12); }
.orbit-a { inset: 0; border-style: dashed; animation: rotate 28s linear infinite; }.orbit-b { inset: 12%; border-color: rgba(141,249,210,.2); animation: rotate 18s linear infinite reverse; }.orbit-c { inset: 26%; border-color: rgba(141,249,210,.13); }
.orbit-a::before, .orbit-b::before { content: ''; position: absolute; width: 6px; height: 6px; border-radius: 50%; top: -3px; left: 50%; background: var(--signal); box-shadow: 0 0 14px var(--signal); }
.voice-core { width: 43%; aspect-ratio: 1; border-radius: 50%; display: grid; place-items: center; position: relative; overflow: hidden; background: #0b1713; border: 1px solid rgba(141,249,210,.38); box-shadow: 0 0 0 14px rgba(141,249,210,.025), 0 0 80px rgba(40,169,131,.12); transition: transform .4s ease, border-color .4s; }
.core-grid { position: absolute; inset: 0; opacity: .25; background: linear-gradient(rgba(141,249,210,.15) 1px,transparent 1px),linear-gradient(90deg,rgba(141,249,210,.15) 1px,transparent 1px); background-size: 12px 12px; mask-image: radial-gradient(circle,#000,transparent 72%); }
.voice-core > span { position: absolute; bottom: 21%; font: 7px 'DM Mono'; letter-spacing: .18em; color: rgba(141,249,210,.55); }
.wave-bars { display: flex; align-items: center; height: 42px; gap: 3px; position: relative; z-index: 1; }
.wave-bars i { width: 2px; height: 5px; background: var(--signal); opacity: .65; animation: signal 1.1s ease-in-out infinite alternate; animation-delay: calc(var(--bar) * -55ms); transform-origin: center; }
.live-shell[data-phase='speaking'] .wave-bars i, .live-shell[data-phase='listening'] .wave-bars i { animation-duration: .42s; height: calc(5px + (var(--bar) % 5) * 4px); }
.live-shell[data-phase='thinking'] .voice-core { animation: breathe 1.4s ease-in-out infinite; }.orbital-field.muted { filter: grayscale(.9); opacity: .55; }
.stage-status { position: absolute; left: 25px; right: 25px; bottom: 20px; display: grid; grid-template-columns: auto 1fr auto; gap: 11px; align-items: center; border-top: 1px solid rgba(255,255,255,.08); padding-top: 13px; }
.status-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--signal); box-shadow: 0 0 12px rgba(141,249,210,.7); }.live-shell[data-phase='idle'] .status-pulse { background: #38413d; box-shadow: none; }
.stage-status small { display: block; font: 7px 'DM Mono'; color: #4d5953; letter-spacing: .12em; }.stage-status strong { display: block; margin-top: 2px; font: 500 12px Syne; }.stage-status code { font: 8px 'DM Mono'; color: #49544f; }
.live-error { position: absolute; bottom: 70px; max-width: 70%; padding: 8px 12px; border: 1px solid rgba(255,107,93,.3); color: #ff8c80; background: rgba(255,107,93,.06); font-size: 10px; }
.transcript-panel { min-height: 0; display: grid; grid-template-rows: 63px minmax(0,1fr); background: rgba(7,10,9,.62); }
.transcript-panel > header { display: flex; justify-content: space-between; align-items: center; padding: 0 21px; border-bottom: 1px solid rgba(255,255,255,.08); }
.transcript-panel header span { display: block; color: var(--signal); font: 7px 'DM Mono'; letter-spacing: .15em; }.transcript-panel header strong { display: block; margin-top: 4px; font: 500 12px Syne; }.transcript-panel header button { border: 0; background: none; color: #56615c; font: 9px 'DM Mono'; }
.transcript-list { min-height: 0; overflow-y: auto; padding: 20px; scrollbar-color: rgba(141,249,210,.25) transparent; scrollbar-width: thin; }
.transcript-empty { height: 100%; min-height: 220px; display: grid; place-content: center; text-align: center; color: #48534e; }
.transcript-empty span { font: 8px 'DM Mono'; letter-spacing: .18em; }.transcript-empty p { font-size: 11px; line-height: 1.7; }.transcript-empty i { width: 40px; height: 1px; background: #34403a; justify-self: center; margin-top: 8px; position: relative; }.transcript-empty i::after { content: ''; position: absolute; width: 3px; height: 3px; right: 0; top: -1px; background: var(--signal); }
.transcript-list article { padding: 13px 14px; margin-bottom: 11px; border-left: 1px solid #2a3631; background: rgba(255,255,255,.022); animation: transcript-in .35s ease both; }
.transcript-list article.user { margin-left: 18%; border-color: rgba(255,255,255,.28); }.transcript-list article.assistant { margin-right: 8%; border-color: var(--signal); background: rgba(141,249,210,.035); }
.speaker-line { display: flex; justify-content: space-between; margin-bottom: 8px; }.speaker-line span, .speaker-line code { font: 7px 'DM Mono'; letter-spacing: .12em; color: #5f6a65; }.assistant .speaker-line span { color: var(--signal); }
.transcript-list article p { margin: 0; color: #c8d1cc; font-size: 13px; line-height: 1.7; }.transcript-list article p > i { display: inline-block; width: 5px; height: 12px; background: var(--signal); margin-left: 4px; vertical-align: -2px; animation: blink .7s steps(1) infinite; }.stash { color: #59645f; }.transcript-list article > small { display: block; margin-top: 9px; color: #e88a7f; font: 7px 'DM Mono'; letter-spacing: .1em; }.transcript-list article.interrupted { border-color: rgba(255,107,93,.38); }
.call-dock { z-index: 2; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; padding: 13px 28px; border-top: 1px solid rgba(255,255,255,.08); background: #090c0b; }
.dock-note { display: flex; align-items: center; gap: 10px; color: #46514c; }.dock-note > span { font: 8px 'DM Mono'; color: var(--signal); }.dock-note p { margin: 0; font: 8px/1.55 'DM Mono'; letter-spacing: .04em; }.dock-note.right { justify-content: flex-end; text-align: right; }
.call-controls { display: flex; align-items: center; gap: 12px; }
.mute-button, .deck-button { width: 58px; height: 58px; border: 1px solid rgba(255,255,255,.11); background: #0e1311; color: #88948e; display: grid; place-content: center; gap: 2px; border-radius: 50%; transition: .2s; }.mute-button svg,.deck-button svg { width: 17px; height: 17px; justify-self: center; fill: none; stroke: currentColor; stroke-width: 1.5; }.mute-button span,.deck-button span { font: 7px 'DM Mono'; }.mute-button.active { color: var(--danger); border-color: rgba(255,107,93,.45); background: rgba(255,107,93,.07); }
.call-button { min-width: 170px; height: 70px; border: 1px solid rgba(141,249,210,.4); background: var(--signal); color: #07110d; display: grid; grid-template-columns: 34px 1fr; grid-template-rows: auto auto; text-align: left; align-content: center; column-gap: 10px; padding: 0 18px; transition: transform .2s, background .2s; }.call-button:hover:not(:disabled) { transform: translateY(-2px); }.call-button.active { background: #151a18; color: #e0e7e3; border-color: rgba(255,107,93,.45); }.call-icon { grid-row: 1/3; width: 30px; height: 30px; border: 1px solid currentColor; border-radius: 50%; display: grid; place-items: center; }.call-icon i { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }.call-button.active .call-icon i { border-radius: 1px; background: var(--danger); }.call-button strong { font: 600 11px Syne; }.call-button small { font: 7px 'DM Mono'; opacity: .58; }
.deck-backdrop { position: fixed; inset: 0; z-index: 40; background: rgba(0,0,0,.64); backdrop-filter: blur(8px); display: flex; justify-content: flex-end; }
.settings-deck { width: min(480px, 100%); height: 100%; overflow-y: auto; padding: 28px; border-left: 1px solid rgba(141,249,210,.22); background: #0b0f0e; box-shadow: -30px 0 90px rgba(0,0,0,.45); }
.settings-deck > header { display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 18px; border-bottom: 1px solid rgba(255,255,255,.09); }.settings-deck header span { color: var(--signal); font: 7px 'DM Mono'; letter-spacing: .16em; }.settings-deck h2 { margin: 6px 0 0; font: 600 25px Syne; letter-spacing: -.04em; }.settings-deck header button { width: 32px; height: 32px; border: 1px solid rgba(255,255,255,.12); background: transparent; color: #8b9691; font-size: 19px; }.deck-intro { color: #67726d; font-size: 10px; line-height: 1.65; margin: 15px 0 25px; }
.deck-section { margin-top: 25px; }.deck-section > label { display: flex; justify-content: space-between; color: #66716c; font: 8px 'DM Mono'; letter-spacing: .12em; margin-bottom: 10px; }
.model-options { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }.model-options button { position: relative; overflow: hidden; padding: 15px; text-align: left; border: 1px solid rgba(255,255,255,.1); background: #101513; color: #839089; }.model-options button span { display: block; color: #c6d0cb; font: 600 14px Syne; }.model-options button small { display: block; margin-top: 5px; font: 8px 'DM Mono'; }.model-options button i { position: absolute; bottom: 0; left: 0; height: 2px; width: 0; background: var(--signal); transition: width .2s; }.model-options button.active { border-color: rgba(141,249,210,.35); background: rgba(141,249,210,.055); }.model-options button.active i { width: 100%; }.model-options button.active span { color: var(--signal); }
.voice-options { display: grid; grid-template-columns: repeat(5,1fr); gap: 5px; }.voice-options button { min-width: 0; padding: 11px 3px; border: 1px solid rgba(255,255,255,.09); background: #101513; color: #727e78; }.voice-options strong { display: block; font: 600 11px Syne; }.voice-options small { display: block; overflow: hidden; text-overflow: ellipsis; margin-top: 5px; font: 6px 'DM Mono'; }.voice-options button.active { color: #07100d; background: var(--signal); border-color: var(--signal); }
.prompt-section textarea { width: 100%; min-height: 190px; resize: vertical; box-sizing: border-box; border: 1px solid rgba(255,255,255,.11); background: #080b0a; color: #d0d9d4; padding: 14px; outline: none; font: 11px/1.7 Manrope; }.prompt-section textarea:focus { border-color: rgba(141,249,210,.45); }.prompt-section > small { display: block; margin-top: 7px; color: #4f5b55; font: 8px/1.55 'DM Mono'; }.deck-lock { color: #e88a7f; font: 8px 'DM Mono'; margin: 17px 0 0; }.settings-deck > footer { display: grid; grid-template-columns: 1fr 1.5fr; gap: 8px; margin-top: 26px; }.settings-deck footer button { padding: 12px; border: 1px solid rgba(255,255,255,.12); }.settings-deck .cancel { background: transparent; color: #7c8782; }.settings-deck .save { background: var(--signal); color: #07110d; border-color: var(--signal); font-weight: 700; }
.deck-enter-active,.deck-leave-active { transition: opacity .25s ease; }.deck-enter-active .settings-deck,.deck-leave-active .settings-deck { transition: transform .3s cubic-bezier(.2,.8,.2,1); }.deck-enter-from,.deck-leave-to { opacity: 0; }.deck-enter-from .settings-deck,.deck-leave-to .settings-deck { transform: translateX(100%); }
@keyframes rotate { to { transform: rotate(360deg); } } @keyframes signal { from { transform: scaleY(.3); opacity: .35; } to { transform: scaleY(1.8); opacity: 1; } } @keyframes breathe { 50% { transform: scale(1.07); box-shadow: 0 0 0 22px rgba(141,249,210,.025),0 0 110px rgba(40,169,131,.22); } } @keyframes blink { 50% { opacity: 0; } } @keyframes transcript-in { from { opacity: 0; transform: translateY(8px); } }
@media (max-width: 920px) { .live-shell { grid-template-columns: 205px minmax(0,1fr); }.console-body { grid-template-columns: 1fr; }.transcript-panel { position: absolute; z-index: 5; right: 0; top: 92px; bottom: 108px; width: min(350px,45vw); border-left: 1px solid rgba(255,255,255,.08); }.voice-stage { border: 0; }.dock-note { display:none; }.call-dock { grid-template-columns:1fr; }.call-controls { justify-content:center; } }
@media (max-width: 680px) { .live-shell { display:block; overflow-y:auto; }.live-rail { height:auto; padding:14px; display:grid; grid-template-columns:1fr 1fr; }.live-brand,.channel-card,.signal-spec,.rail-settings,.back-studio { display:none; }.live-console { min-height:100dvh; grid-template-rows:74px 1fr 92px; }.console-head { padding:14px; }.console-head h1 { font-size:20px; }.head-metrics > span:first-child { display:none; }.console-body { min-height:620px; }.transcript-panel { top:auto; bottom:92px; height:42%; width:100%; background:rgba(7,10,9,.92); }.orbital-field { width:280px; transform:translateY(-18%); }.call-dock { position:fixed; bottom:0; left:0; right:0; padding:10px; }.call-button { min-width:145px; }.settings-deck { padding:20px; }.voice-options { grid-template-columns:repeat(3,1fr); } }
</style>
