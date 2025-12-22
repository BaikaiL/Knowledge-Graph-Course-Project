<script setup>
import { computed, ref } from 'vue'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8001'

const question = ref('')
const answer = ref('')
const status = ref('idle')
const error = ref('')
const controller = ref(null)

const isLoading = computed(() => status.value === 'loading')

const ask = async () => {
  const value = question.value.trim()
  error.value = ''
  answer.value = ''

  if (!value) {
    error.value = 'Please enter a question.'
    return
  }

  if (controller.value) {
    controller.value.abort()
  }

  const abortController = new AbortController()
  controller.value = abortController
  status.value = 'loading'

  try {
    const url = `${apiBase}/api/qa?question=${encodeURIComponent(value)}`
    const response = await fetch(url, { signal: abortController.signal })

    if (!response.ok || !response.body) {
      throw new Error(`Request failed (${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    while (true) {
      const { value: chunk, done } = await reader.read()
      if (done) break
      answer.value += decoder.decode(chunk, { stream: true })
    }

    answer.value += decoder.decode()
    status.value = 'done'
  } catch (err) {
    if (err?.name === 'AbortError') {
      status.value = 'idle'
      return
    }
    status.value = 'error'
    error.value = err?.message || 'Request failed.'
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
  answer.value = ''
  error.value = ''
  status.value = 'idle'
}
</script>

<template>
  <div class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">Knowledge Graph QA</p>
        <h1>Ask about herbal tea knowledge</h1>
        <p class="subtitle">
          Streamed answers from your FastAPI controller at
          <span class="pill">{{ apiBase }}</span>
        </p>
      </div>
      <div class="status" :data-state="status">
        <span v-if="status === 'loading'">Streaming response...</span>
        <span v-else-if="status === 'done'">Done</span>
        <span v-else-if="status === 'error'">Error</span>
        <span v-else>Ready</span>
      </div>
    </header>

    <section class="panel">
      <label class="label" for="question">Your question</label>
      <textarea
        id="question"
        v-model="question"
        rows="5"
        placeholder="Ask about ingredients, effects, or combinations..."
      />

      <div class="actions">
        <button class="primary" type="button" :disabled="isLoading" @click="ask">
          Ask
        </button>
        <button class="ghost" type="button" :disabled="!isLoading" @click="stop">
          Stop
        </button>
        <button class="ghost" type="button" @click="clearAll">
          Clear
        </button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <section class="panel output">
      <div class="output-header">
        <h2>Answer</h2>
        <span class="hint">Streaming text from `/api/qa`</span>
      </div>
      <pre class="answer">{{ answer || 'No answer yet.' }}</pre>
    </section>
  </div>
</template>
