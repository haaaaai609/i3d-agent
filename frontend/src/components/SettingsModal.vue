<template>
  <teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="$emit('close')">
      <section class="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <header class="modal-header">
          <h2 id="settings-title">设置</h2>
          <button type="button" class="icon-button" aria-label="关闭" @click="$emit('close')">×</button>
        </header>

        <div class="settings-body">
          <label class="field">
            <span>租户</span>
            <select :value="tenantId" @change="$emit('tenantChanged', $event.target.value)">
              <option value="huabei">华贝 (huabei)</option>
              <option value="shenfa">申发 (shenfa)</option>
              <option value="meidi">美的 (meidi)</option>
              <option value="dongjiang">东江 (dongjiang)</option>
              <option value="default">默认 (default)</option>
            </select>
          </label>

          <label class="field">
            <span>用户 ID</span>
            <input
              type="text"
              :value="userId"
              placeholder="输入用户 ID"
              @input="$emit('userIdChanged', $event.target.value)"
            >
          </label>

          <label class="toggle-row">
            <span>
              <strong>流式输出</strong>
              <small>聊天响应按片段实时显示</small>
            </span>
            <input
              type="checkbox"
              :checked="streamMode"
              @change="$emit('streamModeChanged', $event.target.checked)"
            >
          </label>
        </div>
      </section>
    </div>
  </teleport>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  tenantId: { type: String, default: 'huabei' },
  userId: { type: String, default: 'demo_user' },
  streamMode: { type: Boolean, default: true }
})

defineEmits(['close', 'tenantChanged', 'userIdChanged', 'streamModeChanged'])
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(17, 24, 39, 0.42);
}

.settings-modal {
  width: min(440px, 100%);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 22px 55px rgba(15, 23, 42, 0.25);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
}

.icon-button {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
}

.icon-button:hover {
  background: #f3f4f6;
  color: #111827;
}

.settings-body {
  display: grid;
  gap: 16px;
  padding: 20px;
}

.field {
  display: grid;
  gap: 6px;
}

.field span,
.toggle-row strong {
  color: #374151;
  font-size: 13px;
  font-weight: 700;
}

.field input,
.field select {
  width: 100%;
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 7px;
  background: #fff;
  color: #111827;
  font: inherit;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0 0;
  border-top: 1px solid #f3f4f6;
}

.toggle-row span {
  display: grid;
  gap: 3px;
}

.toggle-row small {
  color: #6b7280;
  font-size: 12px;
}

.toggle-row input {
  width: 18px;
  height: 18px;
}
</style>
