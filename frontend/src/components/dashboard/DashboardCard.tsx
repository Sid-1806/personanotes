import React from 'react';

interface DashboardCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export function DashboardCard({ title, children, className = '', action }: DashboardCardProps) {
  return (
    <div className={`bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 overflow-hidden ${className}`}>
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/30">
        <h3 className="font-semibold text-slate-100">{title}</h3>
        {action && <div>{action}</div>}
      </div>
      <div className="p-6">
        {children}
      </div>
    </div>
  );
}
