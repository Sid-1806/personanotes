'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import api from '@/lib/api';

export default function NoteDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const { data, isLoading, error } = useQuery({
    queryKey: ['note', id],
    queryFn: async () => (await api.get(`/notes/${id}`)).data,
    enabled: !!id,
  });

  return (
    <div className="max-w-4xl mx-auto">
      <Link href="/dashboard" className="flex items-center text-blue-400 hover:underline mb-6">
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
      </Link>

      {isLoading && (
        <div className="h-64 bg-slate-800 animate-pulse rounded-xl border border-slate-700" />
      )}

      {error && (
        <div className="bg-red-500/10 text-red-400 border border-red-500/20 p-6 rounded-xl flex items-start">
          <AlertCircle className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" />
          <p>Could not load this note. It may not exist or you may not have access.</p>
        </div>
      )}

      {data && (
        <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-8">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
            <h1 className="text-xl font-bold text-slate-100">Generated Note</h1>
            <span className="text-xs text-slate-400">
              {new Date(data.created_at).toLocaleString()}
            </span>
          </div>
          <div className="prose max-w-none prose-invert prose-indigo">
            <ReactMarkdown>{data.notes}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
