import React, { useState } from 'react';
import { 
  Video, 
  Maximize2, 
  Eye, 
  EyeOff, 
  Crosshair, 
  ShieldCheck, 
  ShieldAlert, 
  Play, 
  Pause, 
  Settings2,
  RefreshCw,
  Layers
} from 'lucide-react';

export default function LiveMonitoringView() {
  const [showOverlays, setShowOverlays] = useState(true);
  const [selectedCam, setSelectedCam] = useState(null);
  const [activePreset, setActivePreset] = useState('grid');

  const cameras = [
    {
      id: 'CAM-01',
      name: 'Firing Lane #01 - Active',
      status: 'Live',
      fps: 30,
      officer: 'Officer Smith',
      weapon: 'Glock 17 (Verified)',
      badgeColor: 'mint',
      box: { top: '35%', left: '40%', width: '120px', height: '140px', label: 'Officer Smith • Glock 17' }
    },
    {
      id: 'CAM-02',
      name: 'Firing Lane #02 - Idle',
      status: 'Live',
      fps: 30,
      officer: 'None',
      weapon: 'No Weapon Detected',
      badgeColor: 'stone',
      box: null
    },
    {
      id: 'CAM-03',
      name: 'Firing Lane #03 - Active',
      status: 'Live',
      fps: 28,
      officer: 'Nitish Kumar',
      weapon: 'M4A1 Carbine (Pending)',
      badgeColor: 'butter',
      box: { top: '30%', left: '45%', width: '140px', height: '150px', label: 'Nitish Kumar • M4A1' }
    },
    {
      id: 'CAM-04',
      name: 'Armory Entrance AI Feed',
      status: 'Live',
      fps: 30,
      officer: 'Ali Raza',
      weapon: 'Beretta 92FS (Verified)',
      badgeColor: 'mint',
      box: { top: '40%', left: '35%', width: '110px', height: '130px', label: 'Ali Raza • Armory Pass' }
    },
  ];

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Control Bar */}
      <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-xs flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-[#e0e7ff] text-[#4338ca] flex items-center justify-center font-bold">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-stone-900 text-sm">4-Channel AI Vision Monitoring Grid</h3>
            <p className="text-xs text-stone-400">YOLOv8 Weapon Detection & Face Recognition Stream</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Toggle AI Overlays */}
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-2 border transition-all ${
              showOverlays
                ? 'bg-[#dcfce7] border-emerald-300 text-[#15803d] shadow-2xs'
                : 'bg-stone-100 border-stone-200 text-stone-600'
            }`}
          >
            {showOverlays ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            <span>AI Bounding Overlays: {showOverlays ? 'ON' : 'OFF'}</span>
          </button>

          <div className="h-4 w-[1px] bg-stone-200"></div>

          {/* Grid Layout Toggle */}
          <button 
            onClick={() => setActivePreset('grid')}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium border ${
              activePreset === 'grid' ? 'bg-[#e0e7ff] text-[#4338ca] border-indigo-200' : 'bg-white border-stone-200 text-stone-600'
            }`}
          >
            2x2 Grid
          </button>
        </div>
      </div>

      {/* 4 Camera Stream Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cameras.map((cam) => (
          <div 
            key={cam.id} 
            className="bg-stone-900 border border-stone-800 rounded-2xl overflow-hidden shadow-md relative group aspect-video flex flex-col justify-between"
          >
            {/* Simulated Live Video Background */}
            <div className="absolute inset-0 bg-gradient-to-br from-stone-900 via-stone-850 to-stone-950 flex items-center justify-center">
              {/* Grid texture for realistic camera feel */}
              <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px]"></div>

              {/* Simulated Camera Video Content */}
              <div className="text-center select-none">
                <Video className="w-12 h-12 text-stone-700 mx-auto mb-2 animate-pulse" />
                <p className="text-xs font-mono text-stone-500 font-semibold">{cam.name}</p>
                <p className="text-[10px] font-mono text-stone-600">RTSP Stream • 1080p @ {cam.fps} FPS</p>
              </div>

              {/* Simulated AI Detection Bounding Box */}
              {showOverlays && cam.box && (
                <div 
                  className="absolute border-2 border-emerald-400 bg-emerald-500/10 rounded-lg p-1 animate-in fade-in duration-300"
                  style={{ top: cam.box.top, left: cam.box.left, width: cam.box.width, height: cam.box.height }}
                >
                  <div className="bg-emerald-500 text-stone-950 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shadow-xs whitespace-nowrap -mt-4 inline-block">
                    {cam.box.label}
                  </div>
                </div>
              )}
            </div>

            {/* Top Camera Header Bar */}
            <div className="relative z-10 p-3 bg-gradient-to-b from-stone-950/90 to-transparent flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-mono font-bold text-white tracking-wide">{cam.id}</span>
                <span className="text-xs text-stone-300 font-medium truncate max-w-[180px]">{cam.name}</span>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-stone-800 text-stone-300 font-medium">
                  {cam.fps} FPS
                </span>
                <button 
                  onClick={() => setSelectedCam(cam)}
                  className="p-1 rounded bg-stone-800 text-stone-400 hover:text-white transition-colors"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Bottom Camera Footer Bar */}
            <div className="relative z-10 p-3 bg-gradient-to-t from-stone-950/90 to-transparent flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                  cam.badgeColor === 'mint' ? 'bg-[#dcfce7] text-[#15803d]' :
                  cam.badgeColor === 'butter' ? 'bg-[#fef3c7] text-[#b45309]' : 'bg-stone-800 text-stone-400'
                }`}>
                  {cam.officer !== 'None' ? `Officer: ${cam.officer}` : 'No Active Person'}
                </span>
              </div>

              <span className="text-[11px] font-mono text-stone-400 font-medium">
                {cam.weapon}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Fullscreen Camera Modal Preview */}
      {selectedCam && (
        <div className="fixed inset-0 bg-stone-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-6">
          <div className="bg-stone-900 border border-stone-800 rounded-2xl overflow-hidden max-w-4xl w-full shadow-2xl flex flex-col">
            <div className="p-4 border-b border-stone-800 flex items-center justify-between bg-stone-950">
              <div className="flex items-center space-x-3">
                <Video className="w-5 h-5 text-emerald-400" />
                <div>
                  <h4 className="font-mono font-bold text-white text-sm">{selectedCam.name} ({selectedCam.id})</h4>
                  <p className="text-xs text-stone-400">Full Resolution 1080p Stream</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedCam(null)}
                className="px-3 py-1 rounded-lg bg-stone-800 text-stone-300 text-xs font-semibold hover:bg-stone-700"
              >
                Close Stream
              </button>
            </div>
            <div className="aspect-video bg-stone-950 flex items-center justify-center relative">
              <p className="text-stone-500 font-mono text-sm">Full 1080p Live Stream Rendering...</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
