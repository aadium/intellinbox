<script setup lang="ts">
import { ref } from 'vue'
import { PlusIcon, TrashIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import { createInbox, deleteInbox, updateInboxStatus, triggerSyncAll, type Inbox } from '../services/api'

const props = defineProps<{ inboxes: Inbox[] }>()
const emit = defineEmits(['refresh'])

const showAddDialog = ref(false)
const newInbox = ref({ email_address: '', password: '', imap_server: 'imap.gmail.com', is_active: true })

const formatTime = (dateString?: string) => {
    if (!dateString) return 'Never synced'
    const date = new Date(dateString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const handleAdd = async () => {
    await createInbox(newInbox.value)
    showAddDialog.value = false
    newInbox.value = { email_address: '', password: '', imap_server: 'imap.gmail.com', is_active: true }
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
    <div class="w-72 border-r border-slate-800 flex flex-col h-full bg-slate-950">
        <div class="p-6 border-b border-slate-800 flex justify-between items-center">
            <h2 class="text-xl font-bold text-white">Accounts</h2>
            <button @click="syncAll" class="text-slate-400 hover:text-blue-400" title="Sync All">
                <ArrowPathIcon class="h-5 w-5" />
            </button>
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-2">
            <div v-for="inbox in inboxes" :key="inbox.id"
                class="group flex items-center justify-between p-3 rounded-lg hover:bg-slate-900 transition-colors">
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
                <button @click="removeInbox(inbox.id)"
                    class="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-500 transition-opacity">
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
                    <input v-model="newInbox.password" type="password" placeholder="App Password"
                        class="w-full bg-slate-800 border-slate-700 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500" />
                    <input v-model="newInbox.imap_server" placeholder="IMAP Server"
                        class="w-full bg-slate-800 border-slate-700 rounded-lg p-3 outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div class="flex gap-4 mt-8">
                    <button @click="showAddDialog = false"
                        class="flex-1 text-slate-400 hover:text-white">Cancel</button>
                    <button @click="handleAdd" class="flex-1 bg-blue-600 py-3 rounded-lg font-bold">Connect</button>
                </div>
            </div>
        </div>
    </div>
</template>