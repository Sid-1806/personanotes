import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center bg-gradient-to-br from-slate-950 via-slate-900 to-black">
      <h1 className="text-5xl font-bold text-slate-100 mb-6">Personalized AI Notes Generator</h1>
      <p className="text-xl text-slate-400 mb-12 max-w-xl">
        Learn smarter with AI-generated notes grounded in your lectures and written in your personal style.
      </p>
      <div className="flex flex-wrap gap-4 justify-center">
        <Link href="/login" className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
          Login
        </Link>
        <Link href="/register" className="px-6 py-3 bg-slate-800 text-slate-100 border border-slate-700 rounded-lg hover:bg-slate-700 transition">
          Register
        </Link>
        <Link href="/dashboard" className="px-6 py-3 bg-transparent text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/10 transition">
          Go to Dashboard
        </Link>
      </div>
    </main>
  );
}
