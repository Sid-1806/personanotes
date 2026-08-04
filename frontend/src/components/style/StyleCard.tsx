import React from 'react';
import { ConfidenceBar } from './ConfidenceBar';

interface StyleCardProps {
  featureKey: string;
  value: any;
  reason: string;
  confidence: number;
  lastUpdated?: string;
}

export function StyleCard({ featureKey, value, reason, confidence, lastUpdated }: StyleCardProps) {
  const formatKey = (key: string) => key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  
  const formatValue = (val: any) => {
    if (typeof val === 'boolean') return val ? 'Yes' : 'No';
    if (Array.isArray(val)) return val.length === 0 ? 'None' : val.join(', ');
    if (typeof val === 'number') return Number.isInteger(val) ? val : val.toFixed(2);
    if (typeof val === 'object' && val !== null) return JSON.stringify(val);
    return val || 'None';
  };

  return (
    <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 overflow-hidden hover:border-indigo-500/50 hover:shadow-xl hover:bg-slate-800/50 transition duration-200 flex flex-col h-full">
      <div className="p-5 flex-1 flex flex-col">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">{formatKey(featureKey)}</h3>
        <div className="text-xl font-bold text-indigo-400 mb-4 line-clamp-2">
          {formatValue(value)}
        </div>
        <div className="bg-slate-900/30 rounded-lg p-3 text-sm text-slate-300 mb-4 flex-1 border border-slate-800 italic">
          "{reason}"
        </div>
        <div className="mt-auto">
          <ConfidenceBar confidence={confidence} />
        </div>
      </div>
      {lastUpdated && (
        <div className="bg-slate-900/30 px-5 py-2 border-t border-slate-800 text-[10px] text-slate-500 text-right uppercase font-medium">
          Updated: {new Date(lastUpdated).toLocaleDateString()}
        </div>
      )}
    </div>
  );
}
