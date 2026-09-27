"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";

// API Server configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

interface PlanStep {
  id: number;
  task: string;
  description: string;
  tool_name: string | null;
  dependencies: number[];
  status: "pending" | "running" | "completed" | "failed" | "awaiting_confirmation";
  result: string | null;
}

interface ExecutionPlan {
  goal: string;
  steps: PlanStep[];
}

interface MCPTool {
  server_name: string;
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

interface SpecializedAgent {
  name: string;
  role: string;
  description: string;
  icon: string;
}

const SPECIALIZED_AGENTS: SpecializedAgent[] = [
  { name: "Planner Agent", role: "Orchestration & Task Delegation", description: "Decomposes goals into dependency steps", icon: "📋" },
  { name: "Travel Agent", role: "Travel and Lodging bookings", description: "Handles buses, trains, flights, hotels", icon: "✈️" },
  { name: "Research Agent", role: "Information, weather, and maps retrieval", description: "Gathers directions, local sights, forecasts", icon: "🔍" },
  { name: "Shopping Agent", role: "Product search and purchases", description: "Finds commodities and compares costs", icon: "🛒" },
  { name: "Email Agent", role: "Mail notifications and drafts", description: "Prepares letters and dispatches reports", icon: "✉️" },
  { name: "Calendar Agent", role: "Meeting schedule coordination", description: "Registers calendar time slots", icon: "📅" },
  { name: "Finance Agent", role: "Budgeting and audit analytics", description: "Computes total travel expense sheets", icon: "💳" },
  { name: "Document Agent", role: "Document writes and PDF parses", description: "Handles local logs and PDF reads", icon: "📄" },
  { name: "Browser Agent", role: "Web scrapers and URL search", description: "Navigates hyperlinks and parses text", icon: "🌐" },
  { name: "Memory Agent", role: "Semantic context indexing", description: "Indexes dialogue context into Qdrant", icon: "🧠" }
];

export default function Home() {
  // Authentication & Security States
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [authError, setAuthError] = useState("");
  const [userSession, setUserSession] = useState<{ user_id: string; email: string } | null>(null);

  // Chat Console States
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentTab, setCurrentTab] = useState<"chat" | "tools" | "memory">("chat");

  // Settings Panel States
  const [provider, setProvider] = useState("openai");
  const [mcpServers, setMcpServers] = useState<string[]>([]);
  const [mcpTools, setMcpTools] = useState<MCPTool[]>([]);
  const [selectedServerFilter, setSelectedServerFilter] = useState<string>("all");

  // Multi-Agent Execution State
  const [activePlan, setActivePlan] = useState<ExecutionPlan | null>(null);
  const [traceLogs, setTraceLogs] = useState<{ time: string; msg: string; type: "info" | "success" | "error" }[]>([]);
  const [currentStepId, setCurrentStepId] = useState<number | null>(null);
  const [activeAgentName, setActiveAgentName] = useState<string | null>(null);

  // Human-In-The-Loop Confirmation States
  const [confirmationData, setConfirmationData] = useState<{
    step_id: number;
    tool_name: string;
    arguments: Record<string, unknown>;
    details: string;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchUserProfile = useCallback(async (jwtToken: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${jwtToken}` }
      });
      if (res.ok) {
        const user = await res.json();
        setUserSession(user);
      } else {
        handleLogout();
      }
    } catch {
      handleLogout();
    }
  }, []);

  const fetchMcpServers = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/mcp/servers`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMcpServers(data.servers || []);
      }
    } catch (e) {
      console.error("Failed to fetch MCP servers", e);
    }
  }, [token]);

  const fetchMcpTools = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/mcp/tools`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMcpTools(data.tools || []);
      }
    } catch (e) {
      console.error("Failed to fetch MCP tools", e);
    }
  }, [token]);

  // Initialize Session ID & JWT Token from localStorage on boot
  useEffect(() => {
    setSessionId(`sess_${Math.random().toString(36).substring(2, 11)}`);
    const savedToken = localStorage.getItem("assistant_token");
    if (savedToken) {
      setToken(savedToken);
      fetchUserProfile(savedToken);
    }
  }, [fetchUserProfile]);

  // Fetch servers & tools list once authenticated
  useEffect(() => {
    if (token) {
      fetchMcpServers();
      fetchMcpTools();
    }
  }, [token, fetchMcpServers, fetchMcpTools]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, traceLogs]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        localStorage.setItem("assistant_token", data.access_token);
        setToken(data.access_token);
        fetchUserProfile(data.access_token);
      } else {
        const err = await res.json();
        setAuthError(err.detail || "Authentication failed. Check credentials.");
      }
    } catch {
      setAuthError("Failed to connect to authentication server.");
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      if (res.ok) {
        setIsRegistering(false);
        setPassword("");
        setAuthError("Registration successful! Please login.");
      } else {
        const err = await res.json();
        setAuthError(err.detail || "Registration failed.");
      }
    } catch {
      setAuthError("Failed to connect to authentication server.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("assistant_token");
    setToken(null);
    setUserSession(null);
    setMcpServers([]);
    setMcpTools([]);
    setMessages([]);
    setActivePlan(null);
    setTraceLogs([]);
    setActiveAgentName(null);
    setConfirmationData(null);
  };

  // SSE Stream Processing Helper
  const processStream = async (reader: ReadableStreamDefaultReader<Uint8Array>) => {
    const decoder = new TextDecoder();
    let buffer = "";
    let assistantResponse = "";

    const addTraceLog = (msg: string, type: "info" | "success" | "error" = "info") => {
      const time = new Date().toLocaleTimeString();
      setTraceLogs(prev => [...prev, { time, msg, type }]);
    };

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const eventData = JSON.parse(jsonStr);

              switch (eventData.event) {
                case "status":
                  addTraceLog(eventData.message, "info");
                  break;

                case "plan_created":
                  addTraceLog("Planner Agent generated dependency task plan graph.", "success");
                  setActivePlan(eventData.plan);
                  break;

                case "agent_active":
                  setActiveAgentName(eventData.agent_name);
                  break;

                case "step_started":
                  setCurrentStepId(eventData.step_id);
                  addTraceLog(`Step ${eventData.step_id} execution started: ${eventData.task}`);
                  setActivePlan(prev => {
                    if (!prev) return null;
                    return {
                      ...prev,
                      steps: prev.steps.map(s =>
                        s.id === eventData.step_id ? { ...s, status: "running" } : s
                      )
                    };
                  });
                  break;

                case "awaiting_confirmation":
                  addTraceLog(`Awaiting User Confirmation for tool: ${eventData.tool_name}`, "info");
                  setConfirmationData({
                    step_id: eventData.step_id,
                    tool_name: eventData.tool_name,
                    arguments: eventData.arguments,
                    details: eventData.details
                  });
                  setActivePlan(prev => {
                    if (!prev) return null;
                    return {
                      ...prev,
                      steps: prev.steps.map(s =>
                        s.id === eventData.step_id ? { ...s, status: "awaiting_confirmation" } : s
                      )
                    };
                  });
                  setIsExecuting(false);
                  return; // Suspend processing, prompt user

                case "tool_output":
                  addTraceLog(`Tool ${eventData.tool_name} returned output successfully.`, "success");
                  setActivePlan(prev => {
                    if (!prev) return null;
                    return {
                      ...prev,
                      steps: prev.steps.map(s =>
                        s.id === eventData.step_id ? { ...s, result: eventData.output } : s
                      )
                    };
                  });
                  break;

                case "step_completed":
                  addTraceLog(`Step ${eventData.step_id} completed successfully.`, "success");
                  setActivePlan(prev => {
                    if (!prev) return null;
                    return {
                      ...prev,
                      steps: prev.steps.map(s =>
                        s.id === eventData.step_id ? { ...s, status: "completed", result: eventData.result } : s
                      )
                    };
                  });
                  break;

                case "step_failed":
                  addTraceLog(`Step ${eventData.step_id} failed: ${eventData.error}`, "error");
                  setActivePlan(prev => {
                    if (!prev) return null;
                    return {
                      ...prev,
                      steps: prev.steps.map(s =>
                        s.id === eventData.step_id ? { ...s, status: "failed", result: eventData.error } : s
                      )
                    };
                  });
                  break;

                case "chunk":
                  assistantResponse += eventData.text;
                  setMessages(prev => {
                    const next = [...prev];
                    if (next.length > 0) {
                      next[next.length - 1] = {
                        ...next[next.length - 1],
                        content: assistantResponse
                      };
                    }
                    return next;
                  });
                  break;

                case "done":
                  addTraceLog("Orchestrator completed entire task pipeline successfully.", "success");
                  setCurrentStepId(null);
                  setActiveAgentName(null);
                  break;
              }
            } catch (err) {
              console.error("JSON parse failure on SSE buffer line:", line, err);
            }
          }
        }
      }
    } catch (e) {
      console.error(e);
      const errMsg = e instanceof Error ? e.message : String(e);
      addTraceLog(`Connection error during streaming: ${errMsg}`, "error");
    } finally {
      setIsExecuting(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isExecuting) return;

    const userPrompt = inputMessage;
    setInputMessage("");
    setIsExecuting(true);
    setConfirmationData(null);
    setTraceLogs([]);
    setActivePlan(null);
    setCurrentStepId(null);
    setActiveAgentName("Planner Agent");

    // Add user message
    setMessages(prev => [
      ...prev,
      { role: "user", content: userPrompt, timestamp: new Date().toLocaleTimeString() }
    ]);

    // Setup empty assistant bubble for chunks
    setMessages(prev => [
      ...prev,
      { role: "assistant", content: "", timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      const res = await fetch(`${API_BASE_URL}/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ message: userPrompt, session_id: sessionId })
      });

      if (!res.body) throw new Error("Null response stream");
      await processStream(res.body.getReader());
    } catch (err) {
      console.error(err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setMessages(prev => {
        const next = [...prev];
        if (next.length > 0) {
          next[next.length - 1] = {
            ...next[next.length - 1],
            content: `Failed to connect with agent gateway: ${errMsg}`
          };
        }
        return next;
      });
      setIsExecuting(false);
    }
  };

  // Human in the loop confirmation submission
  const handleConfirmAction = async (approved: boolean) => {
    if (!confirmationData) return;

    const suspendedStep = confirmationData.step_id;
    setConfirmationData(null);
    setIsExecuting(true);

    // If approved, create a loader assistant bubble or edit last message depending on stream
    try {
      const res = await fetch(`${API_BASE_URL}/agent/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          step_id: suspendedStep,
          approved: approved
        })
      });

      if (!res.body) throw new Error("Null response stream body");
      await processStream(res.body.getReader());
    } catch (err) {
      console.error("Resume error", err);
      setIsExecuting(false);
    }
  };

  const filteredTools = selectedServerFilter === "all"
    ? mcpTools
    : mcpTools.filter(t => t.server_name === selectedServerFilter);

  // AUTHENTICATION LOGIN PAGE
  if (!token) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 p-4 relative overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />

        <div className="w-full max-w-md backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl p-8 shadow-2xl z-10">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-extrabold bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Universal Agent OS
            </h1>
            <p className="text-slate-400 text-sm mt-2">Autonomous Multi-Agent AI Core Control Panel</p>
          </div>

          <form onSubmit={isRegistering ? handleRegister : handleLogin} className="space-y-6">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Developer Profile Email
              </label>
              <input
                type="email"
                required
                className="w-full bg-slate-900 border border-white/10 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
                placeholder="developer@agentic.ai"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Secure Key Password
              </label>
              <input
                type="password"
                required
                className="w-full bg-slate-900 border border-white/10 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>

            {authError && (
              <div className="text-sm font-medium text-rose-400 bg-rose-500/10 border border-rose-500/20 px-4 py-2.5 rounded-lg">
                {authError}
              </div>
            )}

            <button
              type="submit"
              className="w-full bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-semibold py-3 px-4 rounded-lg shadow-lg shadow-violet-600/20 transition-all hover:scale-[1.01]"
            >
              {isRegistering ? "Create Developer Profile" : "Initialize Agent System"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-400">
            {isRegistering ? (
              <p>
                Access existing system?{" "}
                <button onClick={() => setIsRegistering(false)} className="text-violet-400 hover:underline">
                  Log In
                </button>
              </p>
            ) : (
              <p>
                Register a new operator profile?{" "}
                <button onClick={() => setIsRegistering(true)} className="text-cyan-400 hover:underline">
                  Create Profile
                </button>
              </p>
            )}
          </div>
        </div>
      </main>
    );
  }

  // MAIN COGNITIVE OS DASHBOARD
  return (
    <main className="min-h-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden relative">
      {/* Top OS Menu Bar */}
      <header className="h-14 flex items-center justify-between border-b border-white/10 px-6 backdrop-blur-md bg-slate-950/80 z-20 shrink-0">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-glow shadow-emerald-500/40" />
          <h1 className="text-md font-extrabold bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent tracking-tight">
            Universal Agent OS
          </h1>
          <span className="text-[10px] bg-white/5 border border-white/10 text-slate-400 px-2 py-0.5 rounded-full">
            Active session: <span className="font-mono text-slate-300">{sessionId}</span>
          </span>
        </div>
        
        {/* Navigation tabs */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentTab("chat")}
            className={`text-xs font-semibold px-4 py-2 rounded-lg border transition-all ${
              currentTab === "chat"
                ? "bg-violet-600/20 text-violet-300 border-violet-500/30"
                : "bg-transparent text-slate-400 border-transparent hover:text-slate-200"
            }`}
          >
            💬 Chat Panel
          </button>
          <button
            onClick={() => setCurrentTab("tools")}
            className={`text-xs font-semibold px-4 py-2 rounded-lg border transition-all ${
              currentTab === "tools"
                ? "bg-violet-600/20 text-violet-300 border-violet-500/30"
                : "bg-transparent text-slate-400 border-transparent hover:text-slate-200"
            }`}
          >
            ⚙️ MCP Tools ({mcpTools.length})
          </button>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-xs text-slate-400">
            Operator: <span className="text-slate-200 font-medium">{userSession?.email || "developer"}</span>
          </div>
          <button
            onClick={handleLogout}
            className="text-[11px] font-semibold bg-white/5 hover:bg-rose-500/20 hover:text-rose-300 border border-white/10 hover:border-rose-500/30 px-3 py-1.5 rounded-md transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Main Panel Content */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Side: Configuration & Settings */}
        <aside className="w-80 border-r border-white/10 flex flex-col bg-slate-950/40 shrink-0">
          <div className="p-4 border-b border-white/10 space-y-4">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              LLM Provider Gateway
            </h2>
            <div>
              <select
                value={provider}
                onChange={e => setProvider(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-lg py-2.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-violet-500"
              >
                <option value="openai">OpenAI Gateway (GPT-4o)</option>
                <option value="anthropic">Anthropic Gateway (Claude 3.5)</option>
                <option value="gemini">Google Gateway (Gemini 1.5 Pro)</option>
              </select>
            </div>
          </div>

          {/* Active MCP Servers Discovery list */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-white/10 bg-slate-900/10 flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-300 uppercase">MCP Server Clusters</h3>
              <span className="text-[10px] bg-violet-600/10 text-violet-300 border border-violet-500/20 px-2 py-0.5 rounded-full">
                {mcpServers.length} Active
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
              {mcpServers.map(serv => (
                <div
                  key={serv}
                  className="flex items-center justify-between p-2.5 bg-white/5 border border-white/5 rounded-lg hover:border-violet-500/20 transition-all"
                >
                  <span className="text-xs font-bold text-slate-300 font-mono">{serv}</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow shadow-emerald-500" />
                </div>
              ))}
              {mcpServers.length === 0 && (
                <div className="text-xs text-slate-500 text-center py-6">
                  No MCP servers connected on lifespan setup.
                </div>
              )}
            </div>
          </div>
        </aside>

        {/* Center Section: Tab Panels (Chat / MCP Tool Inspector) */}
        <section className="flex-1 flex flex-col bg-slate-900/5 relative overflow-hidden">
          
          {/* TAB 1: Chat Console + Live Graph */}
          {currentTab === "chat" && (
            <div className="flex-1 flex flex-col overflow-hidden">
              
              {/* SVG Dependency workflow graph visualizer */}
              {activePlan && (
                <div className="h-32 border-b border-white/10 bg-slate-950/80 p-3 shrink-0 overflow-x-auto relative flex items-center gap-4 custom-scrollbar">
                  <div className="absolute left-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider top-2">
                    Execution DAG Graph Visualizer
                  </div>
                  <div className="flex items-center gap-8 pl-4 py-2 mt-4 min-w-max">
                    {activePlan.steps.map((step, idx) => {
                      const isCompleted = step.status === "completed";
                      const isRunning = step.status === "running";
                      const isFailed = step.status === "failed";
                      const isAwaiting = step.status === "awaiting_confirmation";
                      
                      return (
                        <div key={step.id} className="flex items-center gap-6 relative">
                          <div
                            className={`px-3 py-2 border rounded-lg text-xs flex flex-col shadow-lg z-10 w-44 transition-all ${
                              isRunning
                                ? "bg-violet-600/10 border-violet-500 text-violet-200 animate-pulse"
                                : isCompleted
                                ? "bg-emerald-500/5 border-emerald-500/30 text-emerald-300"
                                : isFailed
                                ? "bg-rose-500/5 border-rose-500/30 text-rose-300"
                                : isAwaiting
                                ? "bg-amber-500/10 border-amber-500 text-amber-300 font-bold"
                                : "bg-slate-900 border-white/5 text-slate-400"
                            }`}
                          >
                            <span className="text-[9px] uppercase font-bold text-slate-500 mb-0.5">
                              Step {step.id} {isCompleted && "✓"} {isFailed && "✗"}
                            </span>
                            <span className="font-semibold truncate">{step.task}</span>
                            <span className="text-[9px] text-slate-500 truncate mt-1">
                              {step.tool_name || "Reasoning"}
                            </span>
                          </div>
                          {idx < activePlan.steps.length - 1 && (
                            <svg className="w-6 h-4 text-slate-700 shrink-0" fill="none" viewBox="0 0 24 16">
                              <path d="M0 8H20M20 8L14 2M20 8L14 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                            </svg>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Chat timeline feed */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                {messages.length <= 1 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-6">
                    <div className="w-16 h-16 bg-gradient-to-tr from-violet-600 to-cyan-500 rounded-2xl flex items-center justify-center shadow-xl shadow-violet-600/20">
                      <span className="text-2xl font-black">⚙️</span>
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold">Initialize AI Agent Goal</h3>
                      <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                        Enter your request (e.g. <span className="text-slate-200 font-medium">&quot;I want to visit Bangalore next weekend&quot;</span>). The Planner Agent will distribute tasks across Travel, Hotel, and Weather MCP servers while gating purchases with Human-in-the-loop validation overlays.
                      </p>
                    </div>
                  </div>
                ) : (
                  messages
                    .filter(m => m.role !== "system")
                    .map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex gap-4 p-4 rounded-xl transition-all ${
                          msg.role === "user"
                            ? "bg-slate-900/40 border border-white/5 ml-12"
                            : "bg-white/5 border border-white/10 mr-12"
                        }`}
                      >
                        <div className="text-xl">
                          {msg.role === "user" ? "👨‍💻" : "🤖"}
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="text-xs text-slate-500 font-bold uppercase tracking-wider">
                            {msg.role === "user" ? "Operator console" : "Orchestrator feedback"}
                          </div>
                          <div className="text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">
                            {msg.content || (
                              <span className="flex items-center gap-1.5 text-slate-500">
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Suspended Human Confirmation Gate Overlay */}
              {confirmationData && (
                <div className="p-4 mx-6 mb-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex flex-col gap-3 shadow-lg shadow-amber-500/5 animate-fade-in">
                  <div className="flex items-center gap-2 text-amber-400 font-bold text-sm">
                    <span>⚠️ Human-In-The-Loop Validation Required</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {confirmationData.details}
                  </p>
                  <div className="flex gap-3 mt-1.5">
                    <button
                      onClick={() => handleConfirmAction(true)}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-4 py-2 rounded-lg shadow transition-all hover:scale-[1.01]"
                    >
                      ✓ Approve Booking
                    </button>
                    <button
                      onClick={() => handleConfirmAction(false)}
                      className="bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 font-semibold text-xs px-4 py-2 rounded-lg border border-rose-500/20 transition-all"
                    >
                      ✗ Reject Transaction
                    </button>
                  </div>
                </div>
              )}

              {/* Chat Input Console Bar */}
              <div className="p-4 border-t border-white/10 bg-slate-950/40 shrink-0">
                <form onSubmit={handleSendMessage} className="flex gap-3">
                  <input
                    type="text"
                    disabled={isExecuting || !!confirmationData}
                    className="flex-1 bg-slate-900 border border-white/10 rounded-xl px-5 py-3.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
                    placeholder={
                      isExecuting
                        ? "Agent pipeline executing..."
                        : confirmationData
                        ? "Awaiting your validation approval above..."
                        : "Describe travel plans or database queries..."
                    }
                    value={inputMessage}
                    onChange={e => setInputMessage(e.target.value)}
                  />
                  <button
                    type="submit"
                    disabled={isExecuting || !inputMessage.trim() || !!confirmationData}
                    className="bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white text-xs font-semibold px-6 rounded-xl transition-all shadow-lg shadow-violet-600/10 flex items-center justify-center disabled:opacity-40 disabled:scale-100 hover:scale-[1.02]"
                  >
                    Execute Goal
                  </button>
                </form>
              </div>

              {/* Interactive Execution Traces Console Logs panel */}
              {(activePlan || traceLogs.length > 0) && (
                <div className="h-44 border-t border-white/10 bg-slate-950/95 font-mono text-[10px] p-4 flex flex-col overflow-hidden shrink-0 z-10">
                  <div className="text-slate-500 uppercase tracking-widest font-bold mb-2">
                    System Execution Traces
                  </div>
                  <div className="flex-1 overflow-y-auto space-y-1.5 text-slate-300 custom-scrollbar pr-2">
                    {traceLogs.map((log, index) => (
                      <div key={index} className="flex gap-2.5 items-start">
                        <span className="text-slate-600 shrink-0">{log.time}</span>
                        <span className={
                          log.type === "success" 
                            ? "text-emerald-400" 
                            : log.type === "error" 
                            ? "text-rose-400" 
                            : "text-slate-400"
                        }>
                          {log.msg}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: MCP Discovery List */}
          {currentTab === "tools" && (
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="p-4 border-b border-white/10 bg-slate-950/20 flex items-center justify-between shrink-0">
                <h3 className="text-sm font-bold text-slate-300 uppercase">MCP Discovered Tools</h3>
                <select
                  value={selectedServerFilter}
                  onChange={e => setSelectedServerFilter(e.target.value)}
                  className="bg-slate-900 border border-white/10 rounded px-3 py-1.5 text-xs text-slate-400 focus:outline-none"
                >
                  <option value="all">All Servers</option>
                  {mcpServers.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-2 gap-4 custom-scrollbar">
                {filteredTools.map(tool => (
                  <div
                    key={tool.name}
                    className="p-4 bg-white/5 border border-white/5 hover:border-violet-500/20 rounded-xl transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="font-mono text-sm font-bold text-violet-400">{tool.name}</span>
                        <span className="text-[9px] bg-slate-900 border border-white/10 text-slate-400 px-2 py-0.5 rounded-full font-mono">
                          {tool.server_name}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed mb-4">
                        {tool.description}
                      </p>
                    </div>
                    {/* Render input schema variables if any */}
                    <div className="bg-slate-950/45 p-3 rounded-lg border border-white/5">
                      <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1">Parameters Schema</span>
                      <pre className="text-[10px] text-slate-400 font-mono overflow-x-auto">
                        {JSON.stringify(tool.input_schema, null, 2)}
                      </pre>
                    </div>
                  </div>
                ))}
                {filteredTools.length === 0 && (
                  <div className="text-sm text-slate-500 text-center col-span-2 py-12">
                    No MCP tools found under selected filter.
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Right Sidebar: Active Agents Lights Panel */}
        <aside className="w-80 border-l border-white/10 flex flex-col bg-slate-950/20 shrink-0 overflow-y-auto custom-scrollbar">
          <div className="p-4 border-b border-white/10 shrink-0">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              Specialized Agents Panel
            </h2>
          </div>
          <div className="p-4 space-y-3">
            {SPECIALIZED_AGENTS.map(agent => {
              const isActive = activeAgentName === agent.name;
              
              return (
                <div
                  key={agent.name}
                  className={`p-3.5 rounded-xl border transition-all duration-300 relative overflow-hidden flex items-center gap-3 ${
                    isActive
                      ? "bg-violet-600/10 border-violet-500/40 shadow shadow-violet-600/10 scale-[1.01]"
                      : "bg-white/5 border-white/5 opacity-70 hover:opacity-100"
                  }`}
                >
                  <div className="text-2xl shrink-0">{agent.icon}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-bold text-slate-200 truncate">{agent.name}</span>
                      {isActive && (
                        <span className="w-2 h-2 rounded-full bg-violet-400 animate-ping shrink-0" />
                      )}
                    </div>
                    <p className="text-[9px] text-slate-500 truncate mt-0.5">{agent.role}</p>
                    <p className="text-[10px] text-slate-400 truncate mt-1 leading-normal">{agent.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </aside>
      </div>
    </main>
  );
}
