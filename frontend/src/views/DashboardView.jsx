import React, { useState } from 'react';
import { 
  Users, 
  Crosshair, 
  ShieldAlert, 
  Video, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ChevronRight,
  ShieldCheck,
  Plus,
  Search,
  Filter
} from 'lucide-react';

export default function DashboardView({ onNavigate }) {
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedWeapon, setSelectedWeapon] = useState('Glock 17 (9mm) - SN: G17-9942');
  const [isVerifying, setIsVerifying] = useState(false);
  const [events, setEvents] = useState([
    { id: 'EVT-1092', time: '14:22:05', officer: 'Officer Smith', avatar: 'OS', weapon: 'Glock 17', type: 'Pistol', status: 'Verified', badge: 'mint' },
    { id: 'EVT-1091', time: '14:18:40', officer: 'Nitish Kumar', avatar: 'NK', weapon: 'M4 Carbine', type: 'Rifle', status: 'Pending Verification', badge: 'butter' },
    { id: 'EVT-1090', time: '14:05:12', officer: 'Ali Raza', avatar: 'AR', weapon: 'Beretta 92FS', type: 'Pistol', status: 'Verified', badge: 'mint' },
    { id: 'EVT-1089', time: '13:48:30', officer: 'Officer Davis', avatar: 'OD', weapon: 'MP5 Submachine Gun', type: 'SMG', status: 'Flagged Exception', badge: 'rose' },
  ]);

  const weaponInventoryList = [
    { id: 'W-01', name: 'Glock 17 (9mm) - SN: G17-9942', status: 'Issued' },
    { id: 'W-02', name: 'Beretta 92FS - SN: B92-8821', status: 'Available' },
    { id: 'W-03', name: 'M4A1 Carbine (5.56mm) - SN: M4-5510', status: 'Issued' },
    { id: 'W-04', name: 'MP5 Submachine Gun - SN: MP5-3319', status: 'In Maintenance' },
    { id: 'W-05', name: 'Sig Sauer P320 - SN: SIG-7721', status: 'Available' },
  ];

  const activeSessions = [
    { id: 'SESS-804', officer: 'Officer Smith', avatar: 'OS', lane: 'Lane #01', started: '13:30 (52m ago)', weapon: 'Glock 17 (9mm)', status: 'LIVE' },
    { id: 'SESS-805', officer: 'Nitish Kumar', avatar: 'NK', lane: 'Lane #03', started: '14:00 (22m ago)', weapon: 'M4A1 Carbine', status: 'LIVE' },
    { id: 'SESS-806', officer: 'Ali Raza', avatar: 'AR', lane: 'Lane #04', started: '14:10 (12m ago)', weapon: 'Beretta 92FS', status: 'LIVE' },
  ];

  const handleVerifySubmit = (e) => {
    e.preventDefault();
    if (!selectedEvent) return;
    setEvents(events.map(ev => 
      ev.id === selectedEvent.id 
        ? { ...ev, status: 'Verified', badge: 'mint', weapon: selectedWeapon.split(' - ')[0] }
        : ev
    ));
    setSelectedEvent(null);
  };

  return (
    <div className="p-8 space-[#6] space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-white border border-stone-200/80 rounded-2xl p-6 shadow-xs flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-[#e0e7ff] text-[#4338ca] flex items-center justify-center font-bold">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-stone-900">Shooting Range Operational Dashboard</h3>
            <p className="text-xs text-stone-500 mt-0.5">Real-time attendance, weapon verification & live camera feed status</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button 
            onClick={() => onNavigate('sessions')}
            className="px-4 py-2 rounded-xl bg-[#4338ca] text-white text-xs font-semibold hover:bg-[#3730a3] transition-colors shadow-xs flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>New Range Session</span>
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* People Present */}
        <div className="bg-white border border-stone-200/80 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="h-1 bg-[#dcfce7] absolute top-0 left-0 right-0"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">People Present</span>
            <div className="p-2 rounded-xl bg-[#dcfce7] text-[#15803d]">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-stone-900">6</span>
            <span className="text-xs font-semibold text-[#15803d] ml-2 bg-[#dcfce7] px-2 py-0.5 rounded-full">+2 in last hr</span>
          </div>
          <p className="text-[11px] text-stone-400 mt-2 font-medium">3 Officers • 3 Visitors</p>
        </div>

        {/* Active Sessions */}
        <div className="bg-white border border-stone-200/80 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="h-1 bg-[#e0e7ff] absolute top-0 left-0 right-0"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">Active Sessions</span>
            <div className="p-2 rounded-xl bg-[#e0e7ff] text-[#4338ca]">
              <Crosshair className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-stone-900">3</span>
            <span className="text-xs font-semibold text-[#4338ca] ml-2 bg-[#e0e7ff] px-2 py-0.5 rounded-full">Lanes 1, 3, 4</span>
          </div>
          <p className="text-[11px] text-stone-400 mt-2 font-medium">Lane #02 Available</p>
        </div>

        {/* Weapon Events */}
        <div className="bg-white border border-stone-200/80 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="h-1 bg-[#fef3c7] absolute top-0 left-0 right-0"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">Weapon Events Today</span>
            <div className="p-2 rounded-xl bg-[#fef3c7] text-[#b45309]">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-stone-900">14</span>
            <span className="text-xs font-semibold text-[#b45309] ml-2 bg-[#fef3c7] px-2 py-0.5 rounded-full">1 Pending</span>
          </div>
          <p className="text-[11px] text-stone-400 mt-2 font-medium">13 Auto-Verified</p>
        </div>

        {/* Cameras Online */}
        <div className="bg-white border border-stone-200/80 rounded-2xl p-5 shadow-xs relative overflow-hidden">
          <div className="h-1 bg-[#dcfce7] absolute top-0 left-0 right-0"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-stone-400 uppercase tracking-wider">AI Cameras Online</span>
            <div className="p-2 rounded-xl bg-[#dcfce7] text-[#15803d]">
              <Video className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-stone-900">4 / 4</span>
            <span className="text-xs font-semibold text-[#15803d] ml-2 bg-[#dcfce7] px-2 py-0.5 rounded-full">100% Stream</span>
          </div>
          <p className="text-[11px] text-stone-400 mt-2 font-medium">FPS: 30 • Latency: 14ms</p>
        </div>
      </div>

      {/* Grid Section: Active Sessions & Weapon Events */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Shooting Sessions (2 Cols) */}
        <div className="lg:col-span-2 bg-white border border-stone-200/80 rounded-2xl shadow-xs overflow-hidden">
          <div className="p-5 border-b border-stone-100 flex items-center justify-between">
            <div>
              <h4 className="font-bold text-stone-900 text-sm">Active Shooting Range Sessions</h4>
              <p className="text-xs text-stone-400 mt-0.5">Officers currently occupying range firing lanes</p>
            </div>
            <button 
              onClick={() => onNavigate('sessions')}
              className="text-xs font-semibold text-[#4338ca] hover:underline flex items-center space-x-1"
            >
              <span>View All</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-stone-100">
            {activeSessions.map((session) => (
              <div key={session.id} className="p-4 hover:bg-stone-50/70 transition-colors flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 rounded-full bg-stone-100 border border-stone-200 text-stone-700 font-bold text-xs flex items-center justify-center">
                    {session.avatar}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-stone-900 text-sm">{session.officer}</span>
                      <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-md bg-[#e0e7ff] text-[#4338ca]">
                        {session.id}
                      </span>
                    </div>
                    <p className="text-xs text-stone-400 mt-0.5">
                      Issued: <span className="text-stone-700 font-medium">{session.weapon}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <span className="text-xs font-bold text-stone-800 bg-stone-100 px-2.5 py-1 rounded-lg">
                      {session.lane}
                    </span>
                    <p className="text-[11px] text-stone-400 mt-1">{session.started}</p>
                  </div>

                  <span className="flex items-center space-x-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#dcfce7] text-[#15803d]">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-subtle"></span>
                    <span>LIVE</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Weapon Events Panel (1 Col) */}
        <div className="bg-white border border-stone-200/80 rounded-2xl shadow-xs overflow-hidden flex flex-col">
          <div className="p-5 border-b border-stone-100 flex items-center justify-between">
            <div>
              <h4 className="font-bold text-stone-900 text-sm">Weapon Events</h4>
              <p className="text-xs text-stone-400 mt-0.5">Automated AI detection log</p>
            </div>
            <span className="text-xs font-bold text-stone-500 bg-stone-100 px-2 py-0.5 rounded-full">
              Today
            </span>
          </div>

          <div className="p-4 space-y-3 flex-1 overflow-y-auto max-h-[360px]">
            {events.map((ev) => (
              <div key={ev.id} className="p-3.5 rounded-xl border border-stone-200/60 bg-[#fafaf9] hover:border-stone-300 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="w-7 h-7 rounded-lg bg-white border border-stone-200 text-stone-700 font-bold text-[11px] flex items-center justify-center">
                      {ev.avatar}
                    </span>
                    <div>
                      <h5 className="text-xs font-semibold text-stone-900">{ev.officer}</h5>
                      <span className="text-[10px] text-stone-400 font-mono">{ev.time} • {ev.id}</span>
                    </div>
                  </div>

                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    ev.badge === 'mint' ? 'bg-[#dcfce7] text-[#15803d]' :
                    ev.badge === 'butter' ? 'bg-[#fef3c7] text-[#b45309]' : 'bg-[#ffe4e6] text-[#be123c]'
                  }`}>
                    {ev.type}
                  </span>
                </div>

                <div className="mt-2 pt-2 border-t border-stone-200/40 flex items-center justify-between">
                  <span className="text-xs text-stone-600 font-medium">
                    {ev.weapon}
                  </span>

                  {ev.status === 'Pending Verification' ? (
                    <button
                      onClick={() => setSelectedEvent(ev)}
                      className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[#fef3c7] text-[#b45309] hover:bg-[#fde68a] transition-colors border border-amber-300/60 shadow-2xs"
                    >
                      Verify Gun
                    </button>
                  ) : (
                    <span className={`text-[11px] font-medium flex items-center space-x-1 ${
                      ev.badge === 'mint' ? 'text-[#15803d]' : 'text-[#be123c]'
                    }`}>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{ev.status}</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Manual Verification Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-stone-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-stone-200 shadow-xl max-w-md w-full p-6 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-stone-100">
              <div>
                <h3 className="font-bold text-stone-900 text-base">Manual Weapon Event Verification</h3>
                <p className="text-xs text-stone-400 mt-0.5">Assign and confirm registered gun for {selectedEvent.officer}</p>
              </div>
            </div>

            <form onSubmit={handleVerifySubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1.5">
                  Select Registered Weapon from Inventory
                </label>
                <select
                  value={selectedWeapon}
                  onChange={(e) => setSelectedWeapon(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-stone-300 text-sm font-medium text-stone-800 bg-white focus:outline-none focus:ring-2 focus:ring-[#4338ca]/20 focus:border-[#4338ca]"
                >
                  {weaponInventoryList.map((w) => (
                    <option key={w.id} value={w.name}>
                      {w.name} ({w.status})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider mb-1.5">
                  Officer Assigned
                </label>
                <input
                  type="text"
                  readOnly
                  value={selectedEvent.officer}
                  className="w-full px-3.5 py-2 rounded-xl border border-stone-200 bg-stone-50 text-sm font-medium text-stone-700"
                />
              </div>

              <div className="pt-3 border-t border-stone-100 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setSelectedEvent(null)}
                  className="px-4 py-2 rounded-xl border border-stone-200 text-stone-600 text-xs font-semibold hover:bg-stone-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-[#4338ca] text-white text-xs font-semibold hover:bg-[#3730a3] shadow-xs"
                >
                  Confirm & Verify Weapon
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
