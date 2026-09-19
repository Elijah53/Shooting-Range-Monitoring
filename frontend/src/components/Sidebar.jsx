import React from 'react';
import { 
  LayoutDashboard, 
  Video, 
  Crosshair, 
  Users, 
  Settings, 
  ShieldCheck, 
  Radio, 
  ChevronRight,
  LogOut
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'monitoring', label: 'Live Monitoring', icon: Video, badge: '4 LIVE' },
    { id: 'sessions', label: 'Sessions & Inventory', icon: Crosshair },
    { id: 'users', label: 'Officers & Attendance', icon: Users },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-white border-r border-stone-200 flex flex-col justify-between h-screen sticky top-0 select-none shadow-xs">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-stone-100 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[#e0e7ff] text-[#4338ca] flex items-center justify-center font-bold shadow-xs">
            <ShieldCheck className="w-5 h-5 text-[#4338ca]" />
          </div>
          <div>
            <h1 className="font-semibold text-stone-900 text-base leading-tight tracking-tight">Calm Range</h1>
            <p className="text-xs text-stone-400 font-medium">Ops & Monitoring</p>
          </div>
        </div>

        {/* Range Quick Status */}
        <div className="mx-4 my-4 p-3 rounded-xl bg-[#fafaf9] border border-stone-200/60 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-subtle"></span>
            <span className="text-xs font-semibold text-stone-700">Range Safe</span>
          </div>
          <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-[#dcfce7] text-[#15803d]">
            ACTIVE
          </span>
        </div>

        {/* Navigation Menu */}
        <nav className="px-3 space-y-1">
          <div className="px-3 pt-2 pb-1 text-[11px] font-bold tracking-wider text-stone-400 uppercase">
            Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-[#e0e7ff] text-[#4338ca] shadow-xs font-semibold'
                    : 'text-stone-600 hover:bg-stone-100/80 hover:text-stone-900'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#4338ca]' : 'text-stone-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full ${
                    isActive ? 'bg-[#4338ca] text-white' : 'bg-[#dcfce7] text-[#15803d]'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Profile */}
      <div className="p-3 border-t border-stone-100">
        <div className="flex items-center justify-between p-2 rounded-xl hover:bg-stone-50 transition-colors">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 text-white flex items-center justify-center font-bold text-xs shadow-xs">
              SO
            </div>
            <div className="text-left">
              <p className="text-xs font-semibold text-stone-800">Range Master</p>
              <p className="text-[11px] text-stone-400">Station #04 • Admin</p>
            </div>
          </div>
          <button className="text-stone-400 hover:text-stone-600 p-1.5 rounded-lg hover:bg-stone-100">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
