export interface Conversation {
  sessionId: string;
  characterId: string;
  title: string;
  lastMessage: string;
  timestamp: number;
}

const HISTORY_KEY = 'kime-chat-history';

export const getHistory = (): Conversation[] => {
  try {
    const historyJson = localStorage.getItem(HISTORY_KEY);
    if (!historyJson) return [];
    const history = JSON.parse(historyJson) as Conversation[];
    // Sort by timestamp descending (newest first)
    return history.sort((a, b) => b.timestamp - a.timestamp);
  } catch (error) {
    console.error("Failed to parse chat history:", error);
    return [];
  }
};

export const saveHistory = (history: Conversation[]): void => {
  try {
    const historyJson = JSON.stringify(history);
    localStorage.setItem(HISTORY_KEY, historyJson);
  } catch (error) {
    console.error("Failed to save chat history:", error);
  }
};

export const addConversation = (conversation: Omit<Conversation, 'timestamp'>): void => {
  const history = getHistory();
  const now = Date.now();

  const existingIndex = history.findIndex(c => c.sessionId === conversation.sessionId);

  if (existingIndex !== -1) {
    // Update existing conversation
    const existingConv = history[existingIndex];
    existingConv.lastMessage = conversation.lastMessage;
    existingConv.timestamp = now;
    // If the title was a placeholder, update it
    if (existingConv.title.startsWith('Conversation at')) {
        existingConv.title = conversation.title;
    }
  } else {
    // Add new conversation
    history.push({ ...conversation, timestamp: now });
  }

  saveHistory(history);
};
