document.addEventListener('DOMContentLoaded', () => {
    // Neural State
    let allSkills = [];
    let selectedSkills = [];
    let totalTokens = 0; 
    let totalCost = 0.00;

    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = item.getAttribute('data-tab');

            navItems.forEach(i => i.classList.remove('active'));
            tabContents.forEach(t => t.classList.remove('active'));

            item.classList.add('active');
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'agents') fetchAgents();
            if (tabId === 'dashboard') fetchStats();
            if (tabId === 'skills') fetchSkills();
            if (tabId === 'mission') fetchMissionStatus();
        });

        // Keyboard navigation support
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                item.click();
            }
        });
    });

    // Agent Modal
    const modal = document.getElementById('modal-agent');
    const btnNewAgent = document.getElementById('btn-new-agent');
    const btnCloseModal = document.getElementById('btn-close-modal');

    btnNewAgent.onclick = () => {
        modal.classList.add('active');
        document.getElementById('agent-name').focus();
    };

    btnCloseModal.onclick = () => modal.classList.remove('active');

    // MCP Modal
    const modalMcp = document.getElementById('modal-mcp');
    const btnNewMcp = document.getElementById('btn-new-mcp');
    const btnCloseMcp = document.getElementById('btn-close-mcp');
    const btnSaveMcp = document.getElementById('btn-save-mcp');

    if (btnNewMcp) {
        btnNewMcp.onclick = () => {
            modalMcp.classList.add('active');
            document.getElementById('mcp-name').focus();
        };
    }

    if (btnCloseMcp) {
        btnCloseMcp.onclick = () => modalMcp.classList.remove('active');
    }

    if (btnSaveMcp) {
        btnSaveMcp.onclick = () => {
            const name = document.getElementById('mcp-name').value;
            const type = document.getElementById('mcp-type').value;
            const command = document.getElementById('mcp-command').value;

            if (!name || !command) return alert('Name and Command/URL are required');

            // Add to list UI
            const list = document.getElementById('mcp-server-list');
            if (list.querySelector('.empty-state')) list.innerHTML = '';

            const item = document.createElement('div');
            item.className = 'mcp-item';
            item.style = 'background: rgba(255,255,255,0.03); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border: 1px solid rgba(255,255,255,0.05);';
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>${name}</strong>
                    <span class="status-badge status-active" style="padding: 2px 6px; font-size: 0.7rem;">READY</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">${type.toUpperCase()}: ${command}</div>
            `;
            list.prepend(item);

            modalMcp.classList.remove('active');
            // Reset form
            document.getElementById('mcp-name').value = '';
            document.getElementById('mcp-command').value = '';
        };
    }

    // Close modals on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (modal.classList.contains('active')) modal.classList.remove('active');
            if (modalMcp && modalMcp.classList.contains('active')) modalMcp.classList.remove('active');
        }
    });

    // Close modals on backdrop click
    [modal, modalMcp].forEach(m => {
        if (!m) return;
        m.addEventListener('click', (e) => {
            if (e.target === m) {
                m.classList.remove('active');
            }
        });
    });

    // Fetch Stats
    async function fetchStats() {
        try {
            const response = await fetch('/');
            const data = await response.json();
            document.getElementById('stat-provider').textContent = data.provider || 'Unknown';
            document.getElementById('stat-model').textContent = data.model || 'Unknown';

            // Populate mapping inputs if they are empty
            if (!document.getElementById('map-opus').value && data.mapping) {
                document.getElementById('map-opus').value = data.mapping.opus || '';
                document.getElementById('map-sonnet').value = data.mapping.sonnet || '';
                document.getElementById('map-haiku').value = data.mapping.haiku || '';
            }

            // Sync global toggles
            if (data.settings) {
                const toggles = {
                    'cfg-hyper': 'hyper_analysis',
                    'cfg-thinking': 'thinking',
                    'cfg-adversarial': 'adversarial',
                    'cfg-raw': 'raw_mode',
                    'cfg-planning': 'planning'
                };
                for (const [id, key] of Object.entries(toggles)) {
                    const el = document.getElementById(id);
                    if (el) el.checked = !!data.settings[key];
                }
            }

            // Simulate some stats if not provided
            document.getElementById('stat-optimized').textContent = data.optimized_count || Math.floor(Math.random() * 10) + 5;

        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    }

    // Dynamic Config Updates
    ['cfg-hyper', 'cfg-thinking', 'cfg-adversarial', 'cfg-raw', 'cfg-planning'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.onchange = async (e) => {
                const map = {
                    'cfg-hyper': 'hyper_analysis',
                    'cfg-thinking': 'thinking',
                    'cfg-adversarial': 'adversarial',
                    'cfg-raw': 'raw_mode',
                    'cfg-planning': 'planning'
                };
                const key = map[id];
                try {
                    await fetch('/v1/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ [key]: e.target.checked })
                    });
                } catch (err) {
                    console.error('Failed to update config:', err);
                }
            };
        }
    });

    // Save Mapping
    document.getElementById('btn-save-mapping').onclick = async () => {
        const btn = document.getElementById('btn-save-mapping');
        const originalText = btn.textContent;
        btn.textContent = 'Saving...';
        btn.disabled = true;

        const mapping = {
            opus: document.getElementById('map-opus').value,
            sonnet: document.getElementById('map-sonnet').value,
            haiku: document.getElementById('map-haiku').value,
        };

        try {
            const response = await fetch('/config/mapping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mapping)
            });

            if (response.ok) {
                btn.textContent = 'Saved!';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                }, 1500);
                fetchStats();
            } else {
                btn.textContent = 'Failed';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                }, 1500);
            }
        } catch (err) {
            btn.textContent = 'Error';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.disabled = false;
            }, 1500);
        }
    };

    // Fetch Agents
    async function fetchAgents() {
        const container = document.getElementById('agents-container');
        container.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <span>Loading agents...</span>
            </div>
        `;

        try {
            const response = await fetch('/agents');
            const data = await response.json();

            document.getElementById('stat-agents').textContent = data.data.length;

            if (data.data.length === 0) {
                container.innerHTML = '<div class="subtitle">No agents found. Create your first one!</div>';
                return;
            }

            // Fetch detailed info for each agent to get skills
            const agentsWithDetails = await Promise.all(
                data.data.map(async (agent) => {
                    try {
                        const detailResponse = await fetch(`/agents/${agent.id}/versions`);
                        const detailData = await detailResponse.json();
                        const latestVersion = detailData.data[detailData.data.length - 1];
                        return { ...agent, ...latestVersion };
                    } catch (e) {
                        return agent;
                    }
                })
            );

            container.innerHTML = agentsWithDetails.map((agent, index) => {
                const skills = agent.skills || [];
                const skillsHtml = skills.length > 0
                    ? `<div class="agent-skills">${skills.map(skill => `<span class="skill-tag">${escapeHtml(skill)}</span>`).join('')}</div>`
                    : '';
                const isAntigravity = agent.metadata?.project === 'Antigravity';
                const category = agent.metadata?.category || 'general';
                const categoryColor = getCategoryColor(category);
                const cost = agent.metadata?.total_cost || 0.00;

                return `
                    <div class="agent-card ${isAntigravity ? 'antigravity-card' : ''}" tabindex="0" role="button" aria-label="Agent: ${agent.name}" style="animation-delay: ${index * 0.1}s">
                        ${isAntigravity ? '<div class="antigravity-badge">ANTIGRAVITY</div>' : ''}
                        <div class="agent-header">
                            <h3>${escapeHtml(agent.name)}</h3>
                            <span class="model-tag" style="background-color: ${categoryColor}">${escapeHtml(category)}</span>
                        </div>
                        <p class="agent-description">${escapeHtml(agent.description || 'No description')}</p>
                        ${skillsHtml}
                        <div class="meta">
                            <span class="meta-item">ID: ${escapeHtml(agent.id)}</span>
                            <span class="meta-item">v${agent.version}</span>
                            <span class="meta-item" style="color: var(--color-primary); font-weight: bold;">$${cost.toFixed(2)}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (err) {
            container.innerHTML = `<div class="subtitle" style="color: var(--color-danger)">Error loading agents: ${escapeHtml(err.message)}</div>`;
        }
    }

    function getCategoryColor(category) {
        const colors = {
            'design': 'rgba(59, 130, 246, 0.2)',
            'orchestration': 'rgba(168, 85, 247, 0.2)',
            'workflows': 'rgba(16, 185, 129, 0.2)',
            'modding': 'rgba(245, 158, 11, 0.2)',
            'general': 'rgba(148, 163, 184, 0.2)'
        };
        return colors[category] || colors.general;
    }

    // Save Agent
    document.getElementById('btn-save-agent').onclick = async () => {
        const name = document.getElementById('agent-name').value.trim();
        const model = document.getElementById('agent-model').value;
        const system = document.getElementById('agent-system').value.trim();
        const description = document.getElementById('agent-description').value.trim();
        const skillsRaw = document.getElementById('agent-skills').value.trim();
        const category = document.getElementById('agent-category').value;
        const metadataRaw = document.getElementById('agent-metadata').value.trim();
        const mcpRaw = document.getElementById('agent-mcp').value.trim();

        if (!name) {
            document.getElementById('agent-name').focus();
            return alert('Name is required');
        }

        let skills = [];
        let metadata = {};
        let mcp_servers = [];

        try {
            if (skillsRaw) skills = skillsRaw.split(',').map(s => s.trim()).filter(s => s);
            if (metadataRaw) metadata = JSON.parse(metadataRaw);
            if (mcpRaw) mcp_servers = JSON.parse(mcpRaw);
        } catch (e) {
            return alert('Invalid JSON in Metadata or MCP Servers');
        }

        // Add category to metadata
        metadata.category = category;
        metadata.project = category === 'design' || category === 'orchestration' || category === 'workflows' ? 'Antigravity' : 'Custom';

        const btn = document.getElementById('btn-save-agent');
        const originalText = btn.textContent;
        btn.textContent = 'Saving...';
        btn.disabled = true;

        try {
            const response = await fetch('/agents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    model,
                    system,
                    description: description || null,
                    skills,
                    metadata,
                    mcp_servers
                })
            });

            if (response.ok) {
                modal.classList.remove('active');
                fetchAgents();
                // Clear fields
                document.getElementById('agent-name').value = '';
                document.getElementById('agent-system').value = '';
                document.getElementById('agent-description').value = '';
                document.getElementById('agent-skills').value = '';
                document.getElementById('agent-metadata').value = '';
                document.getElementById('agent-mcp').value = '';
                document.getElementById('agent-category').value = 'general';
            } else {
                alert('Failed to save agent');
            }
        } catch (err) {
            alert('Error: ' + err.message);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    };

    // Escape HTML helper
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initial load
    fetchStats();
    fetchAgents();

    // Auto-refresh stats
    setInterval(fetchStats, 10000);

    // System Health Monitoring (Real Data)
    async function updateHealthMeters() {
        try {
            const response = await fetch('/v1/health/rate-limit');
            const data = await response.json();
            
            // Update Rate Limit Bar (Real Data)
            const rateBar = document.getElementById('rate-bar');
            if (rateBar) {
                const percent = (data.current_usage / data.rate_limit) * 100;
                rateBar.style.width = Math.min(100, Math.max(2, percent)) + '%';
                // Change color if approaching limit
                rateBar.style.backgroundColor = percent > 80 ? 'var(--color-danger)' : 'var(--color-primary)';
            }
            
            // Update Latency Simulation (linked to activity)
            const latencyBar = document.querySelector('.meter:first-child .bar');
            if (latencyBar) {
                const lat = data.current_usage > 0 ? (15 + Math.random() * 10) : 5;
                latencyBar.style.width = lat + '%';
            }
        } catch (err) {
            console.error('Health monitor failed:', err);
        }
    }
    setInterval(updateHealthMeters, 2000);

    // Fetch Skills
    async function fetchSkills() {
        const container = document.getElementById('skills-container');
        if (allSkills.length > 0) {
            renderSkills(allSkills);
            return;
        }

        try {
            const response = await fetch('/v1/skills');
            const data = await response.json();
            allSkills = data.data;
            renderSkills(allSkills);
        } catch (err) {
            container.innerHTML = `<div class="subtitle" style="color: var(--color-danger)">Error scanning neural library: ${escapeHtml(err.message)}</div>`;
        }
    }

    function renderSkills(skills) {
        const container = document.getElementById('skills-container');
        if (skills.length === 0) {
            container.innerHTML = '<div class="subtitle">No neural skills discovered.</div>';
            return;
        }

        container.innerHTML = skills.map(skill => {
            const isActive = selectedSkills.includes(skill.id);
            return `
                <div class="skill-card ${isActive ? 'active' : ''}" data-id="${escapeHtml(skill.id)}">
                    <h3>${escapeHtml(skill.name)}</h3>
                    <p>${escapeHtml(skill.description || 'Neural expansion module for specialized tasks.')}</p>
                    <div class="skill-id">${escapeHtml(skill.id)}</div>
                </div>
            `;
        }).join('');

        // Add click listeners for selection
        container.querySelectorAll('.skill-card').forEach(card => {
            card.addEventListener('click', () => {
                const id = card.getAttribute('data-id');
                if (selectedSkills.includes(id)) {
                    selectedSkills = selectedSkills.filter(s => s !== id);
                    card.classList.remove('active');
                } else {
                    selectedSkills.push(id);
                    card.classList.add('active');
                }
                updateAgentModalSkills();
            });
        });
    }

    function updateAgentModalSkills() {
        const input = document.getElementById('agent-skills');
        if (input) {
            input.value = selectedSkills.join(', ');
        }
    }

    // Skill Search
    const skillSearch = document.getElementById('skill-search');
    if (skillSearch) {
        skillSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = allSkills.filter(s =>
                s.name.toLowerCase().includes(query) ||
                (s.description && s.description.toLowerCase().includes(query)) ||
                s.id.toLowerCase().includes(query)
            );
            renderSkills(filtered);
        });
    }

    // Mission Control
    async function fetchMissionStatus() {
        try {
            const response = await fetch('/v1/mission/status');
            const data = await response.json();
            renderMissionStatus(data);
            // Refresh main stats to sync model override
            fetchStats();
        } catch (err) {
            console.error('Failed to fetch mission status:', err);
        }
    }

    function renderMissionStatus(data) {
        if (!data) return;

        // Update Session Info
        const sessionInfo = document.getElementById('active-session-info');
        if (data.active_count > 0 && data.active_sessions) {
            const sessions = Object.values(data.active_sessions);
            const firstSession = sessions[0] || {};
            sessionInfo.innerHTML = `
                <div class="status-badge status-active">ACTIVE MISSION</div>
                <p style="font-size: 0.9rem; color: var(--text-primary); margin-top: 0.5rem;">
                    ${data.active_count} session(s) active
                </p>
                <p style="font-size: 0.75rem; color: var(--text-muted);">
                    Model: ${firstSession.model || 'Unknown'}
                </p>
            `;
        } else {
            sessionInfo.innerHTML = `
                <div class="status-badge status-idle">IDLE</div>
                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.5rem;">
                    Waiting for mission launch...
                </p>
            `;
        }

        // Update Tool Count
        const toolCountEl = document.getElementById('feed-tool-count');
        if (toolCountEl) toolCountEl.textContent = `${data.tool_count || 0} tools used`;

        // Update Change Log
        const changeLog = document.getElementById('change-log');
        if (!data.recent_changes || data.recent_changes.length === 0) {
            changeLog.innerHTML = '<div class="empty-state">No changes detected yet.</div>';
        } else {
            changeLog.innerHTML = [...data.recent_changes].reverse().map(change => `
                <div class="change-item">
                    <div class="change-file" title="${change.file}">${change.file.split('\\').pop().split('/').pop()}</div>
                    <div class="change-type type-${change.type}">${(change.type || 'edit').toUpperCase()}</div>
                </div>
            `).join('');
        }

        // Update Global Stats (Real Data)
        totalTokens = data.total_tokens || 0;
        totalCost = data.total_cost || 0;
        
        const tokensEl = document.getElementById('analytics-tokens');
        const costEl = document.getElementById('analytics-cost');
        if (tokensEl) tokensEl.textContent = formatNumber(totalTokens);
        if (costEl) costEl.textContent = `$${totalCost.toFixed(2)}`;
    }

    // Abort All
    document.getElementById('btn-stop-all').onclick = async () => {
        if (!confirm('Are you sure you want to abort all active missions?')) return;
        try {
            await fetch('/v1/mission/stop', { method: 'POST' });
            fetchMissionStatus();
        } catch (err) {
            alert('Failed to stop missions');
        }
    };

    // Auto-refresh mission status if on mission tab
    setInterval(() => {
        const activeTab = document.querySelector('.nav-item.active').getAttribute('data-tab');
        if (activeTab === 'mission') {
            fetchMissionStatus();
        }
    }, 2000);

    // WebSocket for Live Intelligence Feed & System Logs
    function connectLogs() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        const socket = new WebSocket(wsUrl);

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'tool_use') {
                const status = data.status === 'INTERCEPTED_FAILURE' ? ' [HEALING...]' : '';
                appendTerminalLine(`EXECUTOR: Calling tool '${data.tool}'${status}`, data.status === 'INTERCEPTED_FAILURE' ? 'system' : 'tool');
                
                const toolCountEl = document.getElementById('feed-tool-count');
                if (toolCountEl) {
                    const current = parseInt(toolCountEl.textContent) || 0;
                    toolCountEl.textContent = `${current + 1} tools used`;
                }
            } else if (data.type === 'orchestration') {
                appendTerminalLine(`ARCHITECT: ${data.action} - [${data.agent}]`, 'system');
            } else if (data.type === 'tool_result') {
                appendTerminalLine(`ARCHITECT: Tool Result Received (ID: ${data.tool_use_id.slice(-6)})`, 'system');
            } else if (data.type === 'traffic') {
                // Update System Logs
                appendLogLine(`[${data.method}] ${data.path} - ${data.model} (${data.tokens} tokens)`, 'info');

                // Update Global Stats
                updateAnalytics(data.tokens);
            }
        };

        socket.onclose = () => {
            setTimeout(connectLogs, 5000); // Reconnect
        };
    }

    function updateAnalytics(tokens) {
        totalTokens += tokens;
        // Approx cost: $15 per 1M tokens (Opus/Sonnet avg)
        const sessionCost = (tokens / 1000000) * 15;
        totalCost += sessionCost;

        const tokensEl = document.getElementById('analytics-tokens');
        const costEl = document.getElementById('analytics-cost');

        if (tokensEl) tokensEl.textContent = formatNumber(totalTokens);
        if (costEl) costEl.textContent = `$${totalCost.toFixed(2)}`;
    }

    function formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num;
    }

    function appendLogLine(text, type = 'info') {
        const logContent = document.getElementById('log-content');
        if (!logContent) return;

        const line = document.createElement('div');
        line.style.marginBottom = '4px';
        line.style.color = type === 'error' ? 'var(--color-danger)' : 'inherit';
        line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;

        logContent.appendChild(line);
        logContent.scrollTop = logContent.scrollHeight;

        while (logContent.children.length > 50) {
            logContent.removeChild(logContent.firstChild);
        }
    }

    function appendTerminalLine(text, type = 'system') {
        const feed = document.getElementById('intelligence-feed');
        if (!feed) return;

        const line = document.createElement('div');
        line.className = `terminal-line ${type}`;
        line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;

        feed.appendChild(line);
        feed.scrollTop = feed.scrollHeight;

        // Limit lines
        while (feed.children.length > 100) {
            feed.removeChild(feed.firstChild);
        }
    }

    connectLogs();
});
