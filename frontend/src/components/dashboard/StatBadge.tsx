import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatBadgeProps {
  value: number;
  trend?: number;
  suffix?: string;
  label?: string;
}

export function StatBadge({ value, trend, suffix = '', label }: StatBadgeProps) {
  const isPositive = trend && trend > 0;
  const isNegative = trend && trend < 0;
  const isNeutral = !trend || trend === 0;

  return (
    <div className="flex flex-col">
      {label && <span className="text-sm text-gray-500 mb-1">{label}</span>}
      <div className="flex items-end gap-3">
        <span className="text-4xl font-bold text-gray-900">
          {value}{suffix}
        </span>
        {trend !== undefined && (
          <div className={`flex items-center text-sm font-medium mb-1 px-2 py-0.5 rounded-full ${
            isPositive ? 'text-green-700 bg-green-50' : 
            isNegative ? 'text-red-700 bg-red-50' : 
            'text-gray-600 bg-gray-100'
          }`}>
            {isPositive ? <TrendingUp size={14} className="mr-1" /> : 
             isNegative ? <TrendingDown size={14} className="mr-1" /> : 
             <Minus size={14} className="mr-1" />}
            <span>{isPositive ? '+' : ''}{trend}%</span>
          </div>
        )}
      </div>
    </div>
  );
}
