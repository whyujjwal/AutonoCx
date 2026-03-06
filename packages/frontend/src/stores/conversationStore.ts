import { create } from 'zustand';
import type { Conversation, ConversationDetail, Message } from '@/types/conversation.types';
import { conversationsApi } from '@/api/conversations.api';

interface ConversationState {
  conversations: Conversation[];
  activeConversation: ConversationDetail | null;
  messages: Message[];
  isLoading: boolean;
  isSending: boolean;

  setConversations: (conversations: Conversation[]) => void;
  setActiveConversation: (conversation: ConversationDetail | null) => void;
  loadConversation: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
}

export const useConversationStore = create<ConversationState>()((set, get) => ({
  conversations: [],
  activeConversation: null,
  messages: [],
  isLoading: false,
  isSending: false,

  setConversations: (conversations) => set({ conversations }),

  setActiveConversation: (conversation) =>
    set({
      activeConversation: conversation,
      messages: conversation?.messages ?? [],
    }),

  loadConversation: async (id) => {
    set({ isLoading: true });
    try {
      const { data } = await conversationsApi.get(id);
      const conversation = data.data;
      set({
        activeConversation: conversation,
        messages: conversation.messages,
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  sendMessage: async (content) => {
    const { activeConversation } = get();
    if (!activeConversation) return;

    const optimisticMessage: Message = {
      id: `temp-${Date.now()}`,
      conversationId: activeConversation.id,
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, optimisticMessage],
      isSending: true,
    }));

    try {
      const { data } = await conversationsApi.sendMessage(activeConversation.id, { content });
      set({
        activeConversation: data.data,
        messages: data.data.messages,
        isSending: false,
      });
    } catch {
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== optimisticMessage.id),
        isSending: false,
      }));
    }
  },

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),
}));
