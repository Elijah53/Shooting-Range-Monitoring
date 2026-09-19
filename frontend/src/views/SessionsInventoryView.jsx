import React, { useState } from 'react';
import { 
  Crosshair, 
  Plus, 
  CheckCircle2, 
  AlertCircle, 
  Search, 
  Filter, 
  Shield, 
  UserCheck, 
  Calendar,
  Clock
} from 'lucide-react';

export default function SessionsInventoryView() {
  const [activeTab, setActiveTab] = useState('inventory');
  const [selectedWeaponFilter, setSelectedWeaponFilter] = useState('all');

  const weaponInventory = [
    { id: 'WPN-101', name: 'Glock 17', cal: '9x19mm', sn: 'G17-9942', category: 'Handgun', status: 'Issued', officer: 'Officer Smith', lane: 'Lane #01' },
    { id: 'WPN-102', name: 'Beretta 92FS', cal: '9x19mm', sn: 'B92-8821', category: 'Handgun', status: 'Available', officer: '-', lane: '-' },
    { id: 'WPN-103', name: 'M4A1 Carbine', cal: '5.56x45mm NATO', sn: 'M4-5510', category: 'Rifle', status: 'Issued', officer: 'Nitish Kumar', lane: 'Lane #03' },
    { id: 'WPN-104', name: 'MP5 Submachine Gun', cal: '9x19mm', sn: 'MP5-3319', category: 'SMG', status: 'In Maintenance', officer: '-', lane: '-' },
    { id: 'WPN-105', name: 'Sig Sauer P320', cal: '9x19mm', sn: 'SIG-7721', category: 'Handgun', status: 'Available', officer: '-', lane: '-' },
    { id: 'WPN-106', name: 'Remington 870', cal: '12 Gauge', sn: 'REM-1102', category: 'Shotgun', status: 'Available', officer: '-', lane: '-' },
  ];

  const sessions = [
    { id: 'SESS-804', officer: 'Officer Smith', lane: 'Lane #01', weapon: 'Glock 17 (G17-9942)', startTime: '13:30', duration: '52 mins', status: 'Active' },
    { id: 'SESS-805', officer: 'Nitish Kumar', lane: 'Lane #03', weapon: 'M4A1 Carbine (M4-5510)', startTime: '14:00', duration: '22 mins', status: 'Active' },
    { id: 'SESS-806', officer: 'Ali Raza', lane: 'Lane #04', weapon: 'Beretta 92FS (B92-8821)', startTime: '14:10', duration: '12 mins', status: 'Active' },
    { id: 'SESS-803', officer: 'Officer Davis', lane: 'Lane #02', weapon: 'Sig Sauer P320', startTime: '11:15', duration: '45 mins', status: 'Completed' },
  ];

  const filteredInventory = weaponInventory.filter(w => {
    if (selectedWeaponFilter === 'available') return w.status === 'Available';
    if (selectedWeaponFilter === 'issued') return w.status === 'Issued';
    if (selectedWeaponFilter === 'maintenance') return w.status === 'In Maintenance';
    return true;
  });

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Header & Mode Switcher */}
      <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-xs flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[#e0e7ff] text-[#4338ca] flex items-center justify-center font-bold">
            <Crosshair className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-stone-900 text-sm">Armory Inventory & Shooting Sessions</h3>
            <p className="text-xs text-stone-400">Weapon status tracking, issue logs & firing sessions</p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-[#fafaf9] p-1 rounded-xl border border-stone-200/80">
          <button
            onClick={() => setActiveTab('inventory')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'inventory' ? 'bg-white text-[#4338ca] shadow-2xs' : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            Weapon Inventory ({weaponInventory.length})
          </button>
          <button
            onClick={() => setActiveTab('sessions')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'sessions' ? 'bg-white text-[#4338ca] shadow-2xs' : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            Range Sessions ({sessions.length})
          </button>
        </div>
      </div>

      {/* Tab 1: Weapon Inventory */}
      {activeTab === 'inventory' && (
        <div className="bg-white border border-stone-200/80 rounded-2xl shadow-xs overflow-hidden">
          {/* Filter Bar */}
          <div className="p-4 border-b border-stone-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-stone-400 uppercase tracking-wider mr-2">Filter Status:</span>
              <button 
                onClick={() => setSelectedWeaponFilter('all')}
                className={`px-3 py-1 rounded-lg text-xs font-medium ${
                  selectedWeaponFilter === 'all' ? 'bg-[#e0e7ff] text-[#4338ca]' : 'bg-stone-100 text-stone-600'
                }`}
              >
                All Weapons
              </button>
              <button 
                onClick={() => setSelectedWeaponFilter('available')}
                className={`px-3 py-1 rounded-lg text-xs font-medium ${
                  selectedWeaponFilter === 'available' ? 'bg-[#dcfce7] text-[#15803d]' : 'bg-stone-100 text-stone-600'
                }`}
              >
                Available
              </button>
              <button 
                onClick={() => setSelectedWeaponFilter('issued')}
                className={`px-3 py-1 rounded-lg text-xs font-medium ${
                  selectedWeaponFilter === 'issued' ? 'bg-[#fef3c7] text-[#b45309]' : 'bg-stone-100 text-stone-600'
                }`}
              >
                Issued
              </button>
              <button 
                onClick={() => setSelectedWeaponFilter('maintenance')}
                className={`px-3 py-1 rounded-lg text-xs font-medium ${
                  selectedWeaponFilter === 'maintenance' ? 'bg-[#ffe4e6] text-[#be123c]' : 'bg-stone-100 text-stone-600'
                }`}
              >
                In Maintenance
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-stone-700">
              <thead className="bg-[#fafaf9] border-b border-stone-100 uppercase font-bold text-stone-400 text-[10px] tracking-wider">
                <tr>
                  <th className="px-5 py-3">Weapon Model</th>
                  <th className="px-5 py-3">Serial Number</th>
                  <th className="px-5 py-3">Caliber</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Current Assignment</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {filteredInventory.map((w) => (
                  <tr key={w.id} className="hover:bg-stone-50/70 transition-colors">
                    <td className="px-5 py-3.5 font-semibold text-stone-900">
                      {w.name}
                      <span className="block text-[10px] text-stone-400 font-normal">{w.category}</span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-stone-600 font-medium">{w.sn}</td>
                    <td className="px-5 py-3.5 text-stone-600">{w.cal}</td>
                    <td className="px-5 py-3.5">
                      <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${
                        w.status === 'Available' ? 'bg-[#dcfce7] text-[#15803d]' :
                        w.status === 'Issued' ? 'bg-[#fef3c7] text-[#b45309]' : 'bg-[#ffe4e6] text-[#be123c]'
                      }`}>
                        {w.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-stone-700 font-medium">
                      {w.officer !== '-' ? (
                        <span>{w.officer} <span className="text-stone-400 font-normal">({w.lane})</span></span>
                      ) : (
                        <span className="text-stone-400 italic">Unassigned</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {w.status === 'Available' ? (
                        <button className="px-3 py-1 rounded-lg bg-[#e0e7ff] text-[#4338ca] text-xs font-semibold hover:bg-indigo-200 transition-colors">
                          Issue Weapon
                        </button>
                      ) : (
                        <button className="px-3 py-1 rounded-lg bg-stone-100 text-stone-600 text-xs font-medium hover:bg-stone-200">
                          View Log
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Range Sessions */}
      {activeTab === 'sessions' && (
        <div className="bg-white border border-stone-200/80 rounded-2xl shadow-xs overflow-hidden">
          <div className="p-5 border-b border-stone-100">
            <h4 className="font-bold text-stone-900 text-sm">Shooting Range Firing Sessions</h4>
            <p className="text-xs text-stone-400 mt-0.5">Active and historic range sessions with assigned firearms</p>
          </div>

          <div className="divide-y divide-stone-100">
            {sessions.map((sess) => (
              <div key={sess.id} className="p-5 hover:bg-stone-50/70 transition-colors flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 rounded-xl bg-[#e0e7ff] text-[#4338ca] font-bold text-xs flex items-center justify-center">
                    {sess.id.split('-')[1]}
                  </div>
                  <div>
                    <h5 className="font-semibold text-stone-900 text-sm">{sess.officer}</h5>
                    <p className="text-xs text-stone-500 mt-0.5">
                      Weapon: <span className="font-medium text-stone-700">{sess.weapon}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-6">
                  <div className="text-right">
                    <span className="text-xs font-bold text-stone-800 bg-stone-100 px-2.5 py-1 rounded-lg">
                      {sess.lane}
                    </span>
                    <p className="text-[11px] text-stone-400 mt-1">Started: {sess.startTime} ({sess.duration})</p>
                  </div>

                  <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${
                    sess.status === 'Active' ? 'bg-[#dcfce7] text-[#15803d]' : 'bg-stone-100 text-stone-600'
                  }`}>
                    {sess.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
