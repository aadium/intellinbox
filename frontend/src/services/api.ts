import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface Analysis {
  category: string;
  priority_score: number;
  summary: string;
  processed_at: string;
}

export interface Email {
  id: number;
  inbox_id: number;
  sender: string;
  subject: string;
  body: string;
  status: string;
  received_at: string;
  analysis?: Analysis;
}

// Add these to your existing api.ts
export interface Inbox {
  id: number;
  email_address: string;
  imap_server: string;
  is_active: boolean;
  last_synced: string;
}

export const fetchInboxes = async (): Promise<Inbox[]> => {
  const response = await axios.get(`${API_BASE_URL}/inboxes/`);
  return response.data;
};

export const createInbox = async (data: any): Promise<Inbox> => {
  const response = await axios.post(`${API_BASE_URL}/inboxes/`, data);
  return response.data;
};

export const deleteInbox = async (id: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/inboxes/${id}`);
};

export const updateInboxStatus = async (id: number, isActive: boolean): Promise<Inbox> => {
  const response = await axios.patch(`${API_BASE_URL}/inboxes/${id}/status?is_active=${isActive}`);
  return response.data;
};

export const syncInbox = async (id: number): Promise<void> => {
  await axios.post(`${API_BASE_URL}/inboxes/${id}/sync`);
};

export const resetInbox = async (id: number, sync_days: number): Promise<void> => {
  await axios.post(`${API_BASE_URL}/inboxes/${id}/reset?sync_days=${sync_days}`);
}

export const triggerSyncAll = async (): Promise<void> => {
  await axios.post(`${API_BASE_URL}/inboxes/syncall`);
};

export const rerunAnalysis = async (emailId: number): Promise<void> => {
  await axios.patch(`${API_BASE_URL}/emails/${emailId}/analysis`);
};

export const fetchEmails = async (): Promise<Email[]> => {
  const response = await axios.get(`${API_BASE_URL}/emails/`);
  return response.data;
};

export const deleteEmail = async (id: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/emails/${id}`);
};