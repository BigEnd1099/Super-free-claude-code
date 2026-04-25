document.addEventListener('DOMContentLoaded', () => {
    /**
     * Manages the Neural Map network graph using vis-network.
     * Handles fetching, rendering, optimization, and lifecycle management.
     */
    class NeuralMapManager {
        #network = null;
        #nodes = null;
        #edges = null;
        #zoomTimeout = null;
        #visibleLabelIds = new Set();
        #containerId;
        #pathId;

        /**
         * Immutable styles for different node groups - Preserving current visuals.
         */
        static GROUP_STYLES = Object.freeze({
            directory: { color: { background: '#0f172a', border: '#94a3b8' }, shape: 'box', font: { size: 16, bold: true } },
            module: { color: { background: '#1e293b', border: '#3b82f6' }, shape: 'diamond', size: 25 },
            class: { color: { background: '#334155', border: '#a855f7' }, shape: 'dot', size: 20 },
            function: { color: { background: '#0f172a', border: '#10b981' }, shape: 'dot', size: 15 },
            import: { color: { background: '#1e293b', border: '#f59e0b' }, shape: 'triangle', size: 12 },
            rationale: { color: { background: '#450a0a', border: '#ef4444' }, shape: 'star', size: 18 },
            file: { color: { background: '#0f172a', border: '#64748b' }, shape: 'dot', size: 10 }
        });

        constructor({ containerId = 'graph-container', pathId = 'active-project-path' } = {}) {
            this.#containerId = containerId;
            this.#pathId = pathId;
        }

        #escapeHtml(str) {
            if (typeof str !== 'string') return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        #showLoading() {
            const container = document.getElementById(this.#containerId);
            if (container) {
                container.innerHTML = `
                    <div class="loading-spinner">
                        <div class="spinner"></div>
                        <span>Mapping Neural Network... This may take a few seconds.</span>
                    </div>
                `;
            }
        }

        #showError(errorMsg) {
            const container = document.getElementById(this.#containerId);
            if (container) {
                container.innerHTML = `
                    <div class="subtitle" style="color: var(--color-danger); padding: 2rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 1rem;">⚠️</div>
                        <strong>Neural Mapping Error:</strong><br>
                        <span style="font-family: monospace; font-size: 0.9rem;">${this.#escapeHtml(errorMsg)}</span>
                    </div>
                `;
            }
        }

        async fetchGraph({ rescan = false } = {}) {
            const isRefresh = !!this.#network;
            
            if (!isRefresh) {
                this.#showLoading();
            } else {
                // For refreshes, show a subtle indicator on the button instead of replacing the whole graph
                const btn = document.getElementById('btn-refresh-graph');
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = 'SCANNING...';
                }
            }

            const dataUrl = rescan ? '/v1/graph/scan' : '/v1/graph/data';
            const projectUrl = '/v1/graph/project';

            try {
                const results = await Promise.allSettled([
                    fetch(projectUrl).then(r => r.ok ? r.json() : Promise.reject(`Project fetch failed`)),
                    fetch(dataUrl).then(r => r.ok ? r.json() : Promise.reject(`Graph data fetch failed`))
                ]);

                const [projectResult, graphResult] = results;

                if (projectResult.status === 'fulfilled') {
                    const pathEl = document.getElementById(this.#pathId);
                    if (pathEl && projectResult.value.path) {
                        pathEl.textContent = `[ROOT] ${projectResult.value.path}`;
                    }
                }

                if (graphResult.status === 'fulfilled') {
                    this.renderGraph(graphResult.value);
                } else {
                    throw new Error(graphResult.reason);
                }

                // Restore refresh button state
                const btn = document.getElementById('btn-refresh-graph');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'SCAN CODEBASE';
                }
            } catch (err) {
                this.#showError(err.message);
                
                // Ensure button is reset even on error
                const btn = document.getElementById('btn-refresh-graph');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'SCAN CODEBASE';
                }
            }
        }

        renderGraph(rawData) {
            const container = document.getElementById(this.#containerId);
            if (!container) return;

            const nodesArray = rawData.nodes.map(node => ({
                ...node,
                ...NeuralMapManager.GROUP_STYLES[node.group || 'module'],
                font: {
                    color: '#ffffff',
                    face: 'JetBrains Mono',
                    size: node.group === 'directory' ? 16 : 12
                }
            }));

            if (this.#network) {
                // High-performance diff: only update what changed
                const currentIds = new Set(this.#nodes.getIds());
                const newIds = new Set(nodesArray.map(n => n.id));
                
                const toDelete = [...currentIds].filter(id => !newIds.has(id));
                const toUpdate = nodesArray.filter(n => currentIds.has(n.id));
                const toAdd = nodesArray.filter(n => !currentIds.has(n.id));
                
                if (toDelete.length > 0) this.#nodes.remove(toDelete);
                if (toUpdate.length > 0) this.#nodes.update(toUpdate);
                if (toAdd.length > 0) this.#nodes.add(toAdd);
                
                // Same for edges
                const currentEdgeIds = new Set(this.#edges.getIds());
                const newEdgeIds = new Set(rawData.edges.map(e => e.id || `${e.from}-${e.to}`));
                
                // Note: edges usually don't have stable IDs unless provided, 
                // but we can clear them if there's a major change
                if (toAdd.length > 0 || toDelete.length > 0) {
                    this.#edges.clear();
                    this.#edges.add(rawData.edges);
                }
                
                this.#updateLabels();
                return;
            }

            this.#nodes = new vis.DataSet(nodesArray);
            this.#edges = new vis.DataSet(rawData.edges);

            const isPerfMode = document.getElementById('graph-perf-mode')?.checked ?? true;
            const options = {
                nodes: { borderWidth: 2, shadow: true },
                edges: {
                    color: { color: 'rgba(255,255,255,0.15)', highlight: '#3b82f6' },
                    arrows: { to: { enabled: true, scaleFactor: 0.4 } },
                    smooth: { type: 'continuous' }
                },
                layout: { improvedLayout: false },
                physics: {
                    stabilization: { iterations: 100 },
                    barnesHut: { gravitationalConstant: -25000, centralGravity: 0.05, springLength: 700 }
                },
                interaction: { 
                    hover: true, 
                    tooltipDelay: 200,
                    hideEdgesOnDrag: isPerfMode,
                    hideEdgesOnZoom: isPerfMode
                }
            };

            this.#network = new vis.Network(container, { nodes: this.#nodes, edges: this.#edges }, options);

            this.#network.on('zoom', () => {
                if (this.#zoomTimeout) clearTimeout(this.#zoomTimeout);
                this.#zoomTimeout = setTimeout(() => this.#updateLabels(), 250);
            });

            this.#network.on('dragEnd', () => {
                if (this.#zoomTimeout) clearTimeout(this.#zoomTimeout);
                this.#zoomTimeout = setTimeout(() => this.#updateLabels(), 150);
            });

            // Performance Mode Toggle
            const perfToggle = document.getElementById('graph-perf-mode');
            if (perfToggle) {
                perfToggle.addEventListener('change', (e) => {
                    const enabled = e.target.checked;
                    if (this.#network && typeof this.#network.setOptions === 'function') {
                        this.#network.setOptions({
                            interaction: {
                                hideEdgesOnDrag: enabled,
                                hideEdgesOnZoom: enabled
                            }
                        });
                    }
                });
            }

            this.#network.on("stabilizationIterationsDone", () => {
                this.#network.setOptions({ physics: false });
                this.#updateLabels(); // Apply initial culling
            });
        }

        #updateLabels() {
            // Safety Check: Ensure network exists and has the required methods
            if (!this.#network || typeof this.#network.getNodesInView !== 'function') {
                return;
            }
            
            let scale;
            let visibleIds;
            try {
                scale = this.#network.getScale();
                visibleIds = this.#network.getNodesInView();
            } catch (e) {
                // Network might not be ready yet
                return;
            }

            if (!visibleIds) return;
            
            const updates = [];
            const labelEnabledIds = new Set();
            let labelsShown = 0;
            const MAX_LABELS = 40;

            // Performance: Direct iteration without expensive sorting or map/filter
            visibleIds.forEach(id => {
                const node = this.#nodes.get(id);
                if (!node) return;

                let targetFontSize = 0;
                const level = node.level ?? 99;

                // Tighter thresholds: Only show detail when significantly zoomed in
                const showByScale = 
                    (scale > 1.5) ||                // Everything
                    (scale > 1.0 && level <= 3) ||  // Functions
                    (scale > 0.7 && level <= 1) ||  // Files
                    (scale > 0.3 && level === 0);   // Directories

                if (showByScale && labelsShown < MAX_LABELS) {
                    targetFontSize = scale > 1.0 ? 12 : 14;
                    labelsShown++;
                    labelEnabledIds.add(String(node.id));
                }

                if ((node.font?.size ?? 0) !== targetFontSize) {
                    updates.push({ 
                        id: node.id, 
                        font: { ...(node.font || {}), size: targetFontSize },
                        color: node.color,
                        shape: node.shape,
                        size: node.size,
                        hidden: false
                    });
                    if (targetFontSize > 0) this.#visibleLabelIds.add(String(node.id));
                }
            });

            // Hide labels that just left the view or were throttled
            this.#visibleLabelIds.forEach(id => {
                if (!labelEnabledIds.has(id)) {
                    const node = this.#nodes.get(id);
                    if (node && (node.font?.size ?? 0) !== 0) {
                        updates.push({ 
                            id: node.id, 
                            font: { ...(node.font || {}), size: 0 },
                            color: node.color,
                            shape: node.shape,
                            size: node.size,
                            hidden: false
                        });
                    }
                    this.#visibleLabelIds.delete(id);
                }
            });

            if (updates.length > 0) {
                this.#nodes.update(updates);
            }
        }

        redraw() { this.#network?.redraw(); }
        
        destroy() {
            if (this.#zoomTimeout) clearTimeout(this.#zoomTimeout);
            if (this.#network) this.#network.destroy();
            this.#nodes = this.#edges = this.#network = null;
        }
    }

    // Neural State
    const neuralMap = new NeuralMapManager();
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

            // Switch active tab UI
            navItems.forEach(t => t.classList.remove('active'));
            item.classList.add('active');

            const targetTab = document.getElementById(tabId);
            if (!targetTab) {
                console.error(`Navigation Error: Target tab #${tabId} not found in DOM.`);
                return;
            }

            tabContents.forEach(t => t.classList.remove('active'));
            targetTab.classList.add('active');

            try {
                if (tabId === 'agents') fetchAgents();
                if (tabId === 'feed') fetchMissionStatus();
                if (tabId === 'dashboard') fetchStats();
                if (tabId === 'graph') {
                    neuralMap.fetchGraph();
                    setTimeout(() => neuralMap.redraw(), 100);
                }
                if (tabId === 'skills') fetchSkills();
                if (tabId === 'mcp') fetchStats();
                if (tabId === 'auth') fetchAuthStatus();
                if (tabId === 'logs') fetchStats();
                if (tabId === 'config') fetchStats();
            } catch (err) {
                console.error(`Tab Load Error (${tabId}):`, err);
            }
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
            if (list.querySelector('.subtitle')) list.innerHTML = '';

            const item = document.createElement('div');
            item.className = 'mcp-item';
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: var(--color-primary);">${escapeHtml(name)}</strong>
                    <span class="status-badge status-active">READY</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem; word-break: break-all;">
                    ${escapeHtml(type.toUpperCase())}: ${escapeHtml(command)}
                </div>
                <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                    <button class="btn btn-secondary btn-sm" style="flex: 1;">CONFIG</button>
                    <button class="btn btn-secondary btn-sm" style="flex: 1; border-color: var(--color-danger); color: var(--color-danger);">REMOVE</button>
                </div>
            `;
            list.prepend(item);

            modalMcp.classList.remove('active');
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

            // Populate stats safely
            const setStat = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val;
            };

            setStat('stat-provider', data.provider || 'Unknown');
            setStat('stat-model', data.model || 'Unknown');
            setStat('stat-agents', data.agent_count || 0);
            setStat('stat-optimized', data.optimized_count || 12);

            // Sync Persistent Stats
            if (data.total_tokens !== undefined) {
                totalTokens = data.total_tokens;
                totalCost = data.total_cost;
                setStat('stat-tokens', formatNumber(totalTokens));
                setStat('stat-cost', `$${totalCost.toFixed(2)}`);
            }

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
                neuralMap.fetchGraph(); // Invalidate and refresh graph on new agent
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
    (async () => {
        console.log("Nexus UI: Initializing modules...");
        try { await fetchStats(); } catch (e) { console.error("Stats init failed", e); }
        try { await fetchAgents(); } catch (e) { console.error("Agents init failed", e); }
    })();

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
    setInterval(updateHealthMeters, 5000);

    // Fetch Skills
    async function fetchSkills() {
        const container = document.getElementById('skills-container');
        if (allSkills && allSkills.length > 0) {
            renderSkills(allSkills);
            return;
        }

        try {
            const response = await fetch('/v1/skills');
            const data = await response.json();
            allSkills = data.data || [];
            renderSkills(allSkills);
        } catch (err) {
            container.innerHTML = `<div class="subtitle" style="color: var(--color-danger)">Error scanning neural library: ${escapeHtml(err.message)}</div>`;
        }
    }

    function renderSkills(skills) {
        const container = document.getElementById('skills-container');
        const countEl = document.getElementById('skill-count');
        if (countEl) countEl.textContent = allSkills.length;

        if (skills.length === 0) {
            container.innerHTML = '<div class="subtitle">No neural skills discovered.</div>';
            return;
        }

        container.innerHTML = skills.map(skill => {
            const isActive = selectedSkills.includes(skill.id);
            const category = skill.category || 'Uncategorized';
            const tags = (skill.tags || []).map(t => `<span class="skill-mini-tag">${escapeHtml(t)}</span>`).join('');

            return `
                <div class="skill-card ${isActive ? 'active' : ''}" data-id="${escapeHtml(skill.id)}">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <h3>${escapeHtml(skill.name)}</h3>
                        <span class="skill-cat-badge">${escapeHtml(category)}</span>
                    </div>
                    <p>${escapeHtml(skill.description || 'Neural expansion module for specialized tasks.')}</p>
                    <div class="skill-tags-row">${tags}</div>
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
        if (sessionInfo) {
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
        }

        // Update Tool Count
        const toolCountEl = document.getElementById('feed-tool-count');
        if (toolCountEl) toolCountEl.textContent = `${data.tool_count || 0} tools used`;

        // Update Change Log
        const changeLog = document.getElementById('change-log');
        if (changeLog) {
            if (!data.recent_changes || data.recent_changes.length === 0) {
                changeLog.innerHTML = '<div class="empty-state">No changes detected yet.</div>';
            } else {
                changeLog.innerHTML = [...data.recent_changes].reverse().map(change => `
                    <div class="change-item">
                        <div class="change-file" title="${change.file}">${change.file.split('\\').pop().split('/').pop()}</div>
                        <div class="change-type ${change.type}">${(change.type || 'edit').toUpperCase()}</div>
                    </div>
                `).join('');

                // Refresh graph if changes detected
                if (data.recent_changes.length > 0) {
                    neuralMap.fetchGraph();
                }
            }
        }

        // Update Global Stats (Real Data)
        totalTokens = data.total_tokens || 0;
        totalCost = data.total_cost || 0;

        const tokensEl = document.getElementById('stat-tokens');
        const costEl = document.getElementById('stat-cost');
        if (tokensEl) tokensEl.textContent = formatNumber(totalTokens);
        if (costEl) costEl.textContent = `$${totalCost.toFixed(2)}`;

        // Sync system logs view if elements exist there too
        const analyticsTokens = document.getElementById('analytics-tokens');
        const analyticsCost = document.getElementById('analytics-cost');
        if (analyticsTokens) analyticsTokens.textContent = formatNumber(totalTokens);
        if (analyticsCost) analyticsCost.textContent = `$${totalCost.toFixed(2)}`;
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
    let logSocket = null;
    function connectLogs() {
        if (logSocket) {
            logSocket.close();
            logSocket = null;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        logSocket = new WebSocket(wsUrl);

        logSocket.onopen = () => console.log('Telemetry stream connected.');

        logSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'tool_use') {
                const status = data.status === 'INTERCEPTED_FAILURE' ? ' [HEALING...]' : '';
                appendTerminalLine(`EXECUTOR: Calling tool '${data.tool}'${status}`, data.status === 'INTERCEPTED_FAILURE' ? 'system' : 'tool');
                updateWorkflowLoop('execution');

                const toolCountEl = document.getElementById('feed-tool-count');
                if (toolCountEl) {
                    const current = parseInt(toolCountEl.textContent) || 0;
                    toolCountEl.textContent = `${current + 1} tools used`;
                }
            } else if (data.type === 'orchestration') {
                appendTerminalLine(`ARCHITECT: ${data.action} - [${data.agent}]`, 'system');
                updateWorkflowLoop('planning');
            } else if (data.type === 'tool_result') {
                appendTerminalLine(`ARCHITECT: Tool Result Received (ID: ${data.tool_use_id.slice(-6)})`, 'system');
                updateWorkflowLoop('validation');
            } else if (data.type === 'traffic') {
                // Update System Logs
                appendLogLine(`[${data.method}] ${data.path} - ${data.model} (${data.tokens} tokens)`, 'info');

                // Update Global Stats
                updateAnalytics(data.tokens);
            }
        };

        logSocket.onclose = () => {
            console.warn('Telemetry stream lost. Reconnecting in 5s...');
            setTimeout(connectLogs, 5000);
        };

        logSocket.onerror = (err) => {
            console.error('Telemetry stream error:', err);
            logSocket.close();
        };
    }

    function updateAnalytics(tokens) {
        totalTokens += tokens;
        // Approx cost: $15 per 1M tokens (Opus/Sonnet avg)
        const sessionCost = (tokens / 1000000) * 15;
        totalCost += sessionCost;

        const tokensEl = document.getElementById('stat-tokens');
        const costEl = document.getElementById('stat-cost');
        if (tokensEl) tokensEl.textContent = formatNumber(totalTokens);
        if (costEl) costEl.textContent = `$${totalCost.toFixed(2)}`;

        // Sync legacy IDs too
        const analyticsTokens = document.getElementById('analytics-tokens');
        const analyticsCost = document.getElementById('analytics-cost');
        if (analyticsTokens) analyticsTokens.textContent = formatNumber(totalTokens);
        if (analyticsCost) analyticsCost.textContent = `$${totalCost.toFixed(2)}`;
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

    function updateWorkflowLoop(step) {
        const nodes = {
            'planning': document.getElementById('node-planning'),
            'execution': document.getElementById('node-execution'),
            'validation': document.getElementById('node-validation')
        };
        const statusText = document.getElementById('workflow-status-text');

        // Reset all
        Object.values(nodes).forEach(n => n?.classList.remove('active'));

        if (nodes[step]) {
            nodes[step].classList.add('active');
            if (statusText) {
                if (step === 'planning') statusText.textContent = 'ARCHITECT: Synthesizing implementation strategy...';
                if (step === 'execution') statusText.textContent = 'EXECUTOR: Operationalizing code changes...';
                if (step === 'validation') statusText.textContent = 'FORENSICS: Verifying system integrity...';
                if (step === 'idle') statusText.textContent = 'SYSTEM: All subsystems operational. Ready for mission.';
            }
        } else if (step === 'idle') {
            if (statusText) statusText.textContent = 'SYSTEM: Ready. Awaiting instructions...';
        }
    }

    // Handle idle state
    let loopCycle = 0;
    setInterval(() => {
        const activeCount = parseInt(document.getElementById('stat-agents').textContent) || 0;
        if (activeCount === 0) {
            updateWorkflowLoop('idle');
        }
    }, 5000);

    document.getElementById('btn-refresh-graph').onclick = () => neuralMap.fetchGraph({ rescan: true });

    // Identity Lab: Auth Status
    async function fetchAuthStatus() {
        const statsContainer = document.getElementById('auth-stats-container');
        const listContainer = document.getElementById('auth-list');

        try {
            const response = await fetch('/v1/auth/status');
            const data = await response.json();
            if (!data || !data.accounts) {
                statsContainer.innerHTML = '<div class="subtitle">No accounts configured.</div>';
                listContainer.innerHTML = '<div class="empty-state">No sessions active.</div>';
                return;
            }

            // Render Stats
            statsContainer.innerHTML = data.accounts.map(acc => `
                <div class="stat-card">
                    <div class="stat-label">${escapeHtml(acc.id)}</div>
                    <div class="stat-value" style="color: ${acc.healthy ? 'var(--color-success)' : 'var(--color-danger)'}">
                        ${acc.quota} Credits
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.5rem;">
                        Expires in ${Math.floor(acc.expires_in / 60)}m
                    </div>
                </div>
            `).join('') || '<div class="subtitle">No active sessions detected.</div>';

            // Render List
            listContainer.innerHTML = data.accounts.map(acc => `
                <div class="mapping-item" style="padding: 1rem; background: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <div class="pulse-dot" style="background-color: ${acc.active ? 'var(--color-success)' : 'var(--color-muted)'}"></div>
                        <div>
                            <div style="font-weight: 600;">${escapeHtml(acc.id)}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Status: ${acc.healthy ? 'HEALTHY' : 'DEGRADED'}</div>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-sm">REFRESH</button>
                </div>
            `).join('');

        } catch (err) {
            console.error('Failed to fetch auth status:', err);
        }
    }

    document.getElementById('btn-add-session').onclick = () => {
        const accountId = prompt("Enter Account ID/Email:");
        const token = prompt("Enter Access Token:");
        if (accountId && token) {
            fetch('/v1/auth/session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    account_id: accountId,
                    access_token: token,
                    expires_at: Date.now() / 1000 + 3600
                })
            }).then(() => fetchAuthStatus());
        }
    };

    connectLogs();
});
