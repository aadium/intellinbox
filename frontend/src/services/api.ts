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
  sender: string;
  subject: string;
  body: string;
  status: string;
  received_at: string;
  analysis?: Analysis;
}

export const fetchEmails = async (): Promise<Email[]> => {
  const response = await axios.get(`${API_BASE_URL}/emails/`);
  return response.data;
};

export const deleteEmail = async (id: number): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/emails/${id}`);
};