document.addEventListener('DOMContentLoaded', () => {
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
        });

        // Keyboard navigation support
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                item.click();
            }
        });
    });

    // Modals
    const modal = document.getElementById('modal-agent');
    const btnNewAgent = document.getElementById('btn-new-agent');
    const btnCloseModal = document.getElementById('btn-close-modal');

    btnNewAgent.onclick = () => {
        modal.classList.add('active');
        document.getElementById('agent-name').focus();
    };

    btnCloseModal.onclick = () => modal.classList.remove('active');

    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            modal.classList.remove('active');
        }
    });

    // Close modal on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
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

            // Simulate some stats if not provided
            document.getElementById('stat-optimized').textContent = data.optimized_count || Math.floor(Math.random() * 10) + 5;

        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    }

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
                            <span class="meta-item">${new Date(agent.updated_at).toLocaleDateString()}</span>
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

    // Simulate rate limit bar animation
    let rateLimit = 5;
    setInterval(() => {
        rateLimit = Math.max(0, Math.min(100, rateLimit + (Math.random() > 0.5 ? 5 : -5)));
        document.getElementById('rate-bar').style.width = rateLimit + '%';
    }, 3000);
});
