import React, { useState } from 'react';
import { 
  Users, 
  UserCheck, 
  UserMinus, 
  Search, 
  ShieldCheck, 
  Plus, 
  Clock, 
  CheckCircle2,
  ScanFace
} from 'lucide-react';

export default function UsersAttendanceView() {
  const [searchTerm, setSearchTerm] = useState('');

  const officers = [
    { id: 'OFF-001', name: 'Officer Smith', rank: 'Senior Inspector', badge: 'BDG-9941', status: 'Active (On Range)', lane: 'Lane #01', method: 'Face Recognition' },
    { id: 'OFF-002', name: 'Nitish Kumar', rank: 'Range Supervisor', badge: 'BDG-8812', status: 'Active (On Range)', lane: 'Lane #03', method: 'RFID Card' },
    { id: 'OFF-003', name: 'Ali Raza', rank: 'Range Security Officer', badge: 'BDG-7734', status: 'Active (Armory)', lane: 'Armory', method: 'Face Recognition' },
    { id: 'OFF-004', name: 'Officer Davis', rank: 'Inspector', badge: 'BDG-6621', status: 'Checked Out', lane: '-', method: 'RFID Card' },
    { id: 'OFF-005', name: 'Officer Sarah Jenkins', rank: 'Assistant Inspector', badge: 'BDG-5510', status: 'Off Duty', lane: '-', method: '-' },
  ];

  const attendanceLogs = [
    { time: '14:10:05', officer: 'Ali Raza', action: 'CHECK_IN', location: 'Armory Entrance', method: 'Face Recognition', badge: 'mint' },
    { time: '14:00:12', officer: 'Nitish Kumar', action: 'CHECK_IN', location: 'Firing Lane #03', method: 'RFID Card', badge: 'mint' },
    { time: '13:30:00', officer: 'Officer Smith', action: 'CHECK_IN', location: 'Firing Lane #01', method: 'Face Recognition', badge: 'mint' },
    { time: '12:45:30', officer: 'Officer Davis', action: 'CHECK_OUT', location: 'Range Main Exit', method: 'RFID Card', badge: 'stone' },
  ];

  const filteredOfficers = officers.filter(o => 
    o.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    o.badge.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-xs flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[#e0e7ff] text-[#4338ca] flex items-center justify-center font-bold">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-stone-900 text-sm">Officers & Range Attendance Registry</h3>
            <p className="text-xs text-stone-400">Real-time attendance logs & biometric access verification</p>
          </div>
        </div>

        <button className="px-4 py-2 rounded-xl bg-[#4338ca] text-white text-xs font-semibold hover:bg-[#3730a3] transition-colors shadow-xs flex items-center space-x-2">
          <Plus className="w-4 h-4" />
          <span>Register New Officer</span>
        </button>
      </div>

      {/* Grid: Officer Directory & Live Attendance Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Officers List (2 Cols) */}
        <div className="lg:col-span-2 bg-white border border-stone-200/80 rounded-2xl shadow-xs overflow-hidden">
          <div className="p-4 border-b border-stone-100 flex items-center justify-between">
            <div className="relative w-72">
              <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search officer name or badge..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 rounded-xl border border-stone-200 text-xs text-stone-800 focus:outline-none focus:ring-2 focus:ring-[#4338ca]/20 focus:border-[#4338ca]"
              />
            </div>

            <span className="text-xs font-bold text-stone-500 bg-stone-100 px-3 py-1 rounded-full">
              Total Officers: {officers.length}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-stone-700">
              <thead className="bg-[#fafaf9] border-b border-stone-100 uppercase font-bold text-stone-400 text-[10px] tracking-wider">
                <tr>
                  <th className="px-5 py-3">Officer Name</th>
                  <th className="px-5 py-3">Badge ID</th>
                  <th className="px-5 py-3">Rank</th>
                  <th className="px-5 py-3">Attendance Status</th>
                  <th className="px-5 py-3">Verification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {filteredOfficers.map((o) => (
                  <tr key={o.id} className="hover:bg-stone-50/70 transition-colors">
                    <td className="px-5 py-3.5 font-semibold text-stone-900 flex items-center space-x-2.5">
                      <div className="w-7 h-7 rounded-full bg-[#e0e7ff] text-[#4338ca] font-bold text-[10px] flex items-center justify-center">
                        {o.name.split(' ').map(n=>n[0]).join('')}
                      </div>
                      <span>{o.name}</span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-stone-600 font-medium">{o.badge}</td>
                    <td className="px-5 py-3.5 text-stone-600">{o.rank}</td>
                    <td className="px-5 py-3.5">
                      <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${
                        o.status.startsWith('Active') ? 'bg-[#dcfce7] text-[#15803d]' : 'bg-stone-100 text-stone-500'
                      }`}>
                        {o.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-stone-500 text-[11px]">
                      {o.method}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Attendance Activity (1 Col) */}
        <div className="bg-white border border-stone-200/80 rounded-2xl shadow-xs overflow-hidden flex flex-col">
          <div className="p-4 border-b border-stone-100 flex items-center justify-between">
            <h4 className="font-bold text-stone-900 text-sm">Real-time Check-In Log</h4>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          </div>

          <div className="p-4 space-y-3 flex-1 overflow-y-auto">
            {attendanceLogs.map((log, idx) => (
              <div key={idx} className="p-3 rounded-xl border border-stone-200/60 bg-[#fafaf9] hover:border-stone-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-stone-900 text-xs">{log.officer}</span>
                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full ${
                    log.badge === 'mint' ? 'bg-[#dcfce7] text-[#15803d]' : 'bg-stone-200 text-stone-700'
                  }`}>
                    {log.action}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-stone-400">
                  <span>{log.location} • {log.method}</span>
                  <span className="font-mono text-stone-500">{log.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
