'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { BrainCircuit, AlertCircle } from 'lucide-react';
import { StyleCard } from '@/components/style/StyleCard';

export default function StyleProfilePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['styleDashboard'],
    queryFn: async () => {
      const res = await api.get('/style/dashboard');
      return res.data;
    }
  });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse p-6">
        <div className="h-40 bg-slate-800 border border-slate-700 rounded-xl"></div>
        <div className="h-64 bg-slate-800 border border-slate-700 rounded-xl"></div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-500/10 text-red-400 border border-red-500/20 p-6 rounded-xl flex items-start mt-6 mx-6">
        <AlertCircle className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" />
        <p>Failed to load the Style Profile. Please ensure the backend is running.</p>
      </div>
    );
  }

  const { current_profile } = data;
  const hasProfile = current_profile && Object.keys(current_profile).length > 0;

  if (!hasProfile) {
    return (
      <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-12 text-center mt-6 mx-6">
        <BrainCircuit className="w-16 h-16 text-slate-600 mx-auto mb-4" />
        <h3 className="text-xl font-medium text-slate-100 mb-2">No Style Intelligence Yet</h3>
        <p className="text-slate-400 max-w-md mx-auto mb-6">
          The engine hasn't learned your writing style yet. Upload lectures and generate some notes to begin the learning process.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center">
          <BrainCircuit className="mr-3 text-indigo-400" /> Style Profile
        </h1>
        <p className="text-slate-400 mt-1">This represents the writing style the AI has learned from your notes.</p>
      </div>

      <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 overflow-hidden">
        <div className="p-6 border-b border-slate-800 bg-slate-900/30">
          <h3 className="text-lg font-bold text-slate-200">Current Style Parameters</h3>
          <p className="text-sm text-slate-400 mt-1">The active knowledge used for note generation.</p>
        </div>
        
        <div className="p-6 bg-transparent">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(current_profile).map(([key, detail]: [string, any]) => (
              <StyleCard 
                key={key}
                featureKey={key}
                value={detail.value}
                reason={detail.reason}
                confidence={detail.confidence}
                lastUpdated={detail.last_updated}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
