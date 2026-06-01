<template>
  <div class="welcome">
    <h2>欢迎使用 I3D Agent System</h2>
    <p>智能多代理助手，支持 3D 模型搜索、技术文档查询、任务处理等功能</p>
    <div class="quick-actions">
      <div class="quick-action" @click="$emit('quick-action', '帮我搜索一个螺栓零件，材质为不锈钢')">
        <div class="icon">🔍</div>
        <div class="label">搜索相似零件</div>
      </div>
      <div class="quick-action" @click="$emit('quick-action', '如何部署 3D 搜索服务？')">
        <div class="icon">📚</div>
        <div class="label">查询技术文档</div>
      </div>
      <div class="quick-action" @click="$emit('quick-action', '查询最近的文件处理任务状态')">
        <div class="icon">⚙️</div>
        <div class="label">查看任务状态</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['quick-action'])
</script>

<style scoped>
.welcome {
  text-align: center;
  padding: 40px;
}

.welcome h2 {
  font-size: 24px;
  color: #1f2937;
  margin-bottom: 10px;
}

.welcome p {
  color: #6b7280;
  margin-bottom: 30px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  max-width: 600px;
  margin: 0 auto;
}

.quick-action {
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
}

.quick-action:hover {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.quick-action .icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.quick-action .label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}
</style>
