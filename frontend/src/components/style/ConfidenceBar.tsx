import React from 'react';

export function ConfidenceBar({ confidence }: { confidence: number }) {
  const colorClass = 
    confidence >= 0.8 ? 'bg-green-500' : 
    confidence >= 0.5 ? 'bg-yellow-500' : 'bg-red-500';
    
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Engine Confidence</span>
        <span className="font-medium text-gray-700">{Math.round(confidence * 100)}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
        <div 
          className={`h-1.5 rounded-full ${colorClass} transition-all duration-500`}
          style={{ width: `${confidence * 100}%` }}
        ></div>
      </div>
    </div>
  );
}
