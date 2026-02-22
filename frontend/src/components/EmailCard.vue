<script setup lang="ts">
import { TrashIcon } from '@heroicons/vue/24/outline';
import { deleteEmail, type Email } from '../services/api'

const props = defineProps<{
  email: Email
}>()

const emit = defineEmits<{
  (e: 'emailDeleted', id: number): void
}>()

const formatDate = (dateString: string) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString([], { 
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const handleDelete = async () => {
  if (!confirm("Are you sure you want to delete this?")) return;

  try {
    await deleteEmail(props.email.id);
    emit('emailDeleted', props.email.id);
  } catch (err) {
    console.error("Failed to delete email:", err);
    alert("Delete failed. Is the backend running?");
  }
}

const getPriorityClass = (score: number) => {
  if (score > 0.8) return 'bg-red-900 text-red-100 border-red-700'
  if (score > 0.4) return 'bg-yellow-900 text-yellow-100 border-yellow-700'
  return 'bg-green-900 text-green-100 border-green-700'
}

const getStatusClass = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed': return 'text-green-400 font-medium'
    case 'processing': return 'text-yellow-400 animate-pulse'
    case 'failed': return 'text-red-400'
    default: return 'text-slate-500'
  }
}
</script>

<template>
  <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-600 transition-all shadow-xl">
    
    <div class="flex justify-between items-start mb-4">
      <div>
        <span class="text-xs font-mono text-blue-400 uppercase tracking-widest">{{ email.sender }}</span>
        <h2 class="text-xl font-bold text-white mt-1">{{ email.subject }}</h2>
        <span class="flex items-center gap-4 text-xs text-slate-500 italic">
          Received: {{ formatDate(email.received_at || '') }}
        </span>
      </div>
      
      <div class="flex items-center gap-3">
        <button 
          @click.stop="handleDelete" 
          class="relative z-10 p-2 text-slate-500 hover:text-red-500 hover:bg-red-500/10 rounded-full transition-all cursor-pointer"
        >
          <TrashIcon class="h-5 w-5" />
        </button>

        <div v-if="email.analysis" 
             :class="['px-3 py-1 rounded-full text-xs font-bold border', getPriorityClass(email.analysis.priority_score)]">
          {{ (email.analysis.priority_score * 100).toFixed(0) }}% Priority
        </div>
      </div>
    </div>

    <div v-if="email.analysis" class="bg-slate-800/50 rounded-lg p-4 mb-4 border-l-4 border-blue-500">
      <p class="text-sm italic text-slate-300">
        <span class="font-bold text-blue-400 not-italic uppercase text-[10px] mr-2">AI Summary:</span>
        "{{ email.analysis.summary }}"
      </p>
    </div>

    <div v-if="email.body" class="bg-slate-800/30 rounded-lg p-4 mb-4 border border-slate-700/50">
      <p class="text-sm text-slate-400 line-clamp-3 hover:line-clamp-none transition-all cursor-pointer">
        <span class="font-bold text-slate-500 uppercase text-[10px] block mb-1">Full body:</span>
        {{ email.body }}
      </p>
    </div>

    <div class="flex items-center gap-4 text-xs text-slate-500">
      <span :class="[
        'px-2 py-1 rounded font-bold uppercase tracking-tighter', 
        email.analysis?.category === 'positive' ? 'bg-green-900 text-green-200' : 
        email.analysis?.category === 'negative' ? 'bg-red-900 text-red-200' : 
        email.analysis?.category === 'neutral' ? 'bg-blue-800 text-blue-200' : 
        'bg-slate-800 text-slate-200'
      ]">
        {{ email.analysis?.category || 'PENDING' }}
      </span>
      
      <span v-if="email.analysis">Processed: {{ formatDate(email.analysis?.processed_at || '') }}</span>
      <span class="ml-auto flex items-center gap-2">
        <span class="h-2 w-2 rounded-full" :class="email.status === 'completed' ? 'bg-green-500' : 'bg-yellow-500'"></span>
        <span :class="getStatusClass(email.status)">{{ email.status }}</span>
      </span>
    </div>
  </div>
</template>