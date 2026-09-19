import React, { useState, useEffect } from 'react';
import { Clock, ShieldAlert, Bell, Search, RefreshCw } from 'lucide-react';

export default function Header({ title, subtitle }) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formattedTime = currentTime.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  });

  const formattedDate = currentTime.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-stone-200/80 px-8 py-4 sticky top-0 z-10 flex items-center justify-between">
      <div>
        <h2 className="text-xl font-bold text-stone-900 tracking-tight">{title}</h2>
        {subtitle && <p className="text-xs text-stone-500 font-medium mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center space-x-4">
        {/* System Time Badge */}
        <div className="flex items-center space-x-2 bg-[#fafaf9] border border-stone-200/80 px-3.5 py-1.5 rounded-xl">
          <Clock className="w-3.5 h-3.5 text-stone-400" />
          <div className="text-right">
            <span className="text-xs font-mono font-semibold text-stone-800 tracking-wide">{formattedTime}</span>
            <span className="text-[10px] text-stone-400 block -mt-0.5 font-medium">{formattedDate}</span>
          </div>
        </div>

        {/* Range Live Status Indicator */}
        <div className="flex items-center space-x-2 bg-[#dcfce7] border border-emerald-200/60 px-3 py-1.5 rounded-xl">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-semibold text-[#15803d]">System Operational</span>
        </div>

        {/* Quick Refresh */}
        <button 
          onClick={() => window.location.reload()}
          title="Refresh Data"
          className="p-2 rounded-xl text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors border border-stone-200/60"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        {/* Alert Notifications */}
        <div className="relative">
          <button className="p-2 rounded-xl text-stone-600 hover:bg-stone-100 transition-colors border border-stone-200/60 relative">
            <Bell className="w-4 h-4 text-stone-600" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-amber-500"></span>
          </button>
        </div>
      </div>
    </header>
  );
}
