import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './views/DashboardView';
import LiveMonitoringView from './views/LiveMonitoringView';
import SessionsInventoryView from './views/SessionsInventoryView';
import UsersAttendanceView from './views/UsersAttendanceView';
import SettingsView from './views/SettingsView';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const getHeaderMeta = () => {
    switch (activeTab) {
      case 'dashboard':
        return { title: 'Operational Dashboard', subtitle: 'Overview of range safety, active firing sessions & weapon verification' };
      case 'monitoring':
        return { title: 'Live AI Vision Monitoring', subtitle: 'Real-time 4-channel camera feeds with YOLOv8 bounding box overlays' };
      case 'sessions':
        return { title: 'Sessions & Armory Inventory', subtitle: 'Firearms status, serial number tracking & range lane assignments' };
      case 'users':
        return { title: 'Officers & Range Attendance', subtitle: 'Biometric access control logs, RFID check-ins & duty roster' };
      case 'settings':
        return { title: 'System Settings', subtitle: 'AI detection thresholds, verification rules & alert configurations' };
      default:
        return { title: 'Dashboard', subtitle: '' };
    }
  };

  const { title, subtitle } = getHeaderMeta();

  return (
    <div className="flex min-h-screen bg-[#fafaf9] text-[#334155] font-['Inter',sans-serif]">
      {/* Sidebar Navigation */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header title={title} subtitle={subtitle} />

        <main className="flex-1 overflow-y-auto">
          {activeTab === 'dashboard' && <DashboardView onNavigate={(tab) => setActiveTab(tab)} />}
          {activeTab === 'monitoring' && <LiveMonitoringView />}
          {activeTab === 'sessions' && <SessionsInventoryView />}
          {activeTab === 'users' && <UsersAttendanceView />}
          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>
    </div>
  );
}
