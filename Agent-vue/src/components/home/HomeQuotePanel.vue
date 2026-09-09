<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import presetQuotes from '@/content/home-quotes.json'
import { initialQuoteIndex, nextQuoteIndex } from '@/home/home-quotes'
import { saveHomeQuotes, type HomeQuote } from '@/api/user-profile'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
const quotes = computed(() => workspace.profile?.home_quotes ?? presetQuotes)
const quoteIndex = ref(initialQuoteIndex(quotes.value.length))
const currentQuote = computed(() => quotes.value[quoteIndex.value] ?? quotes.value[0])
const dialog = ref<HTMLDialogElement>()
const drafts = ref<HomeQuote[]>([])
const saving = ref(false)
const error = ref('')
let timer: ReturnType<typeof setInterval> | undefined

function stopRotation() {
  if (timer) clearInterval(timer)
  timer = undefined
}

function startRotation() {
  if (timer || document.hidden || dialog.value?.open) return
  timer = setInterval(() => {
    quoteIndex.value = nextQuoteIndex(quoteIndex.value, quotes.value.length)
  }, 10_000)
}

function onVisibilityChange() {
  if (document.hidden) stopRotation()
  else startRotation()
}

function openEditor() {
  drafts.value = quotes.value.map(quote => ({ ...quote }))
  error.value = ''
  stopRotation()
  dialog.value?.showModal()
}

async function save(restore = false) {
  if (saving.value) return
  error.value = ''
  const values = restore ? null : drafts.value.map(quote => ({
    text: quote.text.trim(), speaker: quote.speaker.trim(),
  }))
  if (values?.some(quote => !quote.text)) {
    error.value = '请填写每条格言的内容。'
    return
  }
  saving.value = true
  try {
    workspace.setProfile(await saveHomeQuotes(workspace.userId, values))
    dialog.value?.close()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '保存失败，请重试'
  } finally {
    saving.value = false
  }
}

watch(quotes, () => { quoteIndex.value = 0 })
onMounted(() => {
  startRotation()
  document.addEventListener('visibilitychange', onVisibilityChange)
})
onBeforeUnmount(() => {
  stopRotation()
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<template>
  <section class="home-quotes" aria-label="首页格言">
    <span class="quote-mark" aria-hidden="true">“</span>
    <Transition name="quote" mode="out-in">
      <blockquote :key="`${quoteIndex}:${currentQuote?.text}`">
        <p>{{ currentQuote?.text }}</p>
        <cite v-if="currentQuote?.speaker">— {{ currentQuote.speaker }}</cite>
      </blockquote>
    </Transition>
    <div class="quote-controls">
      <span class="quote-count">{{ quoteIndex + 1 }} / {{ quotes.length }}</span>
      <button type="button" @click="quoteIndex = nextQuoteIndex(quoteIndex, quotes.length)">换一句</button>
      <button type="button" @click="openEditor">自定义格言</button>
    </div>

    <dialog ref="dialog" class="quote-dialog" aria-labelledby="quote-editor-title"
      @close="startRotation" @cancel="saving && $event.preventDefault()">
      <form @submit.prevent="save()">
        <header>
          <div>
            <h2 id="quote-editor-title">首页格言</h2>
            <p>按列表顺序轮播，保存到当前本地资料。</p>
          </div>
          <button type="button" :disabled="saving" aria-label="关闭格言编辑" @click="dialog?.close()">关闭</button>
        </header>
        <div class="quote-scroll">
          <fieldset :disabled="saving" class="quote-fields">
            <div v-for="(quote, index) in drafts" :key="index" class="quote-entry">
              <div class="entry-heading">
                <span>格言 {{ index + 1 }}</span>
                <button type="button" :disabled="drafts.length === 1" :aria-label="`删除格言 ${index + 1}`"
                  @click="drafts.splice(index, 1)">删除</button>
              </div>
              <label>
                <span>内容</span>
                <textarea v-model="quote.text" required maxlength="1000" rows="3" :aria-label="`格言 ${index + 1} 内容`" />
              </label>
              <label>
                <span>署名（选填）</span>
                <input v-model="quote.speaker" maxlength="100" :aria-label="`格言 ${index + 1} 署名`" />
              </label>
            </div>
            <button type="button" class="add-quote" :disabled="drafts.length >= 100"
              @click="drafts.push({ text: '', speaker: '' })">添加格言</button>
          </fieldset>
        </div>
        <p v-if="error" class="quote-error" role="alert">{{ error }}</p>
        <footer>
          <button type="button" :disabled="saving" @click="save(true)">恢复预置格言</button>
          <div>
            <button type="button" :disabled="saving" @click="dialog?.close()">取消</button>
            <button class="save-quotes" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存格言' }}</button>
          </div>
        </footer>
      </form>
    </dialog>
  </section>
</template>

<style scoped>
.home-quotes { position: relative; min-width: 0; }
.quote-mark { position: absolute; right: 0; top: -26px; color: #cbc6ba; font: 100px/1 'Playfair Display', serif; pointer-events: none; }
blockquote { position: relative; min-height: 75px; padding-right: 38px; }
blockquote p { max-width: 480px; max-height: 220px; overflow: auto; overflow-wrap: anywhere; font: 600 clamp(16px,1.7vw,24px)/1.5 'Playfair Display', serif; letter-spacing: -.02em; }
cite { display: block; margin-top: 12px; color: #77736b; font: 11px 'DM Mono', monospace; font-style: normal; overflow-wrap: anywhere; }
.quote-controls { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; margin-top: 12px; }
.quote-count { margin-right: auto; color: #77736b; font: 11px 'DM Mono', monospace; }
button { border: 0; background: transparent; color: inherit; cursor: pointer; font: inherit; font-size: 13px; min-height: 32px; padding: 6px 0; }
button:hover { text-decoration: underline; text-underline-offset: 4px; }
button:disabled { opacity: .45; cursor: default; }
button:focus-visible { outline: 2px solid #667b11; outline-offset: 3px; }
.quote-dialog { margin: auto; width: min(680px, calc(100vw - 28px)); max-height: 85dvh; border: 1px solid #12120f; padding: 0; color: #12120f; background: #e8e4da; box-shadow: 12px 12px 0 rgba(18,18,15,.2); }
.quote-dialog::backdrop { background: rgba(18,18,15,.55); }
form { display: flex; flex-direction: column; max-height: 85dvh; }
header, footer { padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-shrink: 0; }
header { border-bottom: 1px solid #bbb6aa; }
h2 { font-size: 24px; }
header p { color: #6e6a62; margin-top: 6px; font-size: 13px; }
.quote-scroll { min-height: 0; overflow-y: auto; }
.quote-fields { margin: 0; padding: 20px 24px; border: 0; }
.quote-entry { display: grid; gap: 12px; padding-bottom: 20px; margin-bottom: 18px; border-bottom: 1px solid #bbb6aa; }
.entry-heading { display: flex; justify-content: space-between; align-items: center; font-size: 14px; font-weight: 600; }
label { display: grid; gap: 6px; font-size: 12px; color: #6e6a62; }
input, textarea { box-sizing: border-box; width: 100%; border: 1px solid #aaa59a; padding: 10px; color: #12120f; background: #f5f2ea; font: 14px/1.6 Manrope, sans-serif; }
textarea { resize: vertical; min-height: 90px; }
.add-quote { border: 1px dashed #77736b; width: 100%; }
footer { border-top: 1px solid #bbb6aa; flex-wrap: wrap; }
footer > div { display: flex; gap: 18px; margin-left: auto; }
.save-quotes { padding-inline: 16px; background: #d9ff36; border: 1px solid #12120f; }
.quote-error { margin: 0 24px 12px; color: #a32721; font-size: 13px; }
.quote-enter-active, .quote-leave-active { transition: opacity .25s, transform .25s; }
.quote-enter-from { opacity: 0; transform: translateY(6px); }
.quote-leave-to { opacity: 0; transform: translateY(-6px); }
@media (prefers-reduced-motion: reduce) { .quote-enter-active, .quote-leave-active { transition: none; } }
</style>
