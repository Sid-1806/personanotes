'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { BookOpen, ArrowLeft, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import api from '@/lib/api';

export default function GenerateNotes() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedNotes, setGeneratedNotes] = useState('');
  const [noteId, setNoteId] = useState<number | null>(null);
  const [error, setError] = useState('');
  
  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editedNotes, setEditedNotes] = useState('');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string[]>([]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsGenerating(true);
    setError('');
    
    try {
      const response = await api.post('/notes/generate', { prompt });
      setGeneratedNotes(response.data.notes);
      setEditedNotes(response.data.notes);
      setNoteId(response.data.id);
      setIsEditing(false);
      setFeedbackSuccess([]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate notes. Did you configure your Gemini API key?');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmitFeedback = async () => {
    if (!noteId || !editedNotes.trim()) return;
    
    setIsSubmittingFeedback(true);
    try {
      const response = await api.post(`/notes/${noteId}/feedback`, {
        edited_markdown: editedNotes
      });
      setGeneratedNotes(editedNotes); // Update main view
      setIsEditing(false);
      setFeedbackSuccess(response.data.updated_features || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit feedback.');
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <div className="max-w-4xl mx-auto">
        <Link href="/dashboard" className="flex items-center text-blue-400 hover:underline mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Link>

        <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-8 mb-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100">Generate Personalized Notes</h1>
              <p className="text-slate-400">Ask a question or request notes on a topic from your lectures.</p>
            </div>
          </div>

          <form onSubmit={handleGenerate} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                What do you want to learn? (Topic or Question)
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-slate-700 bg-slate-900/50 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-[100px]"
                placeholder="e.g. Summarize the differences between mitosis and meiosis"
                required
              />
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isGenerating || !prompt.trim()}
              className="w-full py-3 px-4 bg-indigo-500 hover:bg-indigo-600 disabled:bg-slate-700 text-white rounded-lg font-medium transition flex items-center justify-center"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Notes'
              )}
            </button>
          </form>
        </div>

        {generatedNotes && (
          <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
              <h2 className="text-xl font-bold text-slate-100">Your AI Notes</h2>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  className="text-sm px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition font-medium"
                >
                  Edit & Teach AI
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setIsEditing(false);
                      setEditedNotes(generatedNotes);
                    }}
                    className="text-sm px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmitFeedback}
                    disabled={isSubmittingFeedback}
                    className="text-sm px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition font-medium flex items-center"
                  >
                    {isSubmittingFeedback ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                    Save & Submit Feedback
                  </button>
                </div>
              )}
            </div>

            {feedbackSuccess.length > 0 && !isEditing && (
              <div className="mb-6 p-4 bg-green-500/10 text-green-400 rounded-lg text-sm border border-green-500/20">
                <strong>Success!</strong> Your edits were analyzed. The following style preferences were updated: 
                <span className="font-semibold ml-1 text-green-300">{feedbackSuccess.join(', ')}</span>.
              </div>
            )}

            {isEditing ? (
              <div className="space-y-2">
                <p className="text-sm text-slate-400 mb-2">
                  Edit the markdown below. When you save, the Continual Learning Engine will analyze your changes to improve future generations.
                </p>
                <textarea
                  value={editedNotes}
                  onChange={(e) => setEditedNotes(e.target.value)}
                  className="w-full h-96 p-4 font-mono text-sm bg-slate-900 border border-slate-700 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            ) : (
              <div className="prose max-w-none prose-invert prose-indigo">
                <ReactMarkdown>{generatedNotes}</ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
