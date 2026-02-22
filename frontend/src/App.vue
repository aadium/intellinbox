<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchEmails, type Email } from './services/api'
import EmailCard from './components/EmailCard.vue'

const emails = ref<Email[]>([])
const loading = ref(true)
let pollTimer: number | null = null

const loadData = async (isSilent = false) => {
  try {
    if (!isSilent) loading.value = true
    
    const data = await fetchEmails()
    emails.value = data
  } catch (err) {
    console.error("Failed to fetch emails:", err)
  } finally {
    loading.value = false
  }
}

const handleDeletedLocal = (deletedId: number) => {
  emails.value = emails.value.filter(email => email.id !== deletedId)
}

// The Polling Logic
const startPolling = () => {
  pollTimer = setInterval(() => {
    const needsUpdate = emails.value.some(e => e.status !== 'completed' && e.status !== 'failed')
    loadData(true)
  }, 5000)
}

onMounted(async () => {
  await loadData()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="min-h-screen bg-slate-950 p-8 text-slate-200">
    <div class="max-w-5xl mx-auto">
      <div class="flex justify-between items-center mb-10">
        <div class="flex items-center gap-4">
          <h1 class="text-3xl font-bold">IntellInbox</h1>
          <div v-if="!loading" class="flex items-center gap-2 text-xs text-slate-500 bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            Live Sync
          </div>
        </div>
        <button @click="loadData(false)" class="bg-blue-600 hover:bg-blue-700 transition-colors px-4 py-2 rounded font-medium">
          Refresh
        </button>
      </div>

      <div v-if="loading && emails.length === 0" class="flex flex-col items-center justify-center py-20 text-slate-500">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
        <p>Connecting to Inbox...</p>
      </div>

      <div class="grid gap-6">
        <EmailCard 
          v-for="email in emails" 
          :key="email.id" 
          :email="email" 
          @emailDeleted="handleDeletedLocal"
        />
        
        <div v-if="!loading && emails.length === 0" class="text-center py-20 border-2 border-dashed border-slate-800 rounded-xl">
          <p class="text-slate-500">Your inbox is empty. Try copy-pasting an email or syncing.</p>
        </div>
      </div>
    </div>
  </div>
</template>