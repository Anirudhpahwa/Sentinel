import Link from "next/link";

export default function Navbar() {
  return (
    <header className="bg-navy text-white border-b border-navy-light">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-sm font-semibold tracking-[0.2em]">SENTINEL</span>
          <span className="text-xs text-white/60 hidden sm:inline">Job Orchestration Platform</span>
        </Link>
        <nav className="flex items-center gap-6 text-sm text-white/80">
          <Link href="/" className="hover:text-white transition-colors">
            Operations
          </Link>
          <Link href="/jobs" className="hover:text-white transition-colors">
            Jobs
          </Link>
          <Link href="/workers" className="hover:text-white transition-colors">
            Workers
          </Link>
        </nav>
      </div>
    </header>
  );
}
