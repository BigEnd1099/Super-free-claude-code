<script setup>
import { ref, onMounted, computed } from 'vue'
import { Search, Brain, Check, ShieldCheck } from 'lucide-vue-next'

const skills = ref([])
const loading = ref(true)
const searchQuery = ref('')
const selectedSkills = ref(new Set())

const fetchSkills = async () => {
  try {
    const res = await fetch('/v1/skills')
    const data = await res.json()
    skills.value = data.data
  } catch (e) {
    console.error('Failed to fetch skills', e)
  } finally {
    loading.value = false
  }
}

const filteredSkills = computed(() => {
  if (!searchQuery.value) return skills.value
  const query = searchQuery.value.toLowerCase()
  return skills.value.filter(s => 
    s.name.toLowerCase().includes(query) || 
    (s.description && s.description.toLowerCase().includes(query))
  )
})

const toggleSkill = (id) => {
  if (selectedSkills.value.has(id)) {
    selectedSkills.value.delete(id)
  } else {
    selectedSkills.value.add(id)
  }
}

onMounted(fetchSkills)
</script>

<template>
  <div class="skill-picker">
    <div class="picker-header">
      <div class="search-box">
        <Search class="search-icon" :size="18" />
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Search 1,200+ neural skills..." 
          class="search-input"
        />
      </div>
      <div class="selection-stats">
        <span class="badge" v-if="selectedSkills.size > 0">
          {{ selectedSkills.size }} Selected
        </span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="pulse-loader"></div>
      <p>Scanning Neural Library...</p>
    </div>

    <div v-else class="skills-grid">
      <div 
        v-for="skill in filteredSkills" 
        :key="skill.id" 
        class="skill-card"
        :class="{ active: selectedSkills.has(skill.id) }"
        @click="toggleSkill(skill.id)"
      >
        <div class="skill-icon">
          <Brain v-if="!selectedSkills.has(skill.id)" :size="20" />
          <Check v-else :size="20" />
        </div>
        <div class="skill-info">
          <h3>{{ skill.name }}</h3>
          <p>{{ skill.description || 'Neural expansion module for specialized tasks.' }}</p>
        </div>
        <div class="skill-footer">
          <span class="skill-id">{{ skill.id }}</span>
          <ShieldCheck v-if="skill.path.includes('official')" :size="14" class="official-icon" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skill-picker {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 15px;
}

.search-box {
  position: relative;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-dim);
}

.search-input {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 12px 12px 40px;
  color: var(--text);
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--accent);
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
  overflow-y: auto;
  padding-bottom: 20px;
}

.skill-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  overflow: hidden;
}

.skill-card:hover {
  border-color: var(--accent-dim);
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.03);
}

.skill-card.active {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.05);
  box-shadow: 0 0 20px rgba(var(--accent-rgb), 0.1);
}

.skill-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--bg-body);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}

.active .skill-icon {
  background: var(--accent);
  color: white;
}

.skill-info h3 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
  color: var(--text);
}

.skill-info p {
  font-size: 0.85rem;
  color: var(--text-dim);
  margin: 8px 0 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.skill-footer {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.skill-id {
  font-size: 0.75rem;
  font-family: monospace;
  color: var(--text-dim);
  opacity: 0.6;
}

.official-icon {
  color: #3b82f6;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  gap: 15px;
}

.pulse-loader {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 0.8; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.badge {
  background: var(--accent);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}
</style>
