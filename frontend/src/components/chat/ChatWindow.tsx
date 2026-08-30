import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Sparkles,
  User as UserIcon,
  Bot,
  Plus,
  Trash2,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import { ChatSession, ChatMessage } from '../../types';
import { SourceCard } from './SourceCard';
import { BreakdownTable } from './BreakdownTable';
import { apiClient } from '../../services/api';

/** Renders a small, safe subset of markdown (**bold** only) used by the
 * backend's deterministic answer text, without pulling in a markdown lib. */
const renderInlineMarkdown = (text: string): React.ReactNode[] => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-bold text-white">{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
};

export const ChatWindow: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const samplePrompts = [
    "How much did I spend on milk this month?",
    "How much did I spend at DMart last month?",
    "What's my highest purchase this month?",
    "How much tax did I pay this year?",
    "Show me all receipts from Amazon."
  ];

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  const fetchSessions = async () => {
    try {
      const res = await apiClient.get<ChatSession[]>('/chat/sessions');
      setSessions(res.data);
      if (res.data.length > 0 && !activeSessionId) {
        loadSession(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch chat sessions:', err);
    }
  };

  const loadSession = async (sessionId: number) => {
    setActiveSessionId(sessionId);
    try {
      const res = await apiClient.get<ChatSession>(`/chat/sessions/${sessionId}`);
      setMessages(res.data.messages);
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
  };

  const handleDeleteSession = async (e: React.MouseEvent, sessionId: number) => {
    e.stopPropagation();
    try {
      await apiClient.delete(`/chat/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleSendQuery = async (queryText: string) => {
    const text = queryText.trim();
    if (!text || isGenerating) return;

    // Optimistic UI user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      session_id: activeSessionId || 0,
      role: 'user',
      content: text,
      sources: [],
      breakdown: null,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setInputQuery('');
    setIsGenerating(true);

    try {
      const res = await apiClient.post('/chat', {
        question: text,
        session_id: activeSessionId,
      });

      const data = res.data;
      if (!activeSessionId) {
        setActiveSessionId(data.session_id);
        fetchSessions();
      }

      const assistantMsg: ChatMessage = {
        id: Date.now() + 1,
        session_id: data.session_id,
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        breakdown: data.breakdown || null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: Date.now() + 1,
        session_id: activeSessionId || 0,
        role: 'assistant',
        content: "I couldn't process your request right now. Please check if your receipts are processed and try again.",
        sources: [],
        breakdown: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-slate-950">
      {/* Left Chat Sessions Sidebar */}
      <aside className="w-64 bg-slate-900/60 border-r border-slate-800 flex flex-col p-4 shrink-0 hidden lg:flex">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 text-cyan-400 font-semibold text-xs transition-all shadow-sm mb-4"
        >
          <Plus className="w-4 h-4" />
          Start New Conversation
        </button>

        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2 px-2">Recent Chats</p>
        
        <div className="space-y-1 overflow-y-auto flex-1 pr-1">
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => loadSession(s.id)}
              className={`flex items-center justify-between p-3 rounded-xl text-xs cursor-pointer group transition-all ${
                activeSessionId === s.id
                  ? 'bg-slate-800 text-slate-100 font-semibold border border-slate-700'
                  : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
              }`}
            >
              <span className="truncate flex-1">{s.title}</span>
              <button
                onClick={(e) => handleDeleteSession(e, s.id)}
                className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 p-1 transition-opacity"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <p className="text-xs text-slate-600 px-2 py-4 italic text-center">No previous chat history.</p>
          )}
        </div>
      </aside>

      {/* Main Chat Conversation Area */}
      <main className="flex-1 flex flex-col justify-between overflow-hidden">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white mx-auto shadow-xl shadow-cyan-500/20">
                <Sparkles className="w-8 h-8 animate-pulse" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">ReceiptRAG Conversational Intelligence</h2>
                <p className="text-xs text-slate-400 mt-2 max-w-lg mx-auto">
                  Ask natural questions about your uploaded bills, invoices, and receipts. Every response is strictly grounded in retrieved documents with verified source citations.
                </p>
              </div>

              {/* Sample Prompt Pills */}
              <div className="pt-4">
                <p className="text-xs font-semibold text-slate-500 mb-3">Try asking:</p>
                <div className="flex flex-wrap gap-2 justify-center max-w-xl mx-auto">
                  {samplePrompts.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendQuery(prompt)}
                      className="text-xs text-slate-300 bg-slate-900 border border-slate-800 hover:border-cyan-500/50 hover:bg-slate-850 px-3.5 py-2 rounded-xl transition-all"
                    >
                      "{prompt}"
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shrink-0 shadow-md shadow-cyan-500/10 mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed space-y-3 shadow-sm ${
                      msg.role === 'user'
                        ? 'bg-cyan-600 text-white rounded-tr-none font-medium'
                        : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{renderInlineMarkdown(msg.content)}</p>

                    {/* Verified numeric breakdown table (structured-query answers) */}
                    {msg.role === 'assistant' && msg.breakdown && (
                      <BreakdownTable breakdown={msg.breakdown} />
                    )}

                    {/* Cited Source Cards */}
                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <div className="pt-3 border-t border-slate-800 space-y-2">
                        <p className="text-[11px] font-bold text-cyan-400 flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Grounded Sources ({msg.sources.length}):
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {msg.sources.map((src, idx) => (
                            <SourceCard key={idx} source={src} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold shrink-0 mt-1">
                      <UserIcon className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))}

              {isGenerating && (
                <div className="flex gap-4 items-center max-w-3xl mx-auto text-xs text-slate-400">
                  <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                  <span>Searching vector embeddings and generating grounded answer...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Text Box */}
        <div className="p-4 bg-slate-900/80 border-t border-slate-800">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendQuery(inputQuery);
            }}
            className="max-w-3xl mx-auto flex items-center gap-2 relative"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask anything about your receipts (e.g., 'How much tax did I pay in August?')"
              className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-4 pr-12 py-3.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-all shadow-inner"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isGenerating}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold disabled:opacity-30 transition-all shadow-md"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};
