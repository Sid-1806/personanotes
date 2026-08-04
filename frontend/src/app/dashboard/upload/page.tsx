'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useLectures } from '@/hooks/useLectures';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect } from 'react';

export default function UploadLecture() {
  const { upload } = useLectures();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    try {
      await upload.mutateAsync(file);
      alert('Upload successful!');
      router.push('/dashboard');
    } catch (error) {
      console.error('Upload failed', error);
      alert('Upload failed.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="bg-slate-900/50 backdrop-blur-md shadow p-4 border-b border-slate-800">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href="/dashboard" className="text-blue-400 hover:underline">&larr; Back to Dashboard</Link>
        </div>
      </nav>

      <main className="max-w-xl mx-auto p-8 mt-10 bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800">
        <h2 className="text-2xl font-bold mb-6 text-slate-100">Upload a Lecture</h2>
        <form onSubmit={handleUpload} className="flex flex-col gap-6">
          <div className="border-2 border-dashed border-slate-700 hover:border-blue-500 hover:bg-slate-800/50 transition-colors rounded-lg p-12 text-center">
            <input
              type="file"
              accept=".pdf,.txt,.md"
              className="hidden"
              id="file-upload"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
              <span className="text-4xl mb-4">📄</span>
              <span className="text-blue-400 font-medium">Browse Files</span>
              <span className="text-sm text-slate-400 mt-2">Supports PDF, TXT, MD</span>
            </label>
          </div>
          
          {file && (
            <div className="bg-blue-500/10 border border-blue-500/20 p-3 rounded text-sm text-blue-300">
              Selected: <strong className="text-blue-100">{file.name}</strong>
            </div>
          )}

          <button 
            type="submit" 
            disabled={!file || upload.isPending}
            className="w-full bg-blue-500 text-white py-3 rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {upload.isPending ? 'Uploading...' : 'Upload Lecture'}
          </button>
        </form>
      </main>
    </div>
  );
}
