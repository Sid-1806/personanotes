'use client';

import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { LogOut, KeyRound, ShieldCheck } from 'lucide-react';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center">
          <ShieldCheck className="mr-3 text-indigo-400" /> Settings
        </h1>
        <p className="text-slate-400 mt-1">Manage your account.</p>
      </div>

      <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-6">
        <h3 className="text-lg font-bold text-slate-200 mb-4">Account</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Name</span>
            <span className="text-slate-200 font-medium">{user?.name ?? '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Email</span>
            <span className="text-slate-200 font-medium">{user?.email ?? '—'}</span>
          </div>
        </div>
      </div>

      <div className="bg-slate-900/50 backdrop-blur-md rounded-xl shadow-lg border border-slate-800 p-6">
        <h3 className="text-lg font-bold text-slate-200 mb-2 flex items-center">
          <KeyRound size={18} className="mr-2 text-indigo-400" /> AI Provider
        </h3>
        <p className="text-sm text-slate-400">
          Note generation uses Google Gemini. The API key is configured on the server via
          the <code className="text-indigo-300">GEMINI_API_KEY</code> environment variable.
        </p>
      </div>

      <button
        onClick={handleLogout}
        className="flex items-center px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition"
      >
        <LogOut size={18} className="mr-2" /> Log out
      </button>
    </div>
  );
}
