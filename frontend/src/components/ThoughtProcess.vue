<template>
  <details class="thought-process" open>
    <summary>🧠 思考过程</summary>
    <div class="thought-steps">
      <div v-for="(step, index) in steps" :key="index" class="thought-step">
        • {{ step }}
      </div>
    </div>
  </details>
</template>

<script setup>
defineProps({
  steps: { type: Array, default: () => [] }
})
</script>

<style scoped>
.thought-process {
  margin-top: 10px;
  padding: 10px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 12px;
}

.thought-process summary {
  cursor: pointer;
  font-weight: 600;
  color: #166534;
}

.thought-steps {
  margin-top: 8px;
  padding-left: 15px;
}

.thought-step {
  margin: 4px 0;
  color: #15803d;
}
</style>
