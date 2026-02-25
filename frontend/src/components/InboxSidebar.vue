<script setup lang="ts">
import { ref } from 'vue'
import { PlusIcon, TrashIcon, ArrowPathIcon, PowerIcon } from '@heroicons/vue/24/outline'
import { createInbox, deleteInbox, updateInboxStatus, triggerSyncAll, type Inbox, syncInbox, resetInbox } from '../services/api'

const props = defineProps<{ inboxes: Inbox[] }>()
const emit = defineEmits(['refresh'])

const showAddDialog = ref(false)
const showResetDialog = ref(false)
const selectedInbox = ref<Inbox | null>(null)
const resetSyncDays = ref(30)
const newInbox = ref({ email_address: '', password: '', imap_server: 'imap.gmail.com', is_active: true, sync_days: 30 })

const formatTime = (dateString?: string) => {
    if (!dateString) return 'Never synced'
    const date = new Date(dateString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const handleAdd = async () => {
    await createInbox(newInbox.value)
    showAddDialog.value = false
    newInbox.value = { email_address: '', password: '', imap_server: 'imap.gmail.com', is_active: true, sync_days: 30 }
    emit('refresh')
}

const toggleStatus = async (inbox: Inbox) => {
    await updateInboxStatus(inbox.id, !inbox.is_active)
    emit('refresh')
}

const removeInbox = async (id: number) => {
    if (confirm("Delete this inbox and all its emails?")) {
        await deleteInbox(id)
        emit('refresh')
    }
}

const syncAll = async () => {
    await triggerSyncAll()
    alert("Sync started!")
}
</script>

<template>
    <div class="w-82 border-r border-slate-800 flex flex-col h-full bg-slate-950">
        <div class="p-6 border-b border-slate-800 flex justify-between items-center">
            <h2 class="text-xl font-bold text-white">Inboxes</h2>
            <button @click="syncAll" class="text-slate-400 hover:text-blue-400" title="Sync All">
                <ArrowPathIcon class="h-5 w-5" />
            </button>
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-2">
            <div v-for="inbox in inboxes" :key="inbox.id"
                class="group flex items-center justify-between p-3 rounded-lg bg-slate-900/70 transition-colors">
                <div class="flex items-center gap-3">
                    <input type="checkbox" :checked="inbox.is_active" @change="toggleStatus(inbox)"
                        class="rounded border-slate-700 bg-slate-800 text-blue-600 focus:ring-blue-500" />
                    <div class="flex flex-col">
                        <span class="text-sm font-medium text-slate-200 truncate w-32">
                            {{ inbox.email_address }}
                        </span>
                        <div class="flex items-center gap-2">
                            <span class="text-[10px] text-slate-500 uppercase">{{ inbox.imap_server }}</span>
                            <span class="text-[10px] text-slate-400">•</span>
                            <span class="text-[10px] text-blue-400/80 italic">
                                {{ formatTime(inbox.last_synced) }}
                            </span>
                        </div>
                    </div>
                </div>
                <button @click="showResetDialog = true; selectedInbox = inbox"
                    class="opacity-100 text-red-300 hover:text-red-400 transition-opacity">
                    <PowerIcon class="h-4 w-4" />
                </button>
                <button @click="syncInbox(inbox.id)"
                    class="opacity-100 text-blue-300 hover:text-blue-500 transition-opacity">
                    <ArrowPathIcon class="h-4 w-4" />
                </button>
                <button @click="removeInbox(inbox.id)"
                    class="opacity-100 text-red-400 hover:text-red-500 transition-opacity">
                    <TrashIcon class="h-4 w-4" />
                </button>
            </div>
        </div>

        <button @click="showAddDialog = true"
            class="m-4 flex items-center justify-center gap-2 bg-slate-900 border border-slate-800 hover:border-blue-500 py-3 rounded-xl text-sm font-bold transition-all">
            <PlusIcon class="h-4 w-4" /> Add Inbox
        </button>

        <div v-if="showAddDialog"
            class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div class="bg-slate-900 border border-slate-800 p-8 rounded-2xl w-full max-w-md shadow-2xl">
                <h3 class="text-2xl font-bold mb-6 text-white">Add Monitored Inbox</h3>
                <div class="space-y-4">
                    <input v-model="newInbox.email_address" placeholder="Email Address"
                        class="w-full bg-slate-800 border-slate-700 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500" />
                    <span class="text-sm text-slate-500">For Gmail, generate an App Password</span>
                    <input v-model="newInbox.password" type="password" placeholder="Password"
                        class="w-full bg-slate-800 border-slate-700 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500" />
                    <span class="text-sm text-slate-500">Your IMAP server</span>
                    <input v-model="newInbox.imap_server" placeholder="IMAP Server"
                        class="w-full bg-slate-800 border-slate-700 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500" />
                    <select v-model="newInbox.sync_days"
                        class="w-full bg-slate-800 border-slate-700 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500">
                        <option :value=1>Sync last 1 day</option>
                        <option :value=7>Sync last 1 week</option>
                        <option :value=30>Sync last 1 month</option>
                        <option :value=90>Sync last 3 months</option>
                    </select>
                </div>
                <div class="flex gap-4 mt-8">
                    <button @click="showAddDialog = false"
                        class="flex-1 text-slate-400 hover:text-white">Cancel</button>
                    <button @click="handleAdd" class="flex-1 bg-blue-600 py-3 rounded-lg font-bold">Connect</button>
                </div>
            </div>
        </div>
        <div v-if="showResetDialog"
            class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div
                class="bg-slate-900 border border-slate-700 p-8 rounded-2xl w-full max-w-md shadow-2xl transform transition-all scale-100">

                <div class="flex items-center gap-3 mb-4">
                    <div class="p-2 bg-red-500/10 rounded-lg">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                            class="text-red-500">
                            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                            <path d="M3 3v5h5" />
                        </svg>
                    </div>
                    <h3 class="text-2xl font-bold text-white">Reset Inbox</h3>
                </div>

                <p class="text-slate-400 mb-6 leading-relaxed">
                    This will <span class="text-red-400 font-semibold">permanently delete</span> all emails in this
                    inbox and restart the analysis from the chosen date.
                </p>

                <div class="mb-8">
                    <label class="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Sync
                        Lookback</label>
                    <select v-model="resetSyncDays"
                        class="w-full bg-slate-800 border-slate-700 text-white rounded-lg p-3 outline-none focus:ring-2 focus:ring-red-500 transition-all cursor-pointer">
                        <option :value=1>Sync last 1 day</option>
                        <option :value=7>Sync last 1 week</option>
                        <option :value=30>Sync last 1 month</option>
                        <option :value=90>Sync last 3 months</option>
                    </select>
                </div>

                <div class="flex items-center gap-4">
                    <button @click="showResetDialog = false; selectedInbox = null"
                        class="flex-1 text-slate-400 hover:text-white font-medium transition-colors">
                        Cancel
                    </button>
                    <button @click="resetInbox(selectedInbox!.id, resetSyncDays).then(() => { showResetDialog = false; selectedInbox = null; emit('refresh') })"
                        class="flex-1 bg-red-600 hover:bg-red-500 text-white py-3 rounded-xl font-bold shadow-lg shadow-red-900/20 transition-all active:scale-95">
                        Confirm Reset
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>