<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h1>I3D Agent System</h1>
      <p>智能多代理助手</p>
    </div>

    <div class="agent-section">
      <h3>Agent 功能</h3>
      <button
        v-for="(config, key) in AGENTS"
        :key="key"
        :class="['agent-btn', { active: currentAgent === key }]"
        @click="$emit('agent-selected', key)"
      >
        <span class="icon">{{ config.icon }}</span>
        <span class="label">{{ config.title }}</span>
        <span class="badge">{{ config.badge }}</span>
      </button>
    </div>

    <div class="settings">
      <div class="setting-item">
        <label>租户</label>
        <select :value="tenantId" @change="$emit('tenant-changed', $event.target.value)">
          <option value="huabei">华贝 (huabei)</option>
          <option value="shenfa">申发 (shenfa)</option>
          <option value="meidi">美的 (meidi)</option>
          <option value="dongjiang">东江 (dongjiang)</option>
        </select>
      </div>
      <div class="setting-item">
        <label>用户 ID</label>
        <input
          type="text"
          :value="userId"
          @input="$emit('user-changed', $event.target.value)"
          placeholder="输入用户ID"
        >
      </div>
    </div>
  </div>
</template>

<script setup>
import { AGENTS } from '../composables/useAgents.js'

defineProps({
  currentAgent: { type: String, default: 'general' },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' }
})

defineEmits(['agent-selected', 'tenant-changed', 'user-changed'])
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: #1a1a2e;
  color: white;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.sidebar-header {
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 20px;
}

.sidebar-header h1 {
  font-size: 20px;
  font-weight: 600;
}

.sidebar-header p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 5px;
}

.agent-section {
  flex: 1;
}

.agent-section h3 {
  font-size: 12px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 15px;
}

.agent-btn {
  width: 100%;
  padding: 12px 16px;
  margin-bottom: 8px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  text-align: left;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.agent-btn.active {
  background: #667eea;
}

.agent-btn .icon {
  font-size: 18px;
}

.agent-btn .label {
  flex: 1;
}

.agent-btn .badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
}

.settings {
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.setting-item {
  margin-bottom: 12px;
}

.setting-item label {
  display: block;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
}

.setting-item select,
.setting-item input {
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 13px;
}

.setting-item select option {
  background: #1a1a2e;
}
</style>
