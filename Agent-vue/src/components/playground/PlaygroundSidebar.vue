<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import AppModeSwitcher from '@/components/AppModeSwitcher.vue'
import { assetContentUrl } from '@/utils/chat-attachments'
import { usePlaygroundStore } from '@/stores/playground'


const props = defineProps<{ userId: string; collapsed?: boolean }>()
const emit = defineEmits<{ toggle: [] }>()
const store = usePlaygroundStore()
const router = useRouter()
const avatar = computed(() =>
  store.activeProfile?.avatar_attachment_id
    ? assetContentUrl(store.activeProfile.avatar_attachment_id, props.userId)
    : '',
)

async function rename(id: string, current: string) {
  const title = window.prompt('重命名会话', current)?.trim()
  if (title) await store.renameConversation(id, title, props.userId)
}

async function remove(id: string, title: string) {
  if (window.confirm(`删除会话「${title}」？此操作会删除该会话的所有消息版本和大总结。`)) {
    await store.removeConversation(id, props.userId)
  }
}
</script>

<template>
  <aside class="playground-sidebar" :class="{ collapsed }">
    <header class="rail-brand"><button class="mark" title="返回今日主页" @click="router.push('/home')"><i></i><span>AGENTBI</span></button><button class="collapse" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="emit('toggle')">{{ collapsed ? '→' : '←' }}</button></header>
    <AppModeSwitcher active="playground" :collapsed="collapsed" />
    <template v-if="!collapsed">
      <div class="mode-tabs"><button :class="{ active: store.mode === 'character' }" @click="store.setMode('character', userId)">角色</button><button :class="{ active: store.mode === 'world' }" @click="store.setMode('world', userId)">世界</button></div>
      <label class="profile-select"><span class="profile-visual"><img v-if="avatar" :src="avatar" alt="" /><i v-else></i></span><div><small>CURRENT {{ store.mode.toUpperCase() }}</small><select :value="store.activeProfileId" @change="store.selectProfile(($event.target as HTMLSelectElement).value, userId)"><option v-if="!store.visibleProfiles.length" value="">尚无资料</option><option v-for="profile in store.visibleProfiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option></select></div></label>
      <button class="manage" @click="router.push({ path: '/playground/manage', query: { profile_id: store.activeProfileId || undefined } })"><span>管理角色、世界与提示词</span><b>↗</b></button>
      <div class="conversation-head"><span>STORY ARCHIVE</span><button :disabled="!store.activeProfile" @click="store.createConversation(userId)">＋ 新故事</button></div>
      <div class="conversation-list">
        <article v-for="conversation in store.conversations" :key="conversation.id" :class="{ active: conversation.id === store.activeConversationId }" @click="store.selectConversation(conversation.id, userId)">
          <i v-if="store.isConversationGenerating(conversation.id)" class="generating"></i><div><strong>{{ conversation.title }}</strong><small>{{ conversation.last_message_at ? new Date(conversation.last_message_at).toLocaleDateString() : 'NEW STORY' }}</small></div><nav><button title="重命名" @click.stop="rename(conversation.id, conversation.title)">✎</button><button title="删除" @click.stop="remove(conversation.id, conversation.title)">×</button></nav>
        </article>
        <div v-if="store.activeProfile && !store.conversations.length" class="conversation-empty"><b>NO STORY YET</b><span>创建一个会话，从开场消息进入故事。</span></div>
      </div>
    </template>
    <div v-else class="collapsed-stack"><button v-for="profile in store.visibleProfiles.slice(0, 4)" :key="profile.id" :class="{ active: profile.id === store.activeProfileId }" :title="profile.name" @click="store.selectProfile(profile.id, userId)"><img v-if="profile.avatar_attachment_id" :src="assetContentUrl(profile.avatar_attachment_id, userId)" alt="" /><i v-else></i></button><button class="add" title="管理角色与世界" @click="router.push('/playground/manage')">＋</button></div>
  </aside>
</template>

<style scoped>
.playground-sidebar{position:relative;z-index:12;display:flex;flex-direction:column;width:292px;height:100vh;border-right:1px solid #2f3531;background:#101310;color:#dfe4df;padding:16px;box-sizing:border-box;transition:width .25s ease}.playground-sidebar.collapsed{width:72px;padding:14px 10px}.rail-brand{display:flex;align-items:center;justify-content:space-between;height:35px;margin-bottom:14px}.rail-brand button{border:0;background:none;color:inherit;cursor:pointer}.mark{display:flex;align-items:center;gap:9px;padding:0;font:700 8px var(--font-mono);letter-spacing:.13em}.mark i{position:relative;width:16px;height:16px;border:1px solid #d7ff3f}.mark i:after{content:'';position:absolute;width:5px;height:5px;right:-4px;bottom:-4px;background:#d7ff3f}.collapse{color:#626a64!important;font:10px var(--font-mono)}.collapsed .mark span{display:none}.mode-tabs{display:grid;grid-template-columns:1fr 1fr;margin-top:15px;border-bottom:1px solid #303632}.mode-tabs button{height:37px;border:0;border-bottom:2px solid transparent;background:none;color:#626a64;font:7px var(--font-mono);cursor:pointer}.mode-tabs button.active{border-color:#d7ff3f;color:#e8ece7}.profile-select{display:grid;grid-template-columns:48px 1fr;gap:11px;align-items:center;margin-top:15px;padding:10px;border:1px solid #343a36;background:#171a18}.profile-visual{position:relative;width:46px;height:46px;overflow:hidden;border:1px solid #3d453f;background:#101310}.profile-visual img{width:100%;height:100%;object-fit:cover}.profile-visual i:before,.profile-visual i:after,.collapsed-stack i:before,.collapsed-stack i:after{content:'';position:absolute;border:1px solid #434b45}.profile-visual i:before{width:17px;height:17px;left:14px;top:7px;border-radius:50%}.profile-visual i:after{width:27px;height:13px;left:9px;bottom:6px;border-radius:18px 18px 0 0}.profile-select>div{display:grid;gap:4px;min-width:0}.profile-select small{color:#687169;font:6px var(--font-mono);letter-spacing:.12em}.profile-select select{width:100%;border:0;outline:0;background:transparent;color:#e7ece7;font:700 10px var(--font-sans)}.profile-select option{background:#171a18}.manage{display:flex;justify-content:space-between;width:100%;border:0;border-bottom:1px solid #2d332f;background:none;color:#687169;padding:10px 1px;font:7px var(--font-mono);cursor:pointer}.manage:hover{color:#d7ff3f}.conversation-head{display:flex;align-items:center;justify-content:space-between;margin:19px 1px 8px}.conversation-head span{color:#535b55;font:6px var(--font-mono);letter-spacing:.14em}.conversation-head button{border:0;background:none;color:#d7ff3f;font:7px var(--font-mono);cursor:pointer}.conversation-list{min-height:0;overflow:auto;margin-inline:-6px;padding-inline:6px;scrollbar-width:thin;scrollbar-color:#39413b transparent}.conversation-list article{position:relative;display:grid;grid-template-columns:1fr auto;gap:8px;min-height:51px;padding:11px;border-left:2px solid transparent;color:#7a837c;cursor:pointer;transition:.15s}.conversation-list article:hover,.conversation-list article.active{background:#181c19;color:#e1e6e1}.conversation-list article.active{border-left-color:#d7ff3f}.conversation-list article>div{display:grid;gap:4px;min-width:0}.conversation-list strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:9px}.conversation-list small{color:#515953;font:6px var(--font-mono)}.conversation-list nav{display:none;align-items:center}.conversation-list article:hover nav{display:flex}.conversation-list nav button{border:0;background:none;color:#677069;padding:4px;font:8px var(--font-mono);cursor:pointer}.generating{position:absolute;left:-4px;top:21px;width:5px;height:5px;border-radius:50%;background:#d7ff3f;box-shadow:0 0 9px #d7ff3f;animation:pulse 1s infinite}.conversation-empty{display:grid;gap:6px;padding:35px 12px;color:#555d57;text-align:center}.conversation-empty b{font:7px var(--font-mono);letter-spacing:.13em}.conversation-empty span{font-size:8px;line-height:1.5}.collapsed-stack{display:grid;gap:9px;margin-top:17px}.collapsed-stack button{position:relative;width:42px;height:42px;margin:auto;overflow:hidden;border:1px solid #343b36;background:#171a18;color:#606861;cursor:pointer}.collapsed-stack button.active{border-color:#d7ff3f}.collapsed-stack img{width:100%;height:100%;object-fit:cover}.collapsed-stack i:before{width:13px;height:13px;left:13px;top:7px;border-radius:50%}.collapsed-stack i:after{width:23px;height:11px;left:8px;bottom:5px;border-radius:15px 15px 0 0}.collapsed-stack .add{font-size:15px}@keyframes pulse{50%{opacity:.3}}@media(max-width:760px){.playground-sidebar{position:absolute;left:0;top:0;transform:translateX(-100%)}.playground-sidebar.collapsed{transform:none;width:58px;padding-inline:7px}.collapsed-stack button{width:38px;height:38px}}
</style>
