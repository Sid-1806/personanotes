'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { DashboardCard } from '@/components/dashboard/DashboardCard';
import { FileText, UploadCloud, BrainCircuit, Activity, Database, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['dashboardSummary'],
    queryFn: async () => {
      const res = await api.get('/dashboard/summary');
      return res.data;
    }
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-64 bg-slate-800 animate-pulse rounded-xl border border-slate-700"></div>
        ))}
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="bg-red-500/10 text-red-400 border border-red-500/20 p-4 rounded-lg">
        Failed to load dashboard summary. Please ensure the backend is running and you are logged in.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Col */}
        <div className="lg:col-span-2 space-y-6">
          <DashboardCard title="Recent Lectures" action={<Link href="/dashboard/upload" className="text-blue-600 text-sm hover:underline">Upload</Link>}>
            {summary.recent_lectures?.length === 0 ? (
              <p className="text-slate-400 text-sm italic">No lectures uploaded yet.</p>
            ) : (
              <ul className="divide-y divide-slate-800">
                {summary.recent_lectures?.map((lec: any) => (
                  <li key={lec.id} className="py-3 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
                        <FileText size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-slate-200 truncate max-w-xs">{lec.filename}</p>
                        <p className="text-xs text-slate-400">{new Date(lec.uploaded_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                    <span className="text-xs px-2 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full">{lec.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </DashboardCard>

          <DashboardCard title="Recent Generated Notes" action={<Link href="/dashboard/generate" className="text-blue-600 text-sm hover:underline">Generate</Link>}>
             {summary.recent_notes?.length === 0 ? (
              <p className="text-slate-400 text-sm italic">No notes generated yet.</p>
            ) : (
              <ul className="divide-y divide-slate-800">
                {summary.recent_notes?.map((note: any) => (
                  <li key={note.id} className="py-3 flex justify-between items-center">
                    <div>
                      <p className="text-sm font-medium text-slate-200 truncate max-w-sm">Notes for: {note.lecture_filename || 'Unknown'}</p>
                      <p className="text-xs text-slate-400">{new Date(note.created_at).toLocaleString()}</p>
                    </div>
                    <Link href={`/dashboard/notes/${note.id}`} className="text-blue-400 p-2 hover:bg-blue-500/20 rounded-full transition-colors">
                      <ArrowRight size={18} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </DashboardCard>
        </div>

        {/* Right Col */}
        <div className="space-y-6">
          <DashboardCard title="Current Style Profile" action={<Link href="/dashboard/style" className="text-blue-600 text-sm hover:underline">View Full</Link>}>
            <ul className="space-y-3">
              <li className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Tone</span>
                <span className="font-medium text-slate-200">{summary.style_summary?.tone || 'N/A'}</span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Bullet Pref</span>
                <span className="font-medium text-slate-200">{summary.style_summary?.bullet_preference || 'N/A'}</span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Sentence Length</span>
                <span className="font-medium text-slate-200">{summary.style_summary?.sentence_length || 'N/A'}</span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Confidence</span>
                <span className="font-medium text-slate-200">{summary.style_summary?.confidence ? (summary.style_summary.confidence * 100).toFixed(0) : '0'}%</span>
              </li>
            </ul>
          </DashboardCard>

          <div className="grid grid-cols-2 gap-4">
            <Link href="/dashboard/upload" className="flex flex-col items-center justify-center p-6 bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl hover:border-blue-500/50 hover:bg-slate-800/50 hover:shadow-sm transition group">
              <UploadCloud className="text-blue-400 mb-2 group-hover:-translate-y-1 transition-transform" size={24} />
              <span className="text-sm font-medium text-slate-300">Upload</span>
            </Link>
            <Link href="/dashboard/import" className="flex flex-col items-center justify-center p-6 bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl hover:border-blue-500/50 hover:bg-slate-800/50 hover:shadow-sm transition group">
              <Database className="text-blue-400 mb-2 group-hover:-translate-y-1 transition-transform" size={24} />
              <span className="text-sm font-medium text-slate-300">Import</span>
            </Link>
            <Link href="/dashboard/generate" className="flex flex-col items-center justify-center p-6 bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl hover:border-blue-500/50 hover:bg-slate-800/50 hover:shadow-sm transition group">
              <BrainCircuit className="text-blue-400 mb-2 group-hover:-translate-y-1 transition-transform" size={24} />
              <span className="text-sm font-medium text-slate-300">Generate</span>
            </Link>
            <Link href="/dashboard/style" className="flex flex-col items-center justify-center p-6 bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl hover:border-blue-500/50 hover:bg-slate-800/50 hover:shadow-sm transition group">
              <Activity className="text-blue-400 mb-2 group-hover:-translate-y-1 transition-transform" size={24} />
              <span className="text-sm font-medium text-slate-300">Profile</span>
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
