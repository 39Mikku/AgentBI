<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppModeSwitcher from '@/components/AppModeSwitcher.vue'
import BrandMark from '@/components/brand/BrandMark.vue'
import WorkspaceRailToggle from '@/components/WorkspaceRailToggle.vue'
import { useWorkspaceRail } from '@/composables/useWorkspaceRail'
import { useAuthStore } from '@/stores/auth'
import * as api from '@/api/tests'
import * as providersApi from '@/api/providers'
import type { ProviderProfile } from '@/api/chat-types'
import type { AnswerSelection, AttemptDetail, TestMode, TestPreferences, TestSession, TestSummary } from '@/api/test-types'

const auth = useAuthStore()
const router = useRouter()
const { railCollapsed, toggleRail } = useWorkspaceRail()
const userId = computed(() => auth.email || 'local-user')
const history = ref<TestSummary[]>([])
const session = ref<TestSession | null>(null)
const attempt = ref<AttemptDetail | null>(null)
const loading = ref(false)
const analysisLoading = ref(false)
const saving = ref(false)
const error = ref('')
const view = ref<'create' | 'attempt'>('create')
const questionIndex = ref(0)
const mode = ref<TestMode>('knowledge')
const topic = ref('')
const requirements = ref('')
const questionCount = ref<5 | 10 | 15 | 20>(10)
const difficulty = ref<'beginner' | 'intermediate' | 'advanced'>('intermediate')
const providers = ref<ProviderProfile[]>([])
const prefs = ref<TestPreferences>({ user_id: '' })
const showModels = ref(false)
const modelSaved = ref('')

const questions = computed(() => attempt.value?.questionnaire.questions ?? [])
const currentQuestion = computed(() => questions.value[questionIndex.value])
const answerMap = computed(() => Object.fromEntries((attempt.value?.answers ?? []).map(a => [a.question_id, a.selected_option_id])))
const answered = computed(() => attempt.value?.answers.length ?? 0)
const canSubmit = computed(() => !!attempt.value && answered.value === questions.value.length && attempt.value.status === 'draft')
const generationModels = computed(() => providers.value.find(p => p.id === prefs.value.generation_provider_id)?.available_models ?? [])
const analysisModels = computed(() => providers.value.find(p => p.id === prefs.value.analysis_provider_id)?.available_models ?? [])
const resultSections = computed(() => {
  const a = attempt.value?.result?.analysis
  return [...(a?.mastered ?? []), ...(a?.weaknesses ?? []), ...(a?.recommendations ?? []), ...(a?.sections ?? [])]
})

function uid() { return crypto.randomUUID() }
function message(e: unknown) { return e instanceof Error ? e.message : '操作失败' }

async function refreshHistory() {
  history.value = (await api.listTests(userId.value)).items
}
async function loadSession(id: string) {
  loading.value = true; error.value = ''
  try {
    session.value = await api.getTest(id, userId.value)
    const active = session.value.attempts[0]
    if (active) {
      attempt.value = await api.getAttempt(active.id, userId.value)
      questionIndex.value = 0
      view.value = 'attempt'
    }
  } catch (e) { error.value = message(e) } finally { loading.value = false }
}
async function openAttempt(id: string) {
  loading.value = true; error.value = ''
  try { attempt.value = await api.getAttempt(id, userId.value); questionIndex.value = 0; view.value = 'attempt' }
  catch (e) { error.value = message(e) } finally { loading.value = false }
}
function newTest() { session.value = null; attempt.value = null; topic.value = ''; requirements.value = ''; view.value = 'create'; error.value = '' }

async function create() {
  if (!topic.value.trim()) return
  loading.value = true; error.value = ''
  const requestId = uid()
  try {
    const result = await api.createTest({ user_id: userId.value, request_id: requestId, mode: mode.value, topic: topic.value, requirements: requirements.value, question_count: questionCount.value, difficulty: mode.value === 'knowledge' ? difficulty.value : null })
    if ('state' in result) {
      for (let i = 0; i < 60; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        const state = await api.getGeneration(requestId, userId.value)
        if (state.state === 'failed') throw new Error(state.error_message || '题目生成失败')
        if (state.state === 'completed' && state.test_id) { await loadSession(state.test_id); break }
      }
    } else {
      session.value = result
      const first = result.attempts[0]
      if (first) attempt.value = await api.getAttempt(first.id, userId.value)
      view.value = 'attempt'
    }
    await refreshHistory()
  } catch (e) { error.value = message(e) } finally { loading.value = false }
}

async function choose(questionId: string, optionId: string) {
  if (!attempt.value || attempt.value.status !== 'draft') return
  const answers: AnswerSelection[] = [...attempt.value.answers.filter(a => a.question_id !== questionId), { question_id: questionId, selected_option_id: optionId }]
  attempt.value.answers = answers
  saving.value = true
  try {
    await api.saveAnswers(attempt.value.id, userId.value, answers)
    if (currentQuestion.value?.id === questionId && questionIndex.value < questions.value.length - 1)
      questionIndex.value += 1
  } catch (e) { error.value = message(e) } finally { saving.value = false }
}
async function submit() {
  if (!attempt.value || !canSubmit.value) return
  loading.value = true; analysisLoading.value = true; error.value = ''
  try { attempt.value = await api.submitAttempt(attempt.value.id, userId.value, attempt.value.answers); if (session.value) session.value = await api.getTest(session.value.id, userId.value); await refreshHistory() }
  catch (e) { error.value = message(e) } finally { loading.value = false; analysisLoading.value = false }
}
async function retry() {
  if (!attempt.value) return
  loading.value = true; analysisLoading.value = true
  try { attempt.value = await api.retryAnalysis(attempt.value.id, userId.value); if (session.value) session.value = await api.getTest(session.value.id, userId.value) } catch (e) { error.value = message(e) } finally { loading.value = false; analysisLoading.value = false }
}
async function retest() {
  if (!session.value) return
  loading.value = true
  try { attempt.value = await api.createAttempt(session.value.id, { user_id: userId.value, request_id: uid() }); session.value = await api.getTest(session.value.id, userId.value); questionIndex.value = 0; view.value = 'attempt'; await refreshHistory() }
  catch (e) { error.value = message(e) } finally { loading.value = false }
}
async function removeCurrent() {
  if (!session.value || !confirm(`删除测试「${session.value.title}」？`)) return
  try { await api.deleteTest(session.value.id, userId.value); await refreshHistory(); newTest() } catch (e) { error.value = message(e) }
}
async function saveModelSettings() {
  try {
    prefs.value.user_id = userId.value
    prefs.value = await api.savePreferences(prefs.value)
    modelSaved.value = `已生效 · ${prefs.value.generation_model} / ${prefs.value.analysis_model}`
  }
  catch (e) { error.value = message(e) }
}
function changeGenerationProvider() {
  const provider = providers.value.find(p => p.id === prefs.value.generation_provider_id)
  prefs.value.generation_model = provider?.default_model || provider?.available_models[0] || null
  modelSaved.value = ''
}
function changeAnalysisProvider() {
  const provider = providers.value.find(p => p.id === prefs.value.analysis_provider_id)
  prefs.value.analysis_model = provider?.default_model || provider?.available_models[0] || null
  modelSaved.value = ''
}

onMounted(async () => {
  try {
    ;[providers.value, prefs.value] = await Promise.all([providersApi.listProviders(), api.getPreferences(userId.value)])
    await refreshHistory()
  } catch (e) { error.value = message(e) }
})
</script>

<template>
  <main class="test-page" :class="{ 'rail-collapsed': railCollapsed }">
    <aside class="rail">
      <WorkspaceRailToggle :collapsed="railCollapsed" @toggle="toggleRail" />
      <button class="brand" type="button" title="返回主页" @click="router.push('/home')"><BrandMark class="test-brand-mark" tone="inverse" /><span>AGENTBI</span><b>/ TEST</b></button>
      <AppModeSwitcher active="test" :collapsed="railCollapsed" />
      <button class="new-test" title="新建测试" @click="newTest"><span>＋</span><b>NEW TEST</b></button>
      <div class="rail-label">HISTORY / {{ String(history.length).padStart(2, '0') }}</div>
      <div class="history">
        <button v-for="item in history" :key="item.id" :class="{ active: session?.id === item.id }" @click="loadSession(item.id)">
          <small>{{ item.mode === 'knowledge' ? 'KNOWLEDGE' : 'FUN' }} · {{ item.question_count }}</small>
          <strong>{{ item.title }}</strong><time>{{ new Date(item.updated_at).toLocaleDateString() }}</time>
        </button>
        <p v-if="!history.length">还没有测试记录</p>
      </div>
      <button class="model-entry" @click="showModels = !showModels"><span>MODEL ROUTES<small>{{ prefs.generation_model || '未配置' }} → {{ prefs.analysis_model || '未配置' }}</small></span><b>↗</b></button>
      <section v-if="showModels" class="model-panel">
        <label>出题提供商<select v-model="prefs.generation_provider_id" @change="changeGenerationProvider"><option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option></select></label>
        <label>出题模型<select v-model="prefs.generation_model" @change="modelSaved = ''"><option v-for="m in generationModels" :key="m">{{ m }}</option></select></label>
        <label>分析提供商<select v-model="prefs.analysis_provider_id" @change="changeAnalysisProvider"><option v-for="p in providers" :key="p.id" :value="p.id">{{ p.name }}</option></select></label>
        <label>分析模型<select v-model="prefs.analysis_model" @change="modelSaved = ''"><option v-for="m in analysisModels" :key="m">{{ m }}</option></select></label>
        <button @click="saveModelSettings">保存模型路由</button>
        <p v-if="modelSaved" class="model-saved">{{ modelSaved }}</p>
      </section>
    </aside>

    <section class="canvas">
      <header><div><span>EDITORIAL ASSESSMENT LAB</span><b>{{ auth.profile?.username || userId }}</b></div><div class="status"><i></i>{{ saving ? 'SAVING' : loading ? 'PROCESSING' : 'READY' }}</div></header>
      <div v-if="error" class="error">{{ error }} <button @click="error = ''">×</button></div>

      <section v-if="view === 'create'" class="create-sheet">
        <p class="eyebrow">NEW ASSESSMENT / 001</p>
        <h1>把主题交给模型，<br><em>把判断留给自己。</em></h1>
        <div class="mode-tabs"><button :class="{ active: mode === 'knowledge' }" @click="mode = 'knowledge'">知识测试 <small>有正确答案</small></button><button :class="{ active: mode === 'fun' }" @click="mode = 'fun'">趣味测试 <small>无标准答案</small></button></div>
        <label class="field"><span>01 / TOPIC</span><input v-model="topic" placeholder="例如：Python 异步编程 / 我像哪种动物" /></label>
        <label class="field"><span>02 / REQUIREMENTS · OPTIONAL</span><textarea v-model="requirements" rows="3" placeholder="可留空。也可以说明侧重点、风格或受众。"></textarea></label>
        <div class="config-row"><label><span>QUESTIONS</span><select v-model="questionCount"><option :value="5">05</option><option :value="10">10</option><option :value="15">15</option><option :value="20">20</option></select></label><label v-if="mode === 'knowledge'"><span>DIFFICULTY</span><select v-model="difficulty"><option value="beginner">入门</option><option value="intermediate">中等</option><option value="advanced">进阶</option></select></label></div>
        <button class="generate" :disabled="loading || !topic.trim()" @click="create"><span>{{ loading ? 'GENERATING…' : 'GENERATE TEST' }}</span><b>↗</b></button>
      </section>

      <section v-else-if="attempt" class="attempt-sheet">
        <div v-if="analysisLoading" class="analysis-overlay"><div class="analysis-orbit"><i></i><b>AI</b></div><p>ANALYSIS IN PROGRESS</p><h2>正在整理你的答案</h2><span>计分已经完成，模型正在生成结论与说明。请稍候，不要重复提交。</span><div class="analysis-track"><i></i></div></div>
        <header class="test-head"><div><p>{{ attempt.questionnaire.mode.toUpperCase() }} / {{ answered }} OF {{ questions.length }}</p><h1>{{ attempt.questionnaire.title }}</h1><span>{{ attempt.questionnaire.description }}</span></div><div class="head-actions"><button class="retest-action" @click="retest"><i>↻</i><span>RETEST<small>复用原题</small></span></button><button class="delete-action" aria-label="删除测试" title="删除测试" @click="removeCurrent">×</button></div></header>
        <nav v-if="session && session.attempts.length > 1" class="attempt-tabs" aria-label="作答版本">
          <button v-for="(item, index) in session.attempts" :key="item.id" :class="{ active: item.id === attempt.id }" @click="openAttempt(item.id)">#{{ session.attempts.length - index }} · {{ item.status }}<span v-if="item.score !== null && item.score !== undefined"> · {{ item.score }}</span></button>
        </nav>

        <template v-if="attempt.status === 'draft' && currentQuestion">
          <div class="progress"><i :style="{ width: `${(answered / questions.length) * 100}%` }"></i></div>
          <article class="question-card">
            <div class="question-no">{{ String(questionIndex + 1).padStart(2, '0') }}<small>/ {{ String(questions.length).padStart(2, '0') }}</small></div>
            <h2>{{ currentQuestion.prompt }}</h2>
            <div class="options"><button v-for="(option, index) in currentQuestion.options" :key="option.id" :class="{ selected: answerMap[currentQuestion.id] === option.id }" @click="choose(currentQuestion.id, option.id)"><b>{{ String.fromCharCode(65 + index) }}</b><span>{{ option.text }}</span><i></i></button></div>
          </article>
          <footer class="question-nav"><button :disabled="questionIndex === 0" @click="questionIndex--">← PREV</button><span>{{ answered }} 已回答 · {{ questions.length - answered }} 未回答</span><button v-if="questionIndex < questions.length - 1" @click="questionIndex++">NEXT →</button><button v-else class="submit" :disabled="!canSubmit || loading" @click="submit">提交并分析 ↗</button></footer>
        </template>

        <section v-else-if="attempt.status === 'completed' && attempt.result" class="result-sheet">
          <p class="eyebrow">FINAL REPORT / {{ attempt.questionnaire.mode.toUpperCase() }}</p>
          <div v-if="attempt.result.score !== undefined" class="score"><strong>{{ attempt.result.score }}</strong><span>/ 100<br>{{ attempt.result.correct_count }} / {{ attempt.result.question_count }} CORRECT</span></div>
          <h2>{{ attempt.result.analysis.title }}</h2><p class="summary">{{ attempt.result.analysis.summary }}</p>
          <div class="sections"><article v-for="section in resultSections" :key="section.heading"><small>ANALYSIS</small><h3>{{ section.heading }}</h3><p>{{ section.body }}</p></article></div>
          <div v-for="chart in attempt.result.analysis.charts" :key="chart.title" class="chart"><h3>{{ chart.title }}</h3><div v-for="item in chart.items" :key="item.label"><span>{{ item.label }}</span><i><b :style="{ width: `${(item.value / item.max_value) * 100}%` }"></b></i><em>{{ item.value }}</em></div></div>
          <details v-if="attempt.result.questions" class="review"><summary>查看逐题解析</summary><article v-for="(q, i) in attempt.result.questions" :key="q.id" :class="{ wrong: !q.is_correct }"><b>{{ i + 1 }}. {{ q.prompt }}</b><p>{{ q.is_correct ? '回答正确' : `回答错误 · 正确项 ${q.correct_option_id}` }}</p><span>{{ q.explanation }}</span></article></details>
        </section>
        <section v-else-if="attempt.status === 'failed'" class="failed"><b>ANALYSIS INTERRUPTED</b><h2>分析没有完成。</h2><p>{{ attempt.error_message }}</p><button @click="retry">RETRY ANALYSIS ↗</button></section>
        <section v-else class="loading-state"><i></i><h2>正在整理你的答案</h2><p>模型完成分析后，报告会出现在这里。</p></section>
      </section>
    </section>
  </main>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Manrope:wght@400;500;600;700&family=Playfair+Display:ital,wght@1,600&display=swap');
*{box-sizing:border-box}.test-page{--ink:#121313;--paper:#f1eee6;--blue:#3157e8;--coral:#ff674d;--acid:#d8ff38;min-height:100vh;display:grid;grid-template-columns:280px minmax(0,1fr);background:var(--ink);color:#efeee8;font-family:Manrope,sans-serif}.rail{height:100vh;position:sticky;top:0;display:flex;flex-direction:column;padding:25px 20px 18px;border-right:1px solid #343535;background:#171818}.brand{width:100%;border:0;background:transparent;color:inherit;cursor:pointer;display:flex;align-items:center;gap:7px;margin-bottom:22px;font:600 11px 'DM Mono';letter-spacing:.12em}.brand:focus-visible{outline:1px solid var(--acid);outline-offset:4px}.brand i{width:17px;height:17px;border:1px solid var(--acid);box-shadow:4px 4px 0 -2px var(--acid)}.brand b{color:#666;font-weight:400}.new-test{height:48px;margin:20px 0;border:1px solid var(--acid);background:var(--acid);color:#111;display:flex;align-items:center;justify-content:space-between;padding:0 14px;font:500 9px 'DM Mono';letter-spacing:.13em;cursor:pointer}.new-test span{font-size:20px}.rail-label{padding:12px 4px;border-bottom:1px solid #313232;color:#686a67;font:8px 'DM Mono';letter-spacing:.15em}.history{min-height:0;flex:1;overflow:auto}.history>button{width:100%;display:grid;gap:6px;padding:15px 10px;border:0;border-bottom:1px solid #292a2a;background:transparent;color:#aaa;text-align:left;cursor:pointer}.history>button.active{background:#242723;color:white;border-left:3px solid var(--acid)}.history small,.history time{color:#656863;font:7px 'DM Mono';letter-spacing:.08em}.history strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}.history p{color:#555;font-size:11px;text-align:center;margin-top:30px}.model-entry{border:0;border-top:1px solid #343535;background:transparent;color:#999;padding:15px 4px;display:flex;justify-content:space-between;font:8px 'DM Mono';letter-spacing:.13em;cursor:pointer}.model-panel{position:absolute;z-index:5;left:20px;bottom:60px;width:240px;padding:14px;background:#242525;border:1px solid #474943;box-shadow:0 15px 40px #000}.model-panel label{display:grid;gap:5px;margin:8px 0;color:#888;font:8px 'DM Mono'}.model-panel select{width:100%;background:#151616;color:#eee;border:1px solid #444;padding:8px;font-size:10px}.model-panel button{width:100%;padding:9px;background:var(--acid);border:0;font:9px 'DM Mono';cursor:pointer}.canvas{min-width:0;background:var(--paper);color:#171716}.canvas>header{height:65px;display:flex;justify-content:space-between;align-items:center;padding:0 clamp(24px,4vw,64px);border-bottom:1px solid #c7c4bb}.canvas>header div:first-child{display:grid;gap:4px}.canvas>header span{font:8px 'DM Mono';letter-spacing:.15em;color:#777}.canvas>header b{font-size:11px}.status{display:flex;align-items:center;gap:8px;color:#777;font:8px 'DM Mono';letter-spacing:.12em}.status i{width:6px;height:6px;background:var(--blue)}.error{margin:16px clamp(24px,4vw,64px) 0;padding:12px 15px;background:#ffddd5;color:#7d2618;font-size:12px}.error button{float:right;border:0;background:transparent}.create-sheet,.attempt-sheet{max-width:1160px;margin:auto;padding:clamp(35px,6vw,90px) clamp(24px,6vw,90px)}.eyebrow{color:var(--blue);font:9px 'DM Mono';letter-spacing:.16em}.create-sheet h1{margin:20px 0 48px;font:700 clamp(40px,6vw,79px)/.98 Manrope;letter-spacing:-.07em}.create-sheet h1 em{color:#827f76;font:600 italic .8em 'Playfair Display'}.mode-tabs{display:grid;grid-template-columns:1fr 1fr;border:1px solid #aaa79e}.mode-tabs button{padding:18px;border:0;background:transparent;display:grid;gap:5px;text-align:left;font-weight:700;cursor:pointer}.mode-tabs button+button{border-left:1px solid #aaa79e}.mode-tabs button.active{background:var(--blue);color:white}.mode-tabs button:last-child.active{background:var(--coral);color:#111}.mode-tabs small{font:7px 'DM Mono';opacity:.65}.field{display:grid;gap:10px;margin-top:32px}.field>span,.config-row span{font:8px 'DM Mono';letter-spacing:.14em;color:#777}.field input,.field textarea{width:100%;border:0;border-bottom:1px solid #8e8b83;background:transparent;padding:12px 0;outline:0;color:#171716;font:500 19px Manrope;resize:vertical}.field textarea{font-size:14px}.config-row{display:flex;gap:40px;margin:28px 0}.config-row label{display:grid;gap:8px}.config-row select{min-width:150px;padding:11px;border:1px solid #aaa79e;background:transparent}.generate{width:100%;height:62px;border:0;background:#171716;color:white;padding:0 22px;display:flex;justify-content:space-between;align-items:center;font:500 10px 'DM Mono';letter-spacing:.14em;cursor:pointer}.generate:hover:not(:disabled){background:var(--blue)}.generate:disabled{opacity:.35}.generate b{font-size:20px}.test-head{display:flex;justify-content:space-between;gap:25px;border-bottom:1px solid #b9b6ad;padding-bottom:26px}.test-head p{color:var(--blue);font:8px 'DM Mono';letter-spacing:.14em}.test-head h1{margin:8px 0;font-size:clamp(28px,4vw,52px);letter-spacing:-.055em}.test-head span{color:#777;font-size:12px}.head-actions{display:flex;gap:6px}.head-actions button{height:34px;border:1px solid #aaa79e;background:transparent;font:8px 'DM Mono';cursor:pointer}.progress{height:3px;margin:26px 0;background:#d7d3c9}.progress i{display:block;height:100%;background:var(--blue)}.question-card{position:relative;padding:35px 0}.question-no{font:600 clamp(64px,10vw,130px)/.75 Manrope;letter-spacing:-.09em;color:#dad6cc}.question-no small{font:9px 'DM Mono';color:#777;letter-spacing:0}.question-card h2{max-width:800px;margin:30px 0;font-size:clamp(24px,3.1vw,42px);line-height:1.2;letter-spacing:-.035em}.options{display:grid;grid-template-columns:1fr 1fr;gap:10px}.options button{min-height:70px;display:grid;grid-template-columns:38px 1fr 12px;align-items:center;gap:12px;border:1px solid #b9b6ad;background:transparent;text-align:left;padding:12px;cursor:pointer}.options button:hover{border-color:var(--blue)}.options button.selected{background:var(--blue);color:white;border-color:var(--blue)}.options button b{font:600 12px 'DM Mono'}.options button span{font-size:13px}.options button i{width:9px;height:9px;border:1px solid currentColor;border-radius:50%}.options button.selected i{background:white}.question-nav{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding-top:25px;border-top:1px solid #b9b6ad}.question-nav button{justify-self:start;border:0;background:transparent;font:9px 'DM Mono';cursor:pointer}.question-nav button:last-child{justify-self:end}.question-nav span{color:#777;font:8px 'DM Mono'}.question-nav .submit{background:#171716;color:white;padding:14px 18px}.score{display:flex;align-items:flex-end;gap:20px;margin:40px 0}.score strong{font:700 clamp(80px,13vw,170px)/.7 Manrope;letter-spacing:-.1em}.score span{font:9px/1.7 'DM Mono';color:#777}.result-sheet>h2{font-size:clamp(35px,5vw,65px);letter-spacing:-.06em;margin:50px 0 10px}.summary{max-width:800px;font-size:18px;line-height:1.7}.sections{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:#b9b6ad;border:1px solid #b9b6ad;margin:35px 0}.sections article{padding:25px;background:var(--paper)}.sections small{color:var(--blue);font:7px 'DM Mono'}.sections h3{font-size:18px}.sections p{color:#555;line-height:1.7;font-size:13px}.chart{margin:30px 0;padding:25px;border:1px solid #b9b6ad}.chart>div{display:grid;grid-template-columns:120px 1fr 40px;align-items:center;gap:12px;margin:12px 0;font-size:11px}.chart i{height:8px;background:#d6d2c8}.chart b{display:block;height:100%;background:var(--blue)}.chart em{font:10px 'DM Mono'}.review{margin-top:35px;border-top:1px solid #aaa79e}.review summary{padding:20px 0;cursor:pointer;font:9px 'DM Mono'}.review article{padding:18px;border-top:1px solid #d5d1c7}.review article.wrong{border-left:4px solid var(--coral);padding-left:15px}.review p,.review span{font-size:12px;color:#666}.failed,.loading-state{min-height:500px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}.failed b{color:var(--coral);font:8px 'DM Mono'}.failed h2,.loading-state h2{font-size:45px}.failed button{margin-top:20px;padding:15px 20px;border:0;background:var(--coral);font:9px 'DM Mono'}.loading-state i{width:42px;height:42px;border:2px solid #ccc;border-top-color:var(--blue);border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.model-entry>span{min-width:0;display:grid;gap:5px;text-align:left}.model-entry small{max-width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#5f625d;font:7px 'DM Mono';text-transform:none}.model-entry b{font-size:13px}.model-saved{margin:9px 0 0;padding:8px;border-left:2px solid var(--acid);background:#181917;color:var(--acid);font:7px/1.5 'DM Mono'}.analysis-overlay{position:fixed;z-index:30;inset:0 0 0 280px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:30px;background:rgba(241,238,230,.94);backdrop-filter:blur(12px);text-align:center}.analysis-orbit{position:relative;width:112px;height:112px;display:grid;place-items:center;border:1px solid #aaa79e;transform:rotate(45deg)}.analysis-orbit:before,.analysis-orbit:after{content:'';position:absolute;inset:-14px;border:1px solid rgba(49,87,232,.22)}.analysis-orbit:after{inset:-29px;border-style:dashed;animation:spin 7s linear infinite}.analysis-orbit i{position:absolute;width:11px;height:11px;right:-6px;top:calc(50% - 5px);background:var(--blue)}.analysis-orbit b{transform:rotate(-45deg);font:700 24px Manrope}.analysis-overlay>p{margin:54px 0 10px;color:var(--blue);font:8px 'DM Mono';letter-spacing:.18em}.analysis-overlay h2{margin:0;font-size:clamp(36px,5vw,65px);letter-spacing:-.06em}.analysis-overlay>span{max-width:520px;margin-top:14px;color:#777;font-size:12px;line-height:1.7}.analysis-track{width:min(420px,75vw);height:2px;margin-top:34px;overflow:hidden;background:#d0ccc2}.analysis-track i{display:block;width:35%;height:100%;background:var(--blue);animation:analysisScan 1.35s ease-in-out infinite}@keyframes analysisScan{from{transform:translateX(-120%)}to{transform:translateX(390%)}}.head-actions{align-items:flex-start}.head-actions .retest-action{height:48px;display:flex;align-items:center;gap:10px;padding:0 14px;border-color:#88857d}.retest-action i{font:normal 19px 'DM Mono';transition:transform .25s}.retest-action:hover i{transform:rotate(-160deg)}.retest-action span{display:grid;text-align:left;color:#222;font:600 8px 'DM Mono';letter-spacing:.1em}.retest-action small{margin-top:3px;color:#8a877f;font:7px Manrope;letter-spacing:0}.head-actions .delete-action{width:48px;height:48px;border-color:transparent;background:#e4e0d6;color:#817d74;font:300 21px 'DM Mono'}.head-actions .delete-action:hover{background:var(--coral);color:#111}.attempt-tabs{display:flex;gap:6px;overflow-x:auto;padding:12px 0;border-bottom:1px solid #d1cdc3}.attempt-tabs button{flex:0 0 auto;padding:7px 10px;border:1px solid #bbb7ad;background:transparent;color:#777;font:8px 'DM Mono';text-transform:uppercase;cursor:pointer}.attempt-tabs button.active{background:#171716;color:white;border-color:#171716}
.test-page{transition:grid-template-columns .28s cubic-bezier(.2,.8,.2,1)}.rail{transition:padding .28s cubic-bezier(.2,.8,.2,1)}.test-brand-mark{width:18px;height:18px;flex:0 0 auto}.new-test b{font:inherit;font-weight:500}.rail :deep(.rail-toggle){background:#171818;color:var(--acid);border-color:#464944}.rail :deep(.rail-toggle:hover){background:var(--acid);color:#111}@media(min-width:821px){.test-page.rail-collapsed{grid-template-columns:72px minmax(0,1fr)}.rail-collapsed .rail{padding-inline:10px}.rail-collapsed .brand{justify-content:center}.rail-collapsed .brand>span,.rail-collapsed .brand>b,.rail-collapsed .rail-label,.rail-collapsed .history,.rail-collapsed .model-entry,.rail-collapsed .model-panel{display:none}.rail-collapsed .new-test{display:grid;place-items:center;padding:0}.rail-collapsed .new-test span{font-size:22px}.rail-collapsed .new-test b{display:none}.rail-collapsed .analysis-overlay{left:72px}}@media(max-width:800px){.test-page{grid-template-columns:1fr}.rail{position:relative;height:auto;min-height:0}.history{max-height:180px}.canvas>header{display:none}.create-sheet,.attempt-sheet{padding:35px 20px}.options,.sections{grid-template-columns:1fr}.question-nav{grid-template-columns:1fr 1fr}.question-nav span{display:none}.test-head{flex-direction:column}.model-panel{position:fixed;left:20px;bottom:20px}.analysis-overlay{inset:0}.head-actions{width:100%}.head-actions .retest-action{flex:1;justify-content:center}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
