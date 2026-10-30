export interface ActionCommand {
  action: "click" | "type" | "press_key" | "scroll" | "select" | "wait" | "goto" | "finish" | "fail";
  element_id: number | null;
  text: string | null;
  key: string | null;
  press_enter: boolean;
  direction: "up" | "down" | null;
  amount: number | null;
  url: string | null;
  seconds: number | null;
  reasoning: string;
  answer: string | null;
}

export interface VerificationResult {
  success: boolean;
  changed_url: boolean;
  new_url: string;
  dom_changed: boolean;
  detected_error: string | null;
  recovery_suggestion: string | null;
}

export interface AgentStep {
  step_number: number;
  url: string;
  title: string;
  thought: string;
  action: ActionCommand;
  verification: VerificationResult | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  screenshot_base64: string | null;
}

export interface SessionStatus {
  session_id: string | null;
  status: "idle" | "running" | "paused" | "completed" | "stopped" | "takeover";
  goal: string;
  total_steps: number;
  total_tokens: number;
  total_cost_usd: number;
  takeover_required: boolean;
  final_answer: string | null;
}

export interface ActionableElement {
  id: number;
  role: string;
  name: string;
  value: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  is_focused?: boolean;
}
