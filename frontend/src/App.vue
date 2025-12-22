<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8001'

const question = ref('')
const status = ref('idle')
const error = ref('')
const controller = ref(null)
const messages = ref([])
const typingTimer = ref(null)

const quickQuestions = [
  '金银花茶有什么功效？',
  '夏季适合喝什么茶？',
  '清热解毒的代茶饮有哪些？',
  '上火时可以喝什么茶？',
]

const isLoading = computed(() => status.value === 'loading')
const typingSpeed = 24
let pendingText = ''
let activeMessage = null

const startTyping = () => {
  if (typingTimer.value) return
  typingTimer.value = setInterval(() => {
    if (!activeMessage || pendingText.length === 0) {
      clearInterval(typingTimer.value)
      typingTimer.value = null
      return
    }
    activeMessage.content += pendingText.slice(0, 1)
    pendingText = pendingText.slice(1)
  }, typingSpeed)
}

const enqueueTyping = (message, text) => {
  activeMessage = message
  pendingText += text
  startTyping()
}

const ask = async (preset) => {
  const value = (preset ?? question.value).trim()
  error.value = ''

  if (!value) {
    error.value = '请输入问题后再发送。'
    return
  }

  if (controller.value) {
    controller.value.abort()
  }

  question.value = value
  messages.value.push({ role: 'user', content: value })
  const assistantMessage = reactive({ role: 'assistant', content: '' })
  messages.value.push(assistantMessage)
  activeMessage = assistantMessage
  pendingText = ''

  const abortController = new AbortController()
  controller.value = abortController
  status.value = 'loading'

  try {
    const url = `${apiBase}/api/qa?question=${encodeURIComponent(value)}`
    const response = await fetch(url, { signal: abortController.signal })

    if (!response.ok || !response.body) {
      throw new Error(`请求失败 (${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    while (true) {
      const { value: chunk, done } = await reader.read()
      if (done) break
      enqueueTyping(assistantMessage, decoder.decode(chunk, { stream: true }))
    }

    enqueueTyping(assistantMessage, decoder.decode())
    status.value = 'done'
  } catch (err) {
    if (err?.name === 'AbortError') {
      status.value = 'idle'
      return
    }
    status.value = 'error'
    error.value = err?.message || '请求失败。'
  } finally {
    controller.value = null
  }
}

const stop = () => {
  if (controller.value) {
    controller.value.abort()
  }
}

const clearAll = () => {
  question.value = ''
  error.value = ''
  messages.value = []
  status.value = 'idle'
  pendingText = ''
  activeMessage = null
  if (typingTimer.value) {
    clearInterval(typingTimer.value)
    typingTimer.value = null
  }
}

onBeforeUnmount(() => {
  if (typingTimer.value) {
    clearInterval(typingTimer.value)
    typingTimer.value = null
  }
})
</script>

<template>
  <div class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">知识图谱问答</p>
        <h1>中药代茶饮智能推荐系统</h1>
        <p class="subtitle">
          当前接口地址：<span class="pill">{{ apiBase }}</span>
        </p>
      </div>
      <div class="status" :data-state="status">
        <span v-if="status === 'loading'">正在生成回答...</span>
        <span v-else-if="status === 'done'">已完成</span>
        <span v-else-if="status === 'error'">发生错误</span>
        <span v-else>可开始提问</span>
      </div>
    </header>

    <section class="panel chat-panel">
      <div class="chat-list">
        <div v-if="messages.length === 0" class="empty">
          还没有对话，试试下面的快捷问题。
        </div>
        <div
          v-for="(item, index) in messages"
          :key="index"
          class="message"
          :data-role="item.role"
        >
          <div class="bubble">{{ item.content || '...' }}</div>
        </div>
      </div>
    </section>

    <section class="panel input-panel">
      <label class="label" for="question">输入问题</label>
      <textarea
        id="question"
        v-model="question"
        rows="4"
        placeholder="例如：菊花和枸杞能一起泡吗？"
      />

      <div class="actions">
        <button class="primary" type="button" :disabled="isLoading" @click="ask">
          发送
        </button>
        <button class="ghost" type="button" :disabled="!isLoading" @click="stop">
          停止
        </button>
        <button class="ghost" type="button" @click="clearAll">
          清空
        </button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div class="quick">
        <button
          v-for="item in quickQuestions"
          :key="item"
          class="pill-btn"
          type="button"
          :disabled="isLoading"
          @click="ask(item)"
        >
          {{ item }}
        </button>
      </div>
    </section>
  </div>
</template>
