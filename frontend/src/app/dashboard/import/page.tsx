'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Upload, File, Loader2, CheckCircle, Database } from 'lucide-react';
import api from '@/lib/api';

export default function HistoricalImport() {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    
    setIsUploading(true);
    setError('');
    
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await api.post('/historical/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setResults(response.data);
      setFiles([]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to import historical notes.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 p-8">
      <div className="max-w-4xl mx-auto">
        <Link href="/dashboard" className="flex items-center text-blue-400 hover:underline mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Link>

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-100 mb-2">Import Previous Notes</h1>
          <p className="text-slate-400">Upload your old lecture notes to instantly bootstrap your Style Profile. The engine will learn your formatting, tone, and structure.</p>
        </div>

        <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-8 mb-8">
          <div className="border-2 border-dashed border-slate-700 rounded-xl p-12 text-center hover:bg-slate-800/50 hover:border-indigo-500 transition">
            <Database className="w-12 h-12 text-slate-500 mx-auto mb-4" />
            <p className="text-slate-400 mb-4">Drag and drop your Markdown or PDF notes here</p>
            <input 
              type="file" 
              multiple
              accept=".md,.pdf,.txt"
              onChange={handleFileChange}
              className="hidden" 
              id="file-upload" 
            />
            <label 
              htmlFor="file-upload"
              className="px-6 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition cursor-pointer inline-flex items-center"
            >
              <Upload className="w-4 h-4 mr-2" />
              Select Files
            </label>
          </div>

          {files.length > 0 && (
            <div className="mt-6">
              <h3 className="font-semibold text-slate-300 mb-3">Selected Files ({files.length})</h3>
              <ul className="space-y-2 mb-6">
                {files.map((f, i) => (
                  <li key={i} className="flex items-center text-sm text-slate-300 bg-slate-800 p-2 rounded">
                    <File className="w-4 h-4 mr-2 text-indigo-400" />
                    {f.name}
                  </li>
                ))}
              </ul>
              
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className="w-full flex justify-center items-center px-4 py-3 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition disabled:opacity-50 font-medium"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Analyzing {files.length} documents...
                  </>
                ) : (
                  'Start Analysis & Import'
                )}
              </button>
            </div>
          )}

          {error && (
            <div className="mt-6 p-4 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-sm">
              {error}
            </div>
          )}
        </div>

        {results && (
          <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-8">
            <div className="flex items-center mb-6">
              <CheckCircle className="w-8 h-8 text-green-400 mr-3" />
              <h2 className="text-2xl font-bold text-slate-100">Import Complete!</h2>
            </div>
            
            <p className="text-slate-400 mb-6">
              Successfully analyzed {results.imported_count} notes and integrated them into your Style Profile.
            </p>
            
            <h3 className="font-semibold text-slate-200 mb-4">Aggregated Feature Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(results.aggregated_features).map(([key, value]) => (
                <div key={key} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                  <div className="text-xs text-slate-400 uppercase font-semibold mb-1">{key.replace(/_/g, ' ')}</div>
                  <div className="font-bold text-indigo-400">
                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-8 text-center">
              <Link href="/dashboard/style" className="text-indigo-400 font-medium hover:underline">
                View Updated Style Profile &rarr;
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
