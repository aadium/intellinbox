<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { fetchEmails, fetchInboxes, type Email, type Inbox } from './services/api'
import EmailCard from './components/EmailCard.vue'
import InboxSidebar from './components/InboxSidebar.vue'

const emails = ref<Email[]>([])
const inboxes = ref<Inbox[]>([])
const loading = ref(true)
const activeTab = ref<'all' | number>('all')

const loadData = async (isSilent = false) => {
  try {
    if (!isSilent) loading.value = true
    const [emailData, inboxData] = await Promise.all([fetchEmails(), fetchInboxes()])
    emails.value = emailData
    inboxes.value = inboxData
  } finally {
    loading.value = false
  }
}

// Filter emails based on selected tab
const filteredEmails = computed(() => {
  // Debugging: Open your browser console (F12) to see this output
  console.log('Active Tab:', activeTab.value, 'Type:', typeof activeTab.value);
  if (emails.value.length > 0) {
    console.log('Example Email Inbox ID:', emails.value[0].inbox_id, 'Type:', typeof emails.value[0].inbox_id);
  }

  if (activeTab.value === 'all') return emails.value;
  
  // Force both to numbers to ensure the comparison works
  return emails.value.filter(e => Number(e.inbox_id) === Number(activeTab.value));
})

const handleDeletedLocal = (deletedId: number) => {
  emails.value = emails.value.filter(email => email.id !== deletedId)
}

let pollTimer: number | null = null

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
  <div class="flex h-screen bg-slate-950 text-slate-200 overflow-hidden">
    <InboxSidebar :inboxes="inboxes" @refresh="loadData(true)" />

    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="p-8 pb-4">
        <div class="flex justify-between items-center mb-8">
          <h1 class="text-3xl font-bold tracking-tight">IntellInbox</h1>
          <button @click="loadData(false)" class="bg-slate-900 border border-slate-800 hover:border-blue-500 transition-all px-4 py-2 rounded-lg text-sm">
            Manual Refresh
          </button>
        </div>

        <div class="flex gap-2 border-b border-slate-800">
          <button @click="activeTab = 'all'" 
                  :class="['px-6 py-3 text-sm font-medium transition-all', activeTab === 'all' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-slate-500 hover:text-slate-300']">
            All Inboxes
          </button>
          <button v-for="inbox in inboxes" :key="inbox.id" 
                  @click="activeTab = inbox.id"
                  :class="['px-6 py-3 text-sm font-medium transition-all', activeTab === inbox.id ? 'border-b-2 border-blue-500 text-blue-400' : 'text-slate-500 hover:text-slate-300']">
            {{ inbox.email_address }}
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto p-4 md:p-8 pt-4">
        <div v-if="loading && emails.length === 0" class="flex items-center justify-center h-full">
           <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>

        <div class="grid gap-6 max-w-full mx-auto w-full">
          <EmailCard 
            v-for="email in filteredEmails" 
            :key="email.id" 
            :email="email" 
            class="w-full wrap-break-word"
            @emailDeleted="loadData(true)"
          />
          <div v-if="!loading && filteredEmails.length === 0" class="text-center py-20 border-2 border-dashed border-slate-900 rounded-3xl">
             <p class="text-slate-600 font-medium">No emails found for this view.</p>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>