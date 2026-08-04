'use client';

import React, { useState, useEffect } from 'react';
import { Save, Clock, SplitSquareHorizontal, Edit3, Eye, Undo, Redo } from 'lucide-react';
import ReactMarkdown from 'react-markdown'; // Assuming installed from prior markdown phases

interface AdvancedEditorProps {
  initialContent: string;
  onSave: (content: string) => void;
  lastEdited?: string;
}

export function AdvancedEditor({ initialContent, onSave, lastEdited }: AdvancedEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>('split');
  const [history, setHistory] = useState<string[]>([initialContent]);
  const [historyIndex, setHistoryIndex] = useState(0);

  // Stats
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
  const readingTime = Math.ceil(wordCount / 200);

  // Auto-save
  useEffect(() => {
    const timer = setTimeout(() => {
      if (content !== initialContent) {
        onSave(content);
      }
    }, 2000);
    return () => clearTimeout(timer);
  }, [content, initialContent, onSave]);

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    
    // Update history for undo/redo
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(newContent);
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      setHistoryIndex(historyIndex - 1);
      setContent(history[historyIndex - 1]);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(historyIndex + 1);
      setContent(history[historyIndex + 1]);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/30 border-b border-slate-800">
        <div className="flex items-center gap-1">
          <button onClick={handleUndo} disabled={historyIndex === 0} className="p-1.5 text-slate-400 hover:bg-slate-700 rounded disabled:opacity-50 transition"><Undo size={16}/></button>
          <button onClick={handleRedo} disabled={historyIndex === history.length - 1} className="p-1.5 text-slate-400 hover:bg-slate-700 rounded disabled:opacity-50 transition"><Redo size={16}/></button>
          <div className="w-px h-4 bg-slate-700 mx-2"></div>
          <button onClick={() => setViewMode('edit')} className={`p-1.5 rounded transition ${viewMode === 'edit' ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-400 hover:bg-slate-700'}`}><Edit3 size={16}/></button>
          <button onClick={() => setViewMode('split')} className={`p-1.5 rounded transition ${viewMode === 'split' ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-400 hover:bg-slate-700'}`}><SplitSquareHorizontal size={16}/></button>
          <button onClick={() => setViewMode('preview')} className={`p-1.5 rounded transition ${viewMode === 'preview' ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-400 hover:bg-slate-700'}`}><Eye size={16}/></button>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-400">
          <span>{wordCount} words • {readingTime} min read</span>
          <span className="flex items-center"><Clock size={12} className="mr-1"/> {lastEdited ? new Date(lastEdited).toLocaleTimeString() : 'Draft'}</span>
          <button onClick={() => onSave(content)} className="flex items-center px-3 py-1 bg-indigo-500 text-white rounded hover:bg-indigo-600 transition">
            <Save size={14} className="mr-1"/> Save
          </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex overflow-hidden">
        {(viewMode === 'edit' || viewMode === 'split') && (
          <textarea
            value={content}
            onChange={handleContentChange}
            className={`flex-1 p-6 resize-none outline-none font-mono text-sm bg-slate-950 text-slate-100 placeholder:text-slate-500 ${viewMode === 'split' ? 'border-r border-slate-800' : ''}`}
            placeholder="Start writing..."
          />
        )}
        {(viewMode === 'preview' || viewMode === 'split') && (
          <div className="flex-1 p-8 overflow-y-auto bg-slate-900/50 prose prose-invert prose-indigo max-w-none">
             <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
