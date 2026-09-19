import React, { useState } from 'react';
import { 
  Settings, 
  Sliders, 
  ShieldCheck, 
  Database, 
  Bell, 
  Save, 
  CheckCircle2,
  Cpu
} from 'lucide-react';

export default function SettingsView() {
  const [detectionConfidence, setDetectionConfidence] = useState(85);
  const [faceConfidence, setFaceConfidence] = useState(90);
  const [enableAudioAlerts, setEnableAudioAlerts] = useState(true);
  const [autoVerifyKnownWeapons, setAutoVerifyKnownWeapons] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = (e) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="p-8 space-y-6 max-w-4xl mx-auto">
      {/* Top Header */}
      <div className="bg-white border border-stone-200/80 rounded-2xl p-4 shadow-xs flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[#e0e7ff] text-[#4338ca] flex items-center justify-center font-bold">
            <Settings className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-stone-900 text-sm">System Configuration & Parameters</h3>
            <p className="text-xs text-stone-400">Manage AI confidence thresholds, verification rules & alert preferences</p>
          </div>
        </div>

        {savedSuccess && (
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-[#dcfce7] text-[#15803d] flex items-center space-x-1 animate-in fade-in">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Settings Saved Successfully</span>
          </span>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* AI Detection Parameters */}
        <div className="bg-white border border-stone-200/80 rounded-2xl p-6 shadow-xs space-y-5">
          <div className="flex items-center space-x-2 pb-3 border-b border-stone-100">
            <Cpu className="w-4 h-4 text-[#4338ca]" />
            <h4 className="font-bold text-stone-900 text-sm">YOLOv8 AI Vision Parameters</h4>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between text-xs font-semibold text-stone-700 mb-1.5">
                <span>Weapon Detection Confidence Threshold</span>
                <span className="font-mono text-[#4338ca] font-bold">{detectionConfidence}%</span>
              </div>
              <input
                type="range"
                min="50"
                max="98"
                value={detectionConfidence}
                onChange={(e) => setDetectionConfidence(e.target.value)}
                className="w-full accent-[#4338ca] cursor-pointer"
              />
              <p className="text-[11px] text-stone-400 mt-1">Minimum AI probability score required to trigger a weapon detection event.</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-xs font-semibold text-stone-700 mb-1.5">
                <span>Biometric Face Recognition Confidence</span>
                <span className="font-mono text-[#4338ca] font-bold">{faceConfidence}%</span>
              </div>
              <input
                type="range"
                min="60"
                max="99"
                value={faceConfidence}
                onChange={(e) => setFaceConfidence(e.target.value)}
                className="w-full accent-[#4338ca] cursor-pointer"
              />
              <p className="text-[11px] text-stone-400 mt-1">Match threshold for identifying registered officers on camera feed.</p>
            </div>
          </div>
        </div>

        {/* Verification & Alert Rules */}
        <div className="bg-white border border-stone-200/80 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center space-x-2 pb-3 border-b border-stone-100">
            <Bell className="w-4 h-4 text-[#4338ca]" />
            <h4 className="font-bold text-stone-900 text-sm">Automated Rules & Notifications</h4>
          </div>

          <div className="space-y-3">
            <label className="flex items-center justify-between p-3 rounded-xl border border-stone-200/60 bg-[#fafaf9] cursor-pointer hover:bg-stone-50">
              <div>
                <span className="text-xs font-semibold text-stone-900 block">Auto-Verify Pre-Issued Weapons</span>
                <span className="text-[11px] text-stone-400">Automatically mark weapon events as verified if assigned to officer in session.</span>
              </div>
              <input
                type="checkbox"
                checked={autoVerifyKnownWeapons}
                onChange={(e) => setAutoVerifyKnownWeapons(e.target.checked)}
                className="w-4 h-4 accent-[#4338ca] rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between p-3 rounded-xl border border-stone-200/60 bg-[#fafaf9] cursor-pointer hover:bg-stone-50">
              <div>
                <span className="text-xs font-semibold text-stone-900 block">Audible Range Exception Chime</span>
                <span className="text-[11px] text-stone-400">Play chime when an unassigned weapon or security exception is detected.</span>
              </div>
              <input
                type="checkbox"
                checked={enableAudioAlerts}
                onChange={(e) => setEnableAudioAlerts(e.target.checked)}
                className="w-4 h-4 accent-[#4338ca] rounded cursor-pointer"
              />
            </label>
          </div>
        </div>

        {/* Database Status Card */}
        <div className="bg-white border border-stone-200/80 rounded-2xl p-6 shadow-xs flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-[#dcfce7] text-[#15803d] flex items-center justify-center font-bold">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-bold text-stone-900 text-xs">SQLite Database Connection</h4>
              <p className="text-[11px] text-stone-400 font-mono mt-0.5">DB File: database/shooting_range.db • Status: Connected</p>
            </div>
          </div>

          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[#dcfce7] text-[#15803d]">
            ONLINE & HEALTHY
          </span>
        </div>

        {/* Save Button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            className="px-6 py-2.5 rounded-xl bg-[#4338ca] text-white text-xs font-semibold hover:bg-[#3730a3] shadow-xs flex items-center space-x-2 transition-all"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings Changes</span>
          </button>
        </div>
      </form>
    </div>
  );
}
