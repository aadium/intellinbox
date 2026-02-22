<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchEmails, type Email } from './services/api'

const emails = ref<Email[]>([])
const loading = ref(true)

const loadData = async () => {
  try {
    loading.value = true
    emails.value = await fetchEmails()
  } catch (err) {
    console.error("Failed to fetch emails:", err)
  } finally {
    loading.value = false
  }
}

const getPriorityClass = (score: number) => {
  if (score > 0.8) return 'bg-red-900 text-red-200 border-red-700'
  if (score > 0.4) return 'bg-yellow-900 text-yellow-200 border-yellow-700'
  return 'bg-green-900 text-green-200 border-green-700'
}

const getStatusClass = (status: string) => {
  if (status === 'completed') return 'text-green-500'
  if (status === 'processing') return 'text-blue-500'
  if (status === 'pending') return 'text-yellow-500'
  if (status === 'failed') return 'text-red-500'
  return 'text-gray-500'
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('en-IN', { 
    day: '2-digit', month: 'short', year: 'numeric', 
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true 
  })
}

onMounted(loadData)
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-200 p-8 font-sans">
    <header class="max-w-5xl mx-auto mb-10 flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight text-white">Intell<span class="text-blue-500">Inbox</span></h1>
        <p class="text-slate-400">AI-Categorized Intelligence</p>
      </div>
      <button @click="loadData" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors font-medium">
        Refresh Feed
      </button>
    </header>

    <main class="max-w-5xl mx-auto">
      <div v-if="loading" class="text-center py-20 animate-pulse text-xl">Loading Intelligence...</div>
      
      <div v-else class="grid gap-4">
        <div v-for="email in emails" :key="email.id" 
             class="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-600 transition-all shadow-xl">
          
          <div class="flex justify-between items-start mb-4">
            <div>
              <span class="text-xs font-mono text-blue-400 uppercase tracking-widest">{{ email.sender }}</span>
              <h2 class="text-xl font-bold text-white mt-1">{{ email.subject }}</h2>
            </div>
            
            <div v-if="email.analysis" 
                 :class="['px-3 py-1 rounded-full text-xs font-bold border', getPriorityClass(email.analysis.priority_score)]">
              {{ (email.analysis.priority_score * 100).toFixed(0) }}% Priority
            </div>
          </div>

          <div v-if="email.analysis" class="bg-slate-800/50 rounded-lg p-4 mb-4 border-l-4 border-blue-500">
            <p class="text-sm italic text-slate-300">
              <span class="font-bold text-blue-400 not-italic uppercase text-[10px] mr-2">AI Summary:</span>
              "{{ email.analysis.summary }}"
            </p>
          </div>

          <div class="flex items-center gap-4 text-xs text-slate-500">
            <span :class="['px-2 py-1 rounded', email.analysis?.category === 'POSITIVE' ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200']">{{ email.analysis?.category || 'PENDING' }}</span>
            <span>Processed at {{ formatDate(email.analysis?.processed_at || '') }}</span>
            <span :class="getStatusClass(email.status)">Processing {{ email.status }}</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>