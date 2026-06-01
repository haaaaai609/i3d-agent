# Vue 3 Frontend Rebuild Design

**Date:** 2026-06-01
**Status:** Draft
**Goal:** Rebuild the I3D Agent System frontend using Vue 3 while preserving all existing functionality.

## Overview

The current frontend is a single HTML file (`/frontend/static/chat.html`) containing a chat interface for the I3D Agent System. This design specifies a Vue 3 rebuild that maintains 100% functional parity while improving maintainability and developer experience.

## Stack Selection

**Chosen: Vue 3 + Vite + Composition API**

- **Vue 3**: Modern reactive framework with excellent TypeScript support
- **Vite**: Fast development server with HMR, optimized production builds
- **Composition API**: Future-forward API, better code organization and reusability
- **Plain CSS**: Port existing styles from HTML (no CSS framework dependency)

## Project Structure

```
/frontend/
├── index.html              # Entry HTML (minimal)
├── package.json            # Dependencies and scripts
├── vite.config.js          # Vite configuration
├── public/                 # Static assets (favicon, etc.)
└── src/
    ├── main.js             # App entry point
    ├── App.vue             # Root component
    ├── components/
    │   ├── Sidebar.vue              # Agent selection & settings panel
    │   ├── ChatArea.vue             # Main chat container
    │   ├── MessageList.vue          # Scrollable messages area
    │   ├── MessageItem.vue          # Single message with formatting
    │   ├── InputArea.vue            # Message input & send button
    │   ├── WelcomeScreen.vue        # Initial welcome with quick actions
    │   ├── ThoughtProcess.vue       # Collapsible thought steps display
    │   └── SourcesList.vue          # Sources/references display
    ├── composables/
    │   ├── useChat.js               # Chat logic & API integration
    │   └── useAgents.js             # Agent selection state & logic
    ├── styles/
    │   └── main.css                  # Ported CSS from original HTML
    └── utils/
        └── api.js                    # API client wrapper
```

## Component Specification

### App.vue (Root)
- Layout: Sidebar + ChatArea side-by-side
- Provides global state to children via props/composables
- Handles window-level events (keyboard shortcuts)

### Sidebar.vue
**Props:** None
**Emits:** `agent-selected`, `tenant-changed`, `user-changed`

**Features:**
- System header with logo/title
- 9 agent selection buttons with icons and badges
- Active state highlighting
- Tenant dropdown (huabei, shenfa, meidi, dongjiang)
- User ID input field

**State:**
```js
const currentAgent = ref('general')
const tenantId = ref('huabei')
const userId = ref('demo_user')
```

### ChatArea.vue
**Props:** `currentAgent`, `tenantId`, `userId`
**Emits:** `stream-mode-toggle`

**Features:**
- Chat header with agent title and online status
- Stream mode checkbox
- Status indicator (online/offline)
- Content area (messages or welcome screen)
- Input area at bottom

### MessageList.vue
**Props:** `messages` (array), `isTyping` (boolean)

**Features:**
- Scrollable message container
- Auto-scroll to latest message
- `<TransitionGroup>` for smooth message entry
- Typing indicator when `isTyping` is true

### MessageItem.vue
**Props:** `message` (object with type, content, agentType, sources, thoughtProcess)

**Features:**
- Different styles for user vs assistant messages
- Agent badge color coding
- Markdown-style code block formatting
- Collapsible sources display
- Collapsible thought process display

### InputArea.vue
**Props:** None
**Emits:** `send`

**Features:**
- Textarea with auto-resize
- Shift+Enter for new line, Enter to send
- File attachment button with preview
- Send button with loading state

### WelcomeScreen.vue
**Props:** None
**Emits:** `quick-action`

**Features:**
- Welcome message and description
- 3 quick action cards (search, rag, process)
- Disappears after first message

## Composables

### useChat.js
```js
export function useChat() {
  const messages = ref([])
  const isTyping = ref(false)
  const sessionId = ref(null)
  const attachedFile = ref(null)

  async function sendMessage(text, userId, tenantId) {
    // Add user message
    // Call API (stream or normal)
    // Handle response
  }

  async function streamChat(payload) {
    // SSE stream handling
  }

  function addMessage(type, content, metadata) {
    // Add to messages array
  }

  return {
    messages,
    isTyping,
    sessionId,
    attachedFile,
    sendMessage,
    streamChat,
    addMessage
  }
}
```

### useAgents.js
```js
const AGENTS = {
  general: { title: '通用对话', icon: '💬', badge: '默认' },
  search: { title: '3D 模型搜索', icon: '🔍', badge: 'Search' },
  '2d-search': { title: '2D 图片搜索', icon: '🖼️', badge: 'Search' },
  rag: { title: '技术文档', icon: '📚', badge: 'RAG' },
  api: { title: 'API 参考', icon: '🔧', badge: 'RAG' },
  deploy: { title: '部署指南', icon: '🚀', badge: 'RAG' },
  troubleshoot: { title: '故障排查', icon: '🔧', badge: 'RAG' },
  process: { title: '任务状态', icon: '⚙️', badge: 'Process' },
  history: { title: '处理历史', icon: '📋', badge: 'Process' }
}

export function useAgents() {
  const currentAgent = ref('general')

  function selectAgent(agent) {
    currentAgent.value = agent
  }

  return {
    AGENTS,
    currentAgent,
    selectAgent
  }
}
```

## API Integration

### Base Configuration
```js
const API_BASE = window.location.origin
```

### Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check |
| POST | `/api/v1/chat` | Normal chat (non-streaming) |
| POST | `/api/v1/chat/stream` | SSE streaming chat |

### Request Format
```js
{
  message: string,
  user_id: string,
  tenant_id: string,
  session_id?: string
}
```

### SSE Stream Format
```js
data: {"type": "content", "content": "..."}
data: {"type": "done", "session_id": "...", "sources": [...]}
data: {"type": "error", "error": "..."}
```

## Styling Strategy

### Port Existing CSS
The current `chat.html` contains ~520 lines of well-structured CSS. This will be:
1. Extracted to `src/styles/main.css`
2. Scoped to components where needed
3. Enhanced with Vue-specific transitions

### Key Visual Elements (Preserved)
- Background: Linear gradient `#667eea` → `#764ba2`
- Container: White, rounded, shadow
- Sidebar: Dark `#1a1a2e`
- Agent badges: Color-coded by type
- Messages: Bubbles with rounded corners

### Vue-Enhanced Animations
```css
/* Message entry animation */
.message-enter-active {
  animation: fadeIn 0.3s ease;
}

/* Smooth hover transitions */
.agent-btn {
  transition: all 0.3s;
}
```

## Functional Parity Checklist

All features from the original HTML will be preserved:

- [x] 9 agent types selection
- [x] Tenant selection (4 options)
- [x] User ID input
- [x] Stream mode toggle
- [x] SSE streaming chat
- [x] Normal chat mode
- [x] File upload support
- [x] Sources/references display
- [x] Thought process display
- [x] Code block formatting
- [x] Quick action prompts
- [x] Welcome screen
- [x] Typing indicator
- [x] Online/offline status
- [x] Auto-scroll to latest
- [x] Session persistence
- [x] Markdown formatting
- [x] Error handling

## Development Workflow

### Installation
```bash
cd /frontend
npm install
```

### Development
```bash
npm run dev
# Runs on http://localhost:5173
# Proxy configured for API requests
```

### Build
```bash
npm run build
# Output: /frontend/dist
```

### Deployment
The built `dist/` folder can be served by:
- Nginx/Apache as static files
- The FastAPI backend with static file mounting
- Any static hosting service

## Vite Configuration

```js
// vite.config.js
export default {
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
}
```

## Package.json Dependencies

```json
{
  "name": "i3d-agent-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

## Implementation Order

1. **Setup Phase**
   - Initialize Vite + Vue 3 project
   - Configure vite.config.js
   - Create folder structure

2. **Core Components**
   - App.vue layout
   - Sidebar.vue
   - ChatArea.vue
   - InputArea.vue

3. **Message Handling**
   - MessageList.vue
   - MessageItem.vue
   - useChat composable

4. **Enhancements**
   - WelcomeScreen.vue
   - SourcesList.vue
   - ThoughtProcess.vue
   - Transitions and animations

5. **Integration**
   - API integration
   - SSE streaming
   - Error handling
   - Testing with backend

## Success Criteria

1. All 9 agent types selectable and functional
2. Chat works in both stream and normal modes
3. File upload functional
4. Sources and thought process display correctly
5. Tenant and user ID settings respected
6. API health check reflected in UI
7. Build produces working static files
8. No console errors in production build

## Notes

- The existing `chat.html` will be replaced but can be kept as backup
- The API contract remains unchanged - no backend modifications needed
- Session ID generation and persistence matches original behavior
- File upload UI exists but backend integration may need verification
