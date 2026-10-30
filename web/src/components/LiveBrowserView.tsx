import React, { useState, useRef } from 'react';
import { ActionableElement, BrowserTab } from '../types';
import { Eye, EyeOff, MousePointer, ShieldAlert, Wifi, WifiOff, Plus, X, Globe, Send } from 'lucide-react';

interface LiveBrowserViewProps {
  frame: string | null;
  isConnected: boolean;
  isTakeover: boolean;
  elements: ActionableElement[];
  tabs: BrowserTab[];
  onSwitchTab: (index: number) => void;
  onNewTab: (url?: string) => void;
  onCloseTab: (index?: number) => void;
  onRemoteClick: (x: number, y: number, button?: string) => void;
  onRemoteScroll: (deltaX: number, deltaY: number) => void;
  onRemoteType: (text: string) => void;
  onRemotePress: (key: string) => void;
}

export const LiveBrowserView: React.FC<LiveBrowserViewProps> = ({
  frame,
  isConnected,
  isTakeover,
  elements,
  tabs,
  onSwitchTab,
  onNewTab,
  onCloseTab,
  onRemoteClick,
  onRemoteScroll,
  onRemoteType,
  onRemotePress,
}) => {
  const [showOverlay, setShowOverlay] = useState(true);
  const [interactiveMode, setInteractiveMode] = useState(false);
  const [keyInput, setKeyInput] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  const isInteractive = isTakeover || interactiveMode;

  const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isInteractive || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Scale to native 1280x800 browser coordinates
    const scaleX = 1280 / rect.width;
    const scaleY = 800 / rect.height;

    const nativeX = Math.round(clickX * scaleX);
    const nativeY = Math.round(clickY * scaleY);

    onRemoteClick(nativeX, nativeY, 'left');
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (!isInteractive) return;
    e.preventDefault();
    onRemoteScroll(e.deltaX, e.deltaY);
  };

  const handleSendText = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) return;
    onRemoteType(keyInput);
    setKeyInput('');
  };

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      {/* Multi-Tab Bar */}
      <div className="flex items-center space-x-1 px-2.5 sm:px-3 pt-2 bg-slate-950 border-b border-slate-800 overflow-x-auto select-none">
        <div className="flex space-x-1.5 pr-2 items-center flex-shrink-0">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
        </div>

        {/* Tab Items */}
        <div className="flex items-center space-x-1 overflow-x-auto flex-1 min-w-0">
          {tabs.map((tab) => (
            <div
              key={tab.index}
              onClick={() => onSwitchTab(tab.index)}
              className={`flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 rounded-t-lg text-[11px] sm:text-xs cursor-pointer border-t border-x transition max-w-[130px] sm:max-w-[200px] flex-shrink-0 ${
                tab.is_active
                  ? 'bg-slate-900 border-slate-700 text-sky-400 font-semibold'
                  : 'bg-slate-950/80 border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <Globe className="w-3 h-3 flex-shrink-0" />
              <span className="truncate">{tab.title || tab.url || `Tab ${tab.index + 1}`}</span>
              {tabs.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseTab(tab.index);
                  }}
                  className="hover:text-rose-400 rounded p-0.5 ml-1 flex-shrink-0"
                  title="Close tab"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}

          {/* New Tab Button */}
          <button
            onClick={() => onNewTab()}
            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition flex-shrink-0"
            title="Open New Tab"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Viewport Control Bar */}
      <div className="flex items-center justify-between gap-1.5 sm:gap-2 px-2.5 sm:px-4 py-2 bg-slate-950/90 border-b border-slate-800 flex-wrap">
        <span className="text-[10px] sm:text-xs font-mono text-slate-400">
          1280×800 Viewport
        </span>

        {/* Action Toggles */}
        <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
          <button
            onClick={() => setShowOverlay(!showOverlay)}
            className={`flex items-center space-x-1 sm:space-x-1.5 px-2 sm:px-2.5 py-1 rounded text-[11px] sm:text-xs font-medium transition whitespace-nowrap ${
              showOverlay
                ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle Accessibility Element Badges"
          >
            {showOverlay ? <Eye className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> : <EyeOff className="w-3 h-3 sm:w-3.5 sm:h-3.5" />}
            <span>Overlay ({elements.length})</span>
          </button>

          <button
            onClick={() => setInteractiveMode(!interactiveMode)}
            className={`flex items-center space-x-1 sm:space-x-1.5 px-2 sm:px-2.5 py-1 rounded text-[11px] sm:text-xs font-medium transition whitespace-nowrap ${
              isInteractive
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle manual click and keystroke takeover"
          >
            <MousePointer className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
            <span>{isInteractive ? 'Takeover Active' : 'Manual Mode'}</span>
          </button>

          <div className="flex items-center pl-1 text-[11px] sm:text-xs text-slate-400">
            {isConnected ? (
              <span className="flex items-center text-emerald-400 space-x-1">
                <Wifi className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                <span className="hidden xs:inline">Live</span>
              </span>
            ) : (
              <span className="flex items-center text-slate-500 space-x-1">
                <WifiOff className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                <span className="hidden xs:inline">Offline</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Viewport Canvas Container */}
      <div
        ref={containerRef}
        onClick={handleCanvasClick}
        onWheel={handleWheel}
        className={`relative aspect-[16/10] w-full bg-slate-950 flex items-center justify-center select-none overflow-hidden ${
          isInteractive ? 'cursor-crosshair ring-2 ring-amber-500/40' : 'cursor-default'
        }`}
      >
        {frame ? (
          <>
            <img
              src={frame.startsWith('data:') ? frame : `data:image/jpeg;base64,${frame}`}
              alt="Live browser stream"
              className="w-full h-full object-contain pointer-events-none"
            />

            {/* Injected Accessibility Bounding Badges */}
            {showOverlay &&
              elements.map((el) => {
                const padX = 3;
                const padY = 2;
                const leftPct = ((el.x - padX) / 1280) * 100;
                const topPct = ((el.y - padY) / 800) * 100;
                const widthPct = ((el.width + padX * 2) / 1280) * 100;
                const heightPct = ((el.height + padY * 2) / 800) * 100;

                return (
                  <div
                    key={el.id}
                    style={{
                      left: `${leftPct}%`,
                      top: `${topPct}%`,
                      width: `${widthPct}%`,
                      height: `${heightPct}%`,
                    }}
                    className="absolute border border-sky-400/80 bg-sky-500/[0.06] pointer-events-none rounded-[4px] transition-all"
                  >
                    <span className="absolute -top-3.5 left-0 bg-sky-400 text-slate-950 font-mono text-[8px] sm:text-[9px] font-black px-1 rounded-sm leading-none select-none shadow">
                      {el.id}
                    </span>
                  </div>
                );
              })}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-6 sm:p-8 space-y-2.5">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400">
              <MousePointer className="w-5 h-5 sm:w-6 sm:h-6 text-sky-400" />
            </div>
            <div className="text-xs sm:text-sm font-medium text-slate-300">
              Browser Stream Idle
            </div>
            <p className="text-[11px] text-slate-500 max-w-xs">
              Launch a mission below or specify a starting URL to initiate autonomous navigation.
            </p>
          </div>
        )}

        {/* Takeover Active Banner */}
        {isTakeover && (
          <div className="absolute top-2.5 left-1/2 -translate-x-1/2 bg-amber-500/90 text-slate-950 px-3 py-1 rounded-full text-[10px] sm:text-xs font-bold flex items-center space-x-1.5 shadow-lg backdrop-blur animate-bounce">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Human Takeover Active</span>
          </div>
        )}
      </div>

      {/* Manual Remote Input Bar (active in takeover mode) */}
      {isInteractive && (
        <form
          onSubmit={handleSendText}
          className="flex items-center space-x-2 px-3 py-2 bg-slate-950 border-t border-slate-800"
        >
          <span className="text-[11px] font-medium text-amber-400 whitespace-nowrap">Remote Keys:</span>
          <input
            type="text"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="Type text and press Send..."
            className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-400"
          />
          <button
            type="submit"
            className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold rounded flex items-center space-x-1 transition"
          >
            <Send className="w-3 h-3" />
            <span className="hidden sm:inline">Send</span>
          </button>
          <button
            type="button"
            onClick={() => onRemotePress('Enter')}
            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono rounded border border-slate-700"
          >
            ↵ Enter
          </button>
        </form>
      )}
    </div>
  );
};

export default LiveBrowserView;
