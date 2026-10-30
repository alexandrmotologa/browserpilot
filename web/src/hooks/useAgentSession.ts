import { useState, useEffect, useRef, useCallback } from 'react';
import { AgentStep, SessionStatus, ActionableElement } from '../types';

export function useAgentSession() {
  const [viewportFrame, setViewportFrame] = useState<string | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [status, setStatus] = useState<SessionStatus>({
    session_id: null,
    status: 'idle',
    goal: '',
    total_steps: 0,
    total_tokens: 0,
    total_cost_usd: 0,
    takeover_required: false,
    final_answer: null,
  });
  const [takeoverChallenge, setTakeoverChallenge] = useState<string | null>(null);
  const [activeElements, setActiveElements] = useState<ActionableElement[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  // Poll current session status and DOM elements
  const refreshStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/sessions/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        if (data.takeover_required) {
          setTakeoverChallenge('challenge');
        }
      }
    } catch {
      // Server may still be starting
    }
  }, []);

  const refreshDomTree = useCallback(async () => {
    try {
      const res = await fetch('/api/dom/tree');
      if (res.ok) {
        const data = await res.json();
        setActiveElements(data);
      }
    } catch {
      // Browser might be closed or busy
    }
  }, []);

  // Connect WebSocket
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/telemetry`;

    function connect() {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        refreshStatus();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'viewport_frame' && msg.frame) {
            setViewportFrame(msg.frame);
          } else if (msg.type === 'step_update' && msg.step) {
            setSteps((prev) => [...prev, msg.step]);
            setStatus((prev) => ({
              ...prev,
              total_steps: msg.step.step_number,
              total_tokens: prev.total_tokens + msg.step.total_tokens,
              total_cost_usd: prev.total_cost_usd + msg.step.cost_usd,
            }));
            refreshDomTree();
          } else if (msg.type === 'human_takeover_required') {
            setTakeoverChallenge(msg.challenge_type || 'verification');
            setStatus((prev) => ({ ...prev, takeover_required: true, status: 'takeover' }));
          } else if (msg.type === 'session_paused') {
            setStatus((prev) => ({ ...prev, status: 'paused' }));
          } else if (msg.type === 'session_resumed') {
            setTakeoverChallenge(null);
            setStatus((prev) => ({ ...prev, takeover_required: false, status: 'running' }));
          } else if (msg.type === 'session_stopped') {
            setStatus((prev) => ({ ...prev, status: 'stopped' }));
          } else if (msg.type === 'session_completed') {
            setStatus((prev) => ({
              ...prev,
              status: 'completed',
              final_answer: msg.final_answer,
            }));
          }
        } catch {
          // Non-JSON frame
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimeoutRef.current = window.setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [refreshStatus, refreshDomTree]);

  // Remote interactive actions
  const sendRemoteClick = useCallback((x: number, y: number, button = 'left') => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mouse_click', x, y, button }));
    }
  }, []);

  const sendRemoteMove = useCallback((x: number, y: number) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mouse_move', x, y }));
    }
  }, []);

  const sendRemoteScroll = useCallback((deltaX: number, deltaY: number) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'mouse_scroll', delta_x: deltaX, delta_y: deltaY }));
    }
  }, []);

  const sendRemoteType = useCallback((text: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'keyboard_type', text }));
    }
  }, []);

  const sendRemotePress = useCallback((key: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'keyboard_press', key }));
    }
  }, []);

  const startSession = useCallback(async (goal: string, startUrl?: string, model?: string) => {
    setSteps([]);
    setTakeoverChallenge(null);
    const res = await fetch('/api/sessions/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal, start_url: startUrl, model }),
    });
    if (res.ok) {
      const data = await res.json();
      setStatus(data);
    }
  }, []);

  const pauseSession = useCallback(async () => {
    await fetch('/api/sessions/pause', { method: 'POST' });
    setStatus((prev) => ({ ...prev, status: 'paused' }));
  }, []);

  const resumeSession = useCallback(async () => {
    await fetch('/api/sessions/resume', { method: 'POST' });
    setTakeoverChallenge(null);
    setStatus((prev) => ({ ...prev, takeover_required: false, status: 'running' }));
  }, []);

  const stopSession = useCallback(async () => {
    await fetch('/api/sessions/stop', { method: 'POST' });
    setStatus((prev) => ({ ...prev, status: 'stopped' }));
  }, []);

  return {
    viewportFrame,
    steps,
    status,
    takeoverChallenge,
    activeElements,
    isConnected,
    sendRemoteClick,
    sendRemoteMove,
    sendRemoteScroll,
    sendRemoteType,
    sendRemotePress,
    startSession,
    pauseSession,
    resumeSession,
    stopSession,
  };
}
