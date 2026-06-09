<template>
  <div class="input-area">
    <div class="input-shell">
      <div v-if="attachedFile" class="file-preview">
        <span class="name">📎 {{ attachedFile.name }}</span>
        <span class="remove" @click="removeFile">✕</span>
      </div>
      <div class="input-wrapper">
        <div class="input-box">
          <textarea
            ref="textareaRef"
            :value="inputText"
            :placeholder="placeholder"
            :disabled="disabled"
            @input="inputText = $event.target.value"
            @keydown="handleKeydown"
            class="message-input"
          ></textarea>
          <button class="attach-btn" @click="triggerFileInput" title="上传文件">📎</button>
          <input
            ref="fileInputRef"
            type="file"
            style="display: none"
            @change="handleFileSelect"
          >
        </div>
        <button class="send-btn" @click="send" :disabled="disabled || !inputText.trim()">
          ➤
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'

const props = defineProps({
  placeholder: { type: String, default: '输入消息...' },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['send'])

const inputText = ref('')
const attachedFile = ref(null)
const textareaRef = ref(null)
const fileInputRef = ref(null)

onMounted(() => {
  textareaRef.value?.focus()
})

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

function send() {
  if (!inputText.value.trim() && !attachedFile.value) return

  emit('send', {
    message: inputText.value,
    file: attachedFile.value
  })

  inputText.value = ''
  attachedFile.value = null
  nextTick(() => textareaRef.value?.focus())
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    attachedFile.value = file
  }
}

function removeFile() {
  attachedFile.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}
</script>

<style scoped>
.input-area {
  padding: 16px 24px 24px;
  background: white;
}

.input-shell {
  max-width: 860px;
  margin: 0 auto;
  padding: 10px;
  border: 1px solid #d1d5db;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 26px rgba(15, 23, 42, 0.08);
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-box {
  flex: 1;
  position: relative;
}

.message-input {
  width: 100%;
  min-height: 44px;
  max-height: 150px;
  padding: 10px 44px 10px 8px;
  border: 0;
  border-radius: 8px;
  resize: none;
  font-size: 14px;
  font-family: inherit;
}

.message-input:focus {
  outline: none;
}

.attach-btn {
  position: absolute;
  right: 12px;
  bottom: 12px;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 18px;
  color: #9ca3af;
  transition: color 0.3s;
}

.attach-btn:hover {
  color: #667eea;
}

.send-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 9px;
  background: #111827;
  color: white;
  font-size: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.send-btn:hover:not(:disabled) {
  background: #000;
  transform: scale(1.05);
}

.send-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f3f4f6;
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}

.file-preview .name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview .remove {
  cursor: pointer;
  color: #ef4444;
}
</style>
