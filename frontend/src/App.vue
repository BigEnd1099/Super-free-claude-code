<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { 
  Activity, 
  Cpu, 
  Database, 
  LayoutDashboard, 
  Settings, 
  Users,
  Shield,
  Zap,
  MoreHorizontal,
  Brain,
  FileText
} from 'lucide-vue-next'
import SkillPicker from './components/SkillPicker.vue'

const stats = ref({
  cpu: 0,
  memory: 0,
  uptime: 0,
  status: 'connecting',
  provider: 'nvidia_nim',
  model: 'z-ai/glm4.7',
  agentsCount: 0,
  optimizedRequests: 0
})

const agents = ref([])
const activeTab = ref('dashboard')
const modelMapping = ref({
  opus: '',
  sonnet: '',
  haiku: ''
})

let pulseSource = null

const connectPulse = () => {
  pulseSource = new EventSource('/pulse')
  pulseSource.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data)
        stats.value = { ...stats.value, ...data }
        stats.value.status = 'online'
    } catch (e) {
        console.error('Failed to parse pulse data', e)
    }
  }
  pulseSource.onerror = () => {
    stats.value.status = 'offline'
  }
}

const fetchAgents = async () => {
  try {
    const res = await fetch('/v1/agents')
    const data = await res.json()
    agents.value = data.data
    stats.value.agentsCount = agents.value.length
  } catch (e) {
    console.error('Failed to fetch agents', e)
  }
}

const saveMapping = async () => {
  try {
    await fetch('/config/mapping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(modelMapping.value)
    })
    alert('Mapping updated!')
  } catch (e) {
    alert('Failed to update mapping')
  }
}

onMounted(() => {
  connectPulse()
  fetchAgents()
})

onUnmounted(() => {
  if (pulseSource) pulseSource.close()
})

const formatUptime = (seconds) => {
  if (!seconds) return '0h 0m 0s'
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hrs}h ${mins}m ${secs}s`
}
</script>

<template>
  <div class="app-container">
    <aside class="sidebar">
      <div class="logo">
        <Shield class="text-blue-500" :size="32" />
        <span class="text">ANTIGRAVITY</span>
      </div>
      
      <nav>
        <button 
          @click="activeTab = 'dashboard'"
          :class="['nav-item', activeTab === 'dashboard' ? 'active' : '']"
        >
          <LayoutDashboard :size="20" /> Dashboard
        </button>
        <button 
          @click="activeTab = 'agents'"
          :class="['nav-item', activeTab === 'agents' ? 'active' : '']"
        >
          <Users :size="20" /> Managed Agents
        </button>
        <button 
          @click="activeTab = 'skills'"
          :class="['nav-item', activeTab === 'skills' ? 'active' : '']"
        >
          <Brain :size="20" /> Skills Library
        </button>
        <button 
          @click="activeTab = 'logs'"
          :class="['nav-item', activeTab === 'logs' ? 'active' : '']"
        >
          <FileText :size="20" /> System Logs
        </button>
        <button 
          @click="activeTab = 'config'"
          :class="['nav-item', activeTab === 'config' ? 'active' : '']"
        >
          <Settings :size="20" /> Configuration
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="status-indicator">
          <div :class="['pulse-dot', stats.status]"></div>
          <span class="capitalize">Server {{ stats.status }}</span>
        </div>
      </div>
    </aside>

    <main class="content">
      <!-- Dashboard Tab -->
      <section v-if="activeTab === 'dashboard'" class="tab-content active">
        <header class="tab-header">
          <h1>Dashboard</h1>
          <p class="subtitle">Real-time status of your Claude Code Proxy</p>
        </header>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Active Provider</div>
            <div class="stat-value">{{ stats.provider }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Model Fallback</div>
            <div class="stat-value">{{ stats.model }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Agents Count</div>
            <div class="stat-value">{{ stats.agentsCount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Optimized Requests</div>
            <div class="stat-value">{{ stats.optimizedRequests }}</div>
          </div>
        </div>

        <div class="dashboard-grid">
          <div class="visual-panel">
            <div class="panel-header">System Health</div>
            <div class="health-meters">
              <div class="meter">
                <label>CPU Load</label>
                <div class="bar-container"><div class="bar" :style="{ width: stats.cpu + '%' }"></div></div>
                <span class="meter-val">{{ stats.cpu }}%</span>
              </div>
              <div class="meter">
                <label>Memory matrix</label>
                <div class="bar-container"><div class="bar" :style="{ width: stats.memory + '%' }"></div></div>
                <span class="meter-val">{{ stats.memory }}%</span>
              </div>
              <div class="meter mt-4">
                <label>System Uptime</label>
                <p class="font-mono text-blue-400 text-sm">{{ formatUptime(stats.uptime) }}</p>
              </div>
            </div>
          </div>

          <div class="visual-panel">
            <div class="panel-header">Model Mapping</div>
            <div class="mapping-list">
              <div class="mapping-item">
                <span>Opus Override</span>
                <input v-model="modelMapping.opus" type="text" placeholder="provider/model">
              </div>
              <div class="mapping-item">
                <span>Sonnet Override</span>
                <input v-model="modelMapping.sonnet" type="text" placeholder="provider/model">
              </div>
              <div class="mapping-item">
                <span>Haiku Override</span>
                <input v-model="modelMapping.haiku" type="text" placeholder="provider/model">
              </div>
              <button @click="saveMapping" class="btn btn-primary btn-sm">Update Map</button>
            </div>
          </div>
        </div>
      </section>

      <!-- Agents Tab -->
      <section v-else-if="activeTab === 'agents'" class="tab-content active">
        <header class="tab-header">
          <div class="header-actions">
            <div>
              <h1>Managed Agents</h1>
              <p class="subtitle">Manage your custom personas and identities</p>
            </div>
            <button class="btn btn-primary">+ Create Agent</button>
          </div>
        </header>

        <div class="agents-list">
          <div v-for="agent in agents" :key="agent.id" class="agent-card">
            <div class="agent-card-header">
              <div class="agent-info">
                <span class="agent-name">{{ agent.name }}</span>
                <span class="agent-model">{{ agent.model }}</span>
              </div>
              <Users :size="24" class="text-slate-600" />
            </div>
            <p class="agent-desc">{{ agent.description || 'No description provided.' }}</p>
            <div class="agent-skills">
              <span v-for="skill in agent.skills" :key="skill" class="skill-pill">{{ skill }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Skills Tab -->
      <section v-else-if="activeTab === 'skills'" class="tab-content active">
        <header class="tab-header">
          <h1>Neural Skills</h1>
          <p class="subtitle">Search and select from 1,200+ specialized expansion modules.</p>
        </header>
        <SkillPicker />
      </section>

      <!-- Logs Tab -->
      <section v-else-if="activeTab === 'logs'" class="tab-content active">
        <header class="tab-header">
          <h1>System Logs</h1>
          <p class="subtitle">Live traffic and proxy activity</p>
        </header>
        <div class="log-viewer">
          <div class="log-content">
            <div class="log-line"><span class="log-time">[00:45:12]</span> <span class="log-tag success">SUCCESS</span> Provider NVIDIA_NIM handshake verified.</div>
            <div class="log-line"><span class="log-time">[00:45:15]</span> <span class="log-tag info">INFO</span> Agent Orchestrator v2.0 synchronized.</div>
            <div class="log-line"><span class="log-time">[00:45:18]</span> <span class="log-tag link">LINK</span> Pulse SSE established on port 8082.</div>
          </div>
        </div>
      </section>

      <!-- Config Tab -->
      <section v-else-if="activeTab === 'config'" class="tab-content active">
        <header class="tab-header">
          <h1>Configuration</h1>
          <p class="subtitle">Manage your environment variables and keys</p>
        </header>
        <div class="config-grid">
          <div class="config-card">
            <h3>API Keys</h3>
            <div class="form-group">
              <label>NVIDIA NIM Key</label>
              <input type="password" value="************************" disabled>
              <small class="text-muted">Set via environment variable</small>
            </div>
            <div class="form-group">
              <label>Anthropic Auth Token</label>
              <input type="text" placeholder="Optional">
              <small class="text-muted">Optional authentication token</small>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
:root {
  --bg-primary: #0a0b10;
  --bg-secondary: rgba(20, 22, 32, 0.8);
  --bg-accent: rgba(30, 34, 48, 0.6);
  --bg-glass: rgba(20, 22, 32, 0.6);
  --text-primary: #ffffff;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-secondary: #a855f7;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --sidebar-width: 260px;
  --border-radius: 12px;
  --border-radius-lg: 16px;
  --glow-color: rgba(59, 130, 246, 0.3);
  --transition-normal: 200ms ease;
}

body {
  margin: 0;
  font-family: 'Inter', -apple-system, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  overflow: hidden;
}

.app-container {
  display: flex;
  height: 100vh;
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background: linear-gradient(180deg, rgba(20, 22, 32, 0.9) 0%, rgba(10, 11, 16, 0.95) 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  padding: 2rem 1.5rem;
  backdrop-filter: blur(12px);
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 3rem;
  font-size: 1.25rem;
  font-weight: 800;
  letter-spacing: 1px;
}

nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex-grow: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border-radius: var(--border-radius);
  color: var(--text-secondary);
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: var(--transition-normal);
  font-weight: 500;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.nav-item.active {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

/* Content Area */
.content {
  flex-grow: 1;
  padding: 3rem;
  overflow-y: auto;
}

.tab-header {
  margin-bottom: 3rem;
}

.tab-header h1 {
  font-size: 2.5rem;
  font-weight: 800;
  margin: 0;
}

.subtitle {
  color: var(--text-secondary);
  margin-top: 0.5rem;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  margin-bottom: 2.5rem;
}

.stat-card {
  background: var(--bg-secondary);
  padding: 1.5rem;
  border-radius: var(--border-radius);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.stat-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 700;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.visual-panel {
  background: var(--bg-glass);
  border-radius: var(--border-radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 1.5rem;
}

.panel-header {
  font-weight: 700;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.health-meters {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.meter label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  display: block;
  margin-bottom: 0.5rem;
}

.bar-container {
  height: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  background: var(--color-primary);
  transition: width 0.5s ease;
}

.meter-val {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
  display: block;
}

/* Forms & Buttons */
.mapping-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mapping-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mapping-item span {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

input {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.875rem;
  width: 200px;
}

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  align-self: flex-end;
}

/* Agents List */
.agents-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.agent-card {
  background: var(--bg-secondary);
  border-radius: var(--border-radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
}

.agent-card-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.agent-info {
  display: flex;
  flex-direction: column;
}

.agent-name {
  font-weight: 700;
  font-size: 1.1rem;
}

.agent-model {
  font-size: 0.75rem;
  color: var(--color-primary);
  font-family: monospace;
}

.agent-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
  line-clamp: 2;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.agent-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.skill-pill {
  font-size: 0.7rem;
  padding: 0.25rem 0.6rem;
  background: rgba(59, 130, 246, 0.1);
  color: var(--color-primary);
  border-radius: 10px;
  font-weight: 600;
}

/* Logs */
.log-viewer {
  background: #000;
  border-radius: 12px;
  padding: 1.5rem;
  font-family: 'JetBrains Mono', monospace;
  height: 500px;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.log-line {
  font-size: 0.8rem;
  margin-bottom: 0.4rem;
  color: #fff;
}

.log-time { color: var(--text-muted); }
.log-tag { font-weight: 700; margin: 0 0.5rem; }
.log-tag.success { color: var(--color-success); }
.log-tag.info { color: var(--color-primary); }
.log-tag.link { color: var(--color-secondary); }

/* Sidebar Footer */
.sidebar-footer {
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
}

.pulse-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  position: relative;
}

.pulse-dot.online { background: var(--color-success); box-shadow: 0 0 10px var(--color-success); }
.pulse-dot.offline { background: var(--color-danger); box-shadow: 0 0 10px var(--color-danger); }
.pulse-dot.connecting { background: var(--color-warning); box-shadow: 0 0 10px var(--color-warning); }

.pulse-dot::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: inherit;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.5; }
  100% { transform: scale(2.5); opacity: 0; }
}
</style>
