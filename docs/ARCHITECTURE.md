# 🏗️ Architecture & Design Documentation

> **Audience:** Junior developers learning AI engineering  
> **Application:** MyCodingAgent — A remote-first AI coding assistant

---

## Table of Contents

1. [What Does This App Do?](#1-what-does-this-app-do)
2. [The Big Picture](#2-the-big-picture)
3. [Key Concepts Explained](#3-key-concepts-explained)
4. [Project Structure](#4-project-structure)
5. [Component Deep Dives](#5-component-deep-dives)
6. [How Everything Connects](#6-how-everything-connects)
7. [Data Flow: From User Message to AI Response](#7-data-flow-from-user-message-to-ai-response)
8. [The Tool System](#8-the-tool-system)
9. [Multi-Provider Model Support](#9-multi-provider-model-support)
10. [Configuration System](#10-configuration-system)
11. [Security: The Sandbox](#11-security-the-sandbox)
12. [Testing Strategy](#12-testing-strategy)
13. [Glossary](#13-glossary)

---

## 1. What Does This App Do?

Imagine having a coding assistant that runs **on your own computer** that you can access remotely. You type a message 
like "Create a Snake game in HTML" and the AI:

1. **Reads** your project files to understand your code
2. **Writes** new files or modifies existing ones
3. **Runs** shell commands (like `npm install` or `python test.py`)
4. **Takes screenshots** of web pages to verify its work
5. **Explains** what it's doing at every step

This app is that assistant. It connects to AI models from OpenAI, Anthropic, Google, or 
even local models running on your machine (via Ollama) — all through a web-based chat 
interface.

---

## 2. The Big Picture

Here's the 10,000-foot view of the whole system:

```mermaid
graph TB
    subgraph User["👤 User (Browser)"]
        Browser["Web Browser<br/>http://127.0.0.1:7862"]
    end

    subgraph App["🖥️ Application (Python)"]
        subgraph UI["ui/ — Frontend Layer"]
            Gradio["Gradio Blocks App"]
            ChatTab["Chat Tab"]
            WorkspaceTab["Workspace Tab"]
            ProjectTab["Projects Tab"]
            DownloadTab["Download Tab"]
            SettingsTab["Settings Tab"]
        end

        subgraph Core["core/ — Configuration Layer"]
            Config["config.py<br/>Settings Manager"]
            Projects["projects.py<br/>Project Manager"]
        end

        subgraph Agent["agent/ — AI Brain Layer"]
            AgentFactory["agent.py<br/>LangGraph Agent"]
            Tools["tools.py<br/>File/Shell Tools"]
            BrowserTools["browser_tool.py<br/>Browser Tools"]
            Models["models.py<br/>Model Factory"]
            Discovery["model_discovery.py<br/>Model Lister"]
        end
    end

    subgraph External["☁️ External Services"]
        OpenAI["OpenAI API<br/>(GPT-4o)"]
        Anthropic["Anthropic API<br/>(Claude)"]
        Google["Google API<br/>(Gemini)"]
        Ollama["Ollama<br/>(Local Models)"]
    end

    subgraph Local["💾 Local Filesystem"]
        ConfigYAML["config.yaml"]
        EnvFile[".env"]
        Workspace["workspace/<br/>Your Projects"]
    end

    Browser <-->|HTTP/WebSocket| Gradio
    Gradio --> ChatTab
    Gradio --> WorkspaceTab
    Gradio --> ProjectTab
    Gradio --> DownloadTab
    Gradio --> SettingsTab

    ChatTab --> AgentFactory
    AgentFactory --> Models
    AgentFactory --> Tools
    AgentFactory --> BrowserTools
    Models --> Discovery

    Models -.->|API Call| OpenAI
    Models -.->|API Call| Anthropic
    Models -.->|API Call| Google
    Models -.->|API Call| Ollama

    Config --> ConfigYAML
    Config --> EnvFile
    Projects --> Workspace
    Tools --> Workspace

    style UI fill:#1e40af,color:#fff
    style Core fill:#7c3aed,color:#fff
    style Agent fill:#059669,color:#fff
    style External fill:#d97706,color:#fff
    style Local fill:#6b7280,color:#fff
```

### The Three Layers

Think of the app like a sandwich with three layers:

| Layer | Package | Responsibility | Analogy |
|-------|---------|---------------|---------|
| **Frontend** | `ui/` | What the user sees and clicks | The restaurant's dining room |
| **Configuration** | `core/` | Settings, project management | The restaurant's operations manual |
| **AI Brain** | `agent/` | AI logic, tools, model connections | The kitchen where the work happens |

---

## 3. Key Concepts Explained

Before diving deeper, let's define some important concepts you'll see throughout the code:

### 🤖 What is an "Agent"?

In AI engineering, an **agent** is an AI application that can **take actions**, not just generate text. 
A regular chatbot just talks. An agent can:
- Read and write files
- Run commands
- Browse the web
- Make decisions about what to do next

Think of it like the difference between someone giving you **verbal directions** vs. someone who 
**drives you there** and makes turns based on traffic.

### 🧠 What is "ReAct" (Reasoning + Acting)?

ReAct is a pattern where the AI alternates between:
1. **Thinking** — "I need to check what files exist in the project"
2. **Acting** — Calls the `list_directory` tool
3. **Observing** — Reads the tool's output
4. **Thinking again** — "Now I see the structure, I should create `index.html`"
5. **Acting again** — Calls `write_file`

```mermaid
graph LR
    Think["🧠 Think<br/>'What should I do?'"]
    Act["⚡ Act<br/>'Call a tool'"]
    Observe["👀 Observe<br/>'Read the result'"]
    
    Think --> Act --> Observe --> Think
    
    style Think fill:#3b82f6,color:#fff
    style Act fill:#ef4444,color:#fff
    style Observe fill:#22c55e,color:#fff
```

This loop continues until the agent decides the task is complete.

### 🔗 What is LangChain / LangGraph?

**LangChain** is a Python library that makes it easy to work with AI models from different 
providers (OpenAI, Anthropic, Google, etc.) using the same code. Instead of learning each 
provider's different API, you just use LangChain's unified interface.

**LangGraph** builds on LangChain to create **stateful agents** — AI programs that remember 
their conversation, use tools, and follow complex workflows. Think of LangChain as Lego bricks 
and LangGraph as the instruction manual for building something specific.

### 🎨 What is Gradio?

**Gradio** is a Python library that creates web interfaces with just a few lines of code. 
Instead of writing HTML, CSS, JavaScript, and a backend server, you describe what UI components 
you want (text boxes, buttons, dropdowns) and Gradio generates the entire web app for you.

---

## 4. Project Structure

```
agent-by-claude/
├── agent/                    # 🧠 AI Brain Layer
│   ├── __init__.py
│   ├── agent.py              # Creates the AI agent + streaming logic
│   ├── tools.py              # File/shell tools the agent can use
│   ├── browser_tool.py       # Browser automation tools (screenshots, etc.)
│   ├── models.py             # Creates AI model connections
│   └── model_discovery.py    # Lists available models from each provider
│
├── core/                     # ⚙️ Configuration Layer
│   ├── __init__.py
│   ├── config.py             # Reads/writes config.yaml and .env
│   └── projects.py           # Manages projects in workspace/
│
├── ui/                       # 🎨 Frontend Layer
│   ├── __init__.py
│   ├── app.py                # Main app entry point — wires tabs together
│   ├── chat_tab.py           # Chat interface with streaming
│   ├── workspace_tab.py      # Mini IDE (file tree + code editor + preview)
│   ├── project_tab.py        # Create/switch projects
│   ├── download_tab.py       # Download files or project ZIP
│   └── settings_tab.py       # Model selection + API key management
│
├── workspace/                # 📁 Your projects live here
│   └── snake/                # Example project
│       └── index.html
│
├── tests/                    # 🧪 Test suite
│   ├── conftest.py           # Shared test fixtures
│   ├── test_agent.py
│   ├── test_config.py
│   ├── test_env_loading.py
│   ├── test_projects.py
│   └── test_tools.py
│
├── config.yaml               # Active model + model list + active project
├── .env                      # API keys (never committed to git!)
├── .env.example              # Template for .env
├── pyproject.toml            # Python package config + dependencies
├── Makefile                  # Build/run shortcuts
└── README.md                 # Getting started guide
```

---

## 5. Component Deep Dives

### 5.1 The Agent (`agent/agent.py`)

This is the heart of the application — where AI meets action.

```mermaid
graph TD
    subgraph AgentCache["Agent Caching (get_agent)"]
        ModelID["Model ID<br/>e.g. 'openai/gpt-4o'"]
        ProjectRoot["Project Root<br/>e.g. workspace/snake/"]
        
        ModelID --> CacheKey["Cache Key<br/>(model_id, project_root)"]
        ProjectRoot --> CacheKey
        
        CacheKey --> CacheCheck{"Key matches<br/>cached agent?"}
        
        CacheCheck -->|Yes| CachedAgent["Return Cached Agent<br/>⚡ Instant!"]
        CacheCheck -->|No| BuildModel["build_model()<br/>Create LLM connection"]
        BuildModel --> MakeTools["make_tools()<br/>Create sandboxed tools"]
        MakeTools --> CreateReAct["create_react_agent()"]
        SystemPrompt["System Prompt<br/>(Instructions for AI)"] --> CreateReAct
        CreateReAct --> StoreCache["Store in Cache<br/>& Return"]
    end

    style AgentCache fill:#0f172a,color:#e2e8f0
    style CacheCheck fill:#f59e0b,color:#000
    style CachedAgent fill:#22c55e,color:#fff
    style BuildModel fill:#3b82f6,color:#fff
    style MakeTools fill:#3b82f6,color:#fff
    style CreateReAct fill:#8b5cf6,color:#fff
    style StoreCache fill:#8b5cf6,color:#fff
```

**What happens step by step:**

1. **`get_agent(model_id, project_root)`** is called when you send a chat message
2. It checks if an agent with the same model + project is already cached
3. **If cached** → returns instantly (no network calls, no rebuilding)
4. **If not cached** → creates a new LLM connection, sandboxed tools, and ReAct agent, then caches it
5. The cache is **invalidated** automatically when you switch models or projects

> **Why cache?** Building an agent involves creating an API connection, initializing tools,
> and compiling a LangGraph — all of which is unnecessary on every message when the model
> and project haven't changed. Caching makes subsequent messages significantly faster.

**The System Prompt** is like giving a new employee their job description:
> "You are an expert AI coding assistant. You have tools to read files, write files, 
> run commands... Before using any tool, explain what you're about to do. Stop when done."

### 5.2 The Streaming System (`stream_response`)

When the AI responds, it doesn't send everything at once — it **streams** chunks in real 
time, just like ChatGPT shows text appearing word by word.

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant Chat as 💬 Chat Tab
    participant Agent as 🤖 Agent
    participant LLM as ☁️ AI Model
    participant Tool as 🔧 Tool

    User->>Chat: "Create a hello world page"
    Chat->>Agent: Create agent + stream_response()
    Agent->>LLM: Send conversation history

    loop ReAct Loop (up to 30 steps)
        LLM-->>Agent: 💭 "I'll check the project structure first"
        Agent-->>Chat: yield ("text", "I'll check...")
        Chat-->>User: Shows text appearing...

        LLM-->>Agent: 🔧 Call list_directory(".")
        Agent-->>Chat: yield ("tool_call", "list_directory")
        Chat-->>User: Shows tool call in collapsible section

        Agent->>Tool: Execute list_directory(".")
        Tool-->>Agent: "📁 css\n📄 index.html"
        Agent-->>Chat: yield ("tool_result", "📁 css...")
        Chat-->>User: Shows result in collapsible section

        LLM-->>Agent: 💭 "I'll create the HTML file"
        Agent-->>Chat: yield ("text", "I'll create...")
        Chat-->>User: Shows more text...

        LLM-->>Agent: 🔧 Call write_file("index.html", "...")
        Agent->>Tool: Execute write_file(...)
        Tool-->>Agent: "OK: Wrote 245 characters"
    end

    LLM-->>Agent: "✅ Done! I created index.html"
    Agent-->>Chat: yield ("text", "Done!")
    Chat-->>User: Shows completion message
```

**The four chunk types:**

| Chunk Type | What It Contains | How It Appears in UI |
|------------|-----------------|---------------------|
| `"text"` | AI's explanations and thoughts | Normal text in the chat bubble |
| `"step"` | Step counter ("Step 1 — `list_directory`") | Animated progress indicator |
| `"tool_call"` | Tool name + arguments (JSON) | Collapsible "🔧 Tool call" section |
| `"tool_result"` | Tool output | Collapsible "📤 Result" section |

### 5.3 The Tool System (`agent/tools.py`)

Tools are functions that give the AI the ability to interact with your computer. Each tool 
is a regular Python function decorated with `@tool` from LangChain.

```mermaid
graph TB
    subgraph ToolFactory["make_tools(project_root)"]
        direction TB
        
        subgraph FileTools["📄 File Operations"]
            read["read_file<br/>Read file contents"]
            write["write_file<br/>Create/update files"]
            list["list_directory<br/>List folder contents"]
            mkdir["create_directory<br/>Create folders"]
            delete["delete_file<br/>Delete files"]
            search["search_code<br/>Search text in files"]
        end
        
        subgraph ShellTools["⚙️ System Operations"]
            shell["run_shell<br/>Run any command<br/>(60s timeout)"]
        end
        
        subgraph BrowserToolsGroup["🌐 Browser Operations (Optional)"]
            screenshot["screenshot_html<br/>Screenshot a local HTML file"]
            browse["browse_url<br/>Visit URL + screenshot"]
            content["get_page_content<br/>Get rendered HTML"]
        end
    end

    Sandbox["🔒 Sandbox<br/>All paths resolved relative<br/>to project_root<br/>Escape attempts → PermissionError"]
    
    ToolFactory --> Sandbox

    style FileTools fill:#1e40af,color:#fff
    style ShellTools fill:#b91c1c,color:#fff
    style BrowserToolsGroup fill:#7c3aed,color:#fff
    style Sandbox fill:#dc2626,color:#fff
```

**How tools work internally — the Factory Pattern:**

The `make_tools()` function uses a design pattern called a **factory**. Instead of creating 
tools globally, it creates them at runtime and "hardwires" the project path into each one. 
This is done using **closures** — inner functions that remember the variables from their 
enclosing function.

```python
def make_tools(project_root: Path) -> list:
    # This inner function "remembers" project_root even after make_tools() returns
    @tool
    def read_file(path: str) -> str:
        target = _resolve(project_root, path)  # ← project_root is "captured"
        return target.read_text()
    
    return [read_file, ...]  # Return the inner function
```

> **Why a factory?** Because different projects need different sandboxes. If you switch 
> from project "snake" to project "blog", the tools need to point to the new folder.

### 5.4 The Model System (`agent/models.py` + `agent/model_discovery.py`)

This app can talk to AI models from four different companies. The model system makes this 
seamless.

```mermaid
graph LR
    subgraph ModelID["Model ID String"]
        ID["'openai/gpt-4o'"]
    end

    subgraph BuildModel["build_model()"]
        Split["Split on '/'"]
        ID --> Split
        Split --> Provider["provider = 'openai'"]
        Split --> ModelName["model = 'gpt-4o'"]
        Provider --> InitChat["init_chat_model()"]
        ModelName --> InitChat
        InitChat --> LCModel["LangChain<br/>ChatModel"]
    end

    subgraph Providers["Supported Providers"]
        direction TB
        P1["openai → ChatOpenAI"]
        P2["anthropic → ChatAnthropic"]
        P3["google_genai → ChatGoogleGenerativeAI"]
        P4["ollama → ChatOllama"]
    end

    LCModel --> Agent["Ready for Agent"]

    style ModelID fill:#f59e0b,color:#000
    style BuildModel fill:#1e40af,color:#fff
    style Providers fill:#059669,color:#fff
```

**The model ID format** — `provider/model-name`:
- `openai/gpt-4o` → Use OpenAI's GPT-4o model
- `anthropic/claude-3-5-sonnet-20241022` → Use Anthropic's Claude 3.5 Sonnet
- `google_genai/gemini-2.0-flash` → Use Google's Gemini 2.0 Flash
- `ollama/llama3.2` → Use Meta's Llama 3.2 running locally

**Model Discovery** fetches available models dynamically:

```mermaid
sequenceDiagram
    participant UI as 🎨 Settings Tab
    participant Discovery as 🔍 model_discovery.py
    participant API as ☁️ Provider API

    UI->>Discovery: fetch_models("openai")
    Discovery->>Discovery: Reload .env (get API key)
    Discovery->>API: List available models
    
    alt API responds successfully
        API-->>Discovery: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", ...]
        Discovery-->>UI: Live model list
    else API unavailable (no key, network error)
        Discovery-->>UI: Fallback static list
    end
```

> **Why fallback lists?** If you don't have an API key for a provider yet, or the API is 
> down, the app still shows you a list of known models so you can configure things before 
> actually connecting.

### 5.5 The UI Layer (`ui/`)

The frontend is built with Gradio Blocks — a Python framework that generates a web interface.

```mermaid
graph TD
    subgraph GradioApp["ui/app.py — Main Application"]
        Header["🤖 Header Banner"]
        SharedState["Shared State<br/>• model_state<br/>• project_state"]
        
        subgraph Tabs["Tab Navigation"]
            T1["💬 Chat Tab<br/>chat_tab.py"]
            T2["🗂️ Workspace Tab<br/>workspace_tab.py"]
            T3["📂 Projects Tab<br/>project_tab.py"]
            T4["📥 Download Tab<br/>download_tab.py"]
            T5["⚙️ Settings Tab<br/>settings_tab.py"]
        end
    end

    subgraph ChatDetails["Chat Tab Details"]
        ProviderDD["Provider Dropdown<br/>(openai, anthropic, ...)"]
        ModelDD["Model Dropdown<br/>(gpt-4o, claude-3, ...)"]
        Chatbot["Chatbot Component<br/>(Message bubbles)"]
        InputBox["Text Input + Send Button"]
    end

    subgraph WorkspaceDetails["Workspace Tab Details"]
        FileTree["File Tree<br/>(Radio buttons)"]
        CodeEditor["Code Editor<br/>(Syntax highlighting)"]
        Preview["Preview Pane<br/>(HTML, images, MD, CSV, ...)"]
        LocalServer["Local HTTP Server<br/>(Port 18862)"]
    end

    T1 --> ChatDetails
    T2 --> WorkspaceDetails

    style GradioApp fill:#1e293b,color:#e2e8f0
    style Tabs fill:#334155,color:#e2e8f0
    style ChatDetails fill:#1e40af,color:#fff
    style WorkspaceDetails fill:#7c3aed,color:#fff
```

**The Event System — how UI interactions work:**

Gradio uses an event-driven pattern. You register callback functions that run when things 
happen:

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant Button as 🔘 Send Button
    participant UserMsg as 📝 user_msg()
    participant BotResp as 🤖 bot_respond()
    participant Chat as 💬 Chatbot

    User->>Button: Clicks "Send"
    Note over Button: .click() event fires
    
    Button->>UserMsg: Step 1: user_msg(text, history)
    UserMsg->>UserMsg: Append user message to history
    UserMsg->>Chat: Update chat display
    UserMsg->>User: Clear input box
    
    Note over Button: .then() chains next step
    
    Button->>BotResp: Step 2: bot_respond(history, provider, model)
    
    loop Streaming
        BotResp-->>Chat: yield updated history
        Chat-->>User: Show new content
    end
```

> **The `.then()` pattern** chains actions: first add the user's message to chat, 
> *then* start the AI response. This ensures the user sees their own message immediately.

### 5.6 The Workspace Tab — A Mini IDE

The Workspace tab is the most complex UI component. It provides a VS Code-like experience:

```mermaid
graph LR
    subgraph LeftPanel["Left Panel"]
        RefreshBtn["🔄 Refresh"]
        FileList["File List<br/>(clickable)"]
    end

    subgraph RightPanel["Right Panel"]
        subgraph EditorTab["📝 Editor Tab"]
            CodeView["Code Editor<br/>(syntax-highlighted)"]
            SaveBtn["💾 Save"]
        end
        subgraph PreviewTab["Preview Tab"]
            PreviewArea["Live Preview<br/>(HTML, images, MD, etc.)"]
            RefreshPreview["🔄 Refresh Preview"]
        end
    end

    subgraph FileServer["Background HTTP Server"]
        Server["SimpleHTTPRequestHandler<br/>Port 18862<br/>(serves project files)"]
    end

    FileList -->|Click file| CodeView
    FileList -->|If previewable| PreviewArea
    SaveBtn -->|Write to disk| FileList
    Server -->|Serves files for| PreviewArea

    style LeftPanel fill:#334155,color:#fff
    style RightPanel fill:#1e293b,color:#e2e8f0
    style FileServer fill:#059669,color:#fff
```

**Why a local HTTP server?** HTML previews need to load CSS, JavaScript, and images using 
relative paths. A simple `file://` URL wouldn't work properly, so the app starts a tiny 
HTTP server that serves your project files — just like a real web server.

---

## 6. How Everything Connects

This diagram shows which module depends on which:

```mermaid
graph BT
    subgraph UI["ui/ (Frontend)"]
        app["app.py"]
        chat["chat_tab.py"]
        workspace["workspace_tab.py"]
        project["project_tab.py"]
        download["download_tab.py"]
        settings["settings_tab.py"]
    end

    subgraph Core["core/ (Config)"]
        config["config.py"]
        projects["projects.py"]
    end

    subgraph AgentPkg["agent/ (AI Brain)"]
        agent["agent.py"]
        tools["tools.py"]
        browser["browser_tool.py"]
        models["models.py"]
        discovery["model_discovery.py"]
    end

    subgraph External["External Libraries"]
        gradio["Gradio"]
        langchain["LangChain"]
        langgraph["LangGraph"]
        playwright["Playwright"]
        dotenv["python-dotenv"]
        pyyaml["PyYAML"]
    end

    %% UI → Core
    app --> config
    app --> projects
    chat --> config
    chat --> projects
    workspace --> projects
    project --> projects
    download --> projects
    settings --> config

    %% UI → Agent
    chat --> agent
    chat --> discovery

    %% Agent internal
    agent --> models
    agent --> tools
    tools --> browser

    %% Core internal
    projects --> config

    %% Agent → Core
    models --> config

    %% External
    app --> gradio
    agent --> langgraph
    agent --> langchain
    models --> langchain
    tools --> langchain
    browser --> playwright
    config --> dotenv
    config --> pyyaml

    style UI fill:#1e40af,color:#fff
    style Core fill:#7c3aed,color:#fff
    style AgentPkg fill:#059669,color:#fff
    style External fill:#d97706,color:#fff
```

**Key insight:** Notice how `core/` has **zero dependencies on `agent/` or `ui/`**. This is 
good software design called **layered architecture** — lower layers don't know about higher 
layers. This means you could swap out the entire UI library (replace Gradio with something 
else) without changing any agent or config code.

---

## 7. Data Flow: From User Message to AI Response

Here's the complete journey of a single user message through the system:

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Gradio as Gradio Server
    participant ChatTab as chat_tab.py
    participant AgentPy as agent.py
    participant Models as models.py
    participant LLM as AI Provider API
    participant Tools as tools.py
    participant FS as File System

    User->>Browser: Types "Create a calculator app"
    Browser->>Gradio: WebSocket message

    rect rgb(30, 64, 175)
        Note over Gradio,ChatTab: Step 1: Process User Input
        Gradio->>ChatTab: user_msg(text, history)
        ChatTab->>ChatTab: Append to chat history
        ChatTab->>Gradio: Return updated history
        Gradio->>Browser: Show user's message in chat
    end

    rect rgb(5, 150, 105)
        Note over ChatTab,AgentPy: Step 2: Get or Create Agent (cached)
        ChatTab->>ChatTab: bot_respond() begins
        ChatTab->>ChatTab: get_active_project() → workspace/snake/
        ChatTab->>AgentPy: get_agent("openai/gpt-4o", project_path)
        alt Cache hit (same model + project)
            AgentPy-->>ChatTab: Return cached agent ⚡
        else Cache miss (first call, or model/project changed)
            AgentPy->>Models: build_model("openai/gpt-4o")
            Models->>Models: init_chat_model(provider="openai", model="gpt-4o")
            Models-->>AgentPy: LLM instance
            AgentPy->>Tools: make_tools(project_path)
            Tools-->>AgentPy: [read_file, write_file, ...]
            AgentPy->>AgentPy: create_react_agent(llm, tools, prompt)
            AgentPy->>AgentPy: Store in cache
            AgentPy-->>ChatTab: New compiled agent graph
        end
    end

    rect rgb(124, 58, 237)
        Note over ChatTab,FS: Step 3: Stream Response
        ChatTab->>AgentPy: stream_response(agent, history, message)
        
        loop ReAct Loop
            AgentPy->>LLM: Send messages
            LLM-->>AgentPy: AI text chunk
            AgentPy-->>ChatTab: yield ("text", chunk)
            ChatTab-->>Gradio: Update chat bubble
            Gradio-->>Browser: Live text update
            
            LLM-->>AgentPy: Tool call request
            AgentPy-->>ChatTab: yield ("tool_call", info)
            AgentPy->>Tools: Execute tool
            Tools->>FS: Read/write files
            FS-->>Tools: Result
            Tools-->>AgentPy: Tool output
            AgentPy-->>ChatTab: yield ("tool_result", output)
            ChatTab-->>Gradio: Update chat bubble
            Gradio-->>Browser: Show tool activity
        end
    end

    rect rgb(217, 119, 6)
        Note over ChatTab,Browser: Step 4: Finalize
        ChatTab->>ChatTab: Build final message with completion footer
        ChatTab-->>Gradio: Final yield
        Gradio-->>Browser: Show "What else can I help with? 🚀"
    end
```

---

## 8. The Tool System

### How the AI Decides Which Tool to Use

The AI doesn't follow a script — it decides which tool to call based on the conversation. 
This is the magic of the ReAct pattern. The system prompt tells the AI what tools are 
available and how to use them.

```mermaid
graph TD
    UserMsg["User: 'Create a hello world page'"]
    
    Think1["🧠 Think: 'I should check the project first'"]
    UserMsg --> Think1
    
    Act1["⚡ list_directory('.')"]
    Think1 --> Act1
    
    Observe1["👀 Result: '📁 css  📄 style.css'"]
    Act1 --> Observe1
    
    Think2["🧠 Think: 'Project has CSS folder.<br/>I'll create index.html'"]
    Observe1 --> Think2
    
    Act2["⚡ write_file('index.html', '<html>...')"]
    Think2 --> Act2
    
    Observe2["👀 Result: 'OK: Wrote 245 characters'"]
    Act2 --> Observe2
    
    Think3["🧠 Think: 'Let me verify by<br/>taking a screenshot'"]
    Observe2 --> Think3
    
    Act3["⚡ screenshot_html('index.html')"]
    Think3 --> Act3
    
    Observe3["👀 Result: 'Screenshot saved<br/>to index.screenshot.png'"]
    Act3 --> Observe3
    
    Done["✅ Task complete!"]
    Observe3 --> Done

    style Think1 fill:#3b82f6,color:#fff
    style Think2 fill:#3b82f6,color:#fff
    style Think3 fill:#3b82f6,color:#fff
    style Act1 fill:#ef4444,color:#fff
    style Act2 fill:#ef4444,color:#fff
    style Act3 fill:#ef4444,color:#fff
    style Observe1 fill:#22c55e,color:#fff
    style Observe2 fill:#22c55e,color:#fff
    style Observe3 fill:#22c55e,color:#fff
    style Done fill:#f59e0b,color:#000
```

### Tool Reference

| Tool | Arguments | What It Does | Example |
|------|-----------|-------------|---------|
| `read_file` | `path` | Reads a file's contents | `read_file("index.html")` |
| `write_file` | `path`, `content` | Creates or overwrites a file | `write_file("app.js", "console.log('hi')")` |
| `list_directory` | `path` (default `.`) | Shows files and folders | `list_directory("src")` |
| `create_directory` | `path` | Creates a folder (and parents) | `create_directory("src/components")` |
| `delete_file` | `path` | Deletes a single file | `delete_file("old.txt")` |
| `search_code` | `query`, `path` | Searches for text across files | `search_code("TODO", ".")` |
| `run_shell` | `command` | Runs any shell command | `run_shell("npm test")` |
| `screenshot_html` | `file_path` | Screenshots a local HTML file | `screenshot_html("index.html")` |
| `browse_url` | `url` | Visits a URL + screenshots | `browse_url("http://localhost:3000")` |
| `get_page_content` | `url` | Gets rendered HTML from a URL | `get_page_content("http://localhost:3000")` |

---

## 9. Multi-Provider Model Support

One of the coolest features of this app is **model agnosticism** — you can switch between 
AI providers without changing any code.

```mermaid
graph TB
    subgraph UserChoice["User Selects Model"]
        Selection["'google_genai/gemini-2.0-flash'"]
    end

    subgraph ModelFactory["models.py — build_model()"]
        Split["Split: provider='google_genai', model='gemini-2.0-flash'"]
        LoadEnv["Load .env → get GOOGLE_API_KEY"]
        Init["LangChain init_chat_model()"]
    end

    subgraph LangChainAdapters["LangChain Provider Adapters"]
        direction LR
        OAI["langchain-openai<br/>ChatOpenAI"]
        ANT["langchain-anthropic<br/>ChatAnthropic"]
        GOOG["langchain-google-genai<br/>ChatGoogleGenerativeAI"]
        OLL["langchain-ollama<br/>ChatOllama"]
    end

    subgraph UnifiedInterface["Unified Interface"]
        BaseChatModel["BaseChatModel<br/>.invoke() / .astream()"]
    end

    Selection --> Split --> LoadEnv --> Init
    Init --> GOOG
    OAI --> BaseChatModel
    ANT --> BaseChatModel
    GOOG --> BaseChatModel
    OLL --> BaseChatModel

    style UserChoice fill:#f59e0b,color:#000
    style ModelFactory fill:#1e40af,color:#fff
    style LangChainAdapters fill:#059669,color:#fff
    style UnifiedInterface fill:#8b5cf6,color:#fff
```

**How this works (the Adapter Pattern):**

Each AI provider has a different API. LangChain provides **adapter libraries** that wrap 
each provider's API into a common interface called `BaseChatModel`. This means the agent 
code doesn't care whether it's talking to GPT-4o, Claude, or Gemini — it just calls 
`.invoke()` or `.astream()` on the model.

This is called the **Adapter Pattern** in software design — like using a travel power 
adapter so your laptop charger works in any country.

---

## 10. Configuration System

The app uses two configuration files:

```mermaid
graph LR
    subgraph ConfigFiles["Configuration Files"]
        YAML["config.yaml<br/>──────────<br/>active_model: openai/gpt-4o<br/>active_project: snake<br/>models: [...]"]
        ENV[".env<br/>──────────<br/>OPENAI_API_KEY=sk-...<br/>ANTHROPIC_API_KEY=sk-ant-...<br/>GOOGLE_API_KEY=AIza..."]
    end

    subgraph ConfigPy["core/config.py"]
        LoadConfig["load_config()<br/>Merge defaults ← YAML"]
        SaveConfig["save_config()<br/>Write to YAML"]
        LoadEnv["load_dotenv()<br/>Load keys into os.environ"]
        SaveEnv["save_env()<br/>Update .env file"]
    end

    subgraph Usage["Who Uses What"]
        Agent["Agent<br/>(API keys)"]
        UI["UI Tabs<br/>(model, project)"]
        Discovery["Model Discovery<br/>(API keys)"]
    end

    YAML --> LoadConfig
    SaveConfig --> YAML
    ENV --> LoadEnv
    SaveEnv --> ENV

    LoadConfig --> UI
    LoadEnv --> Agent
    LoadEnv --> Discovery

    style ConfigFiles fill:#334155,color:#e2e8f0
    style ConfigPy fill:#7c3aed,color:#fff
    style Usage fill:#059669,color:#fff
```

**Why two files?**

| File | Contains | Committed to Git? | Why Separate? |
|------|----------|-------------------|---------------|
| `config.yaml` | App settings (model, project) | ✅ Yes | Settings you'd want to share |
| `.env` | Secret API keys | ❌ Never! | Keys must stay private |

**The defaults cascade:** When `load_config()` runs, it:
1. Starts with hardcoded defaults (so the app always works)
2. Overwrites with values from `config.yaml` (your preferences)
3. The result is a merged config dictionary

---

## 11. Security: The Sandbox

Every file operation the AI performs goes through a **sandbox** — a security boundary that 
prevents the AI from accessing files outside your project folder.

```mermaid
graph TD
    subgraph Allowed["✅ Allowed"]
        A1["read_file('index.html')<br/>→ workspace/snake/index.html"]
        A2["read_file('src/app.js')<br/>→ workspace/snake/src/app.js"]
        A3["list_directory('.')<br/>→ workspace/snake/"]
    end

    subgraph Blocked["❌ Blocked"]
        B1["read_file('../../.env')<br/>→ PermissionError!"]
        B2["read_file('/etc/passwd')<br/>→ PermissionError!"]
        B3["read_file('../other-project/secrets.txt')<br/>→ PermissionError!"]
    end

    Sandbox["🔒 _resolve(project_root, path)<br/>──────────<br/>1. Join project_root + path<br/>2. Resolve symlinks<br/>3. Check: does result start with project_root?<br/>4. If no → PermissionError"]

    A1 --> Sandbox
    A2 --> Sandbox
    B1 --> Sandbox
    B2 --> Sandbox

    style Allowed fill:#059669,color:#fff
    style Blocked fill:#dc2626,color:#fff
    style Sandbox fill:#f59e0b,color:#000
```

**How `_resolve()` works:**

```python
def _resolve(project_root: Path, relative_path: str) -> Path:
    resolved = (project_root / relative_path).resolve()  # Follow symlinks
    if not str(resolved).startswith(str(project_root.resolve())):
        raise PermissionError("Access denied: path is outside the project root.")
    return resolved
```

The trick is `.resolve()` — it converts `../../.env` into the actual absolute path, 
then checks if that path is still inside the project folder. Sneaky path traversal 
attacks like `../../../etc/passwd` are caught and blocked.

> ⚠️ **Note:** The `run_shell` tool does NOT have the same sandbox protection. It runs 
> arbitrary commands in the project directory. This is intentional (the AI needs to run 
> `npm install`, `python test.py`, etc.) but means you should be aware that the AI 
> could theoretically run harmful commands. The 60-second timeout provides some protection.

---

## 12. Testing Strategy

The project uses **pytest** with a clean fixture-based approach:

```mermaid
graph TD
    subgraph Fixtures["conftest.py — Shared Fixtures"]
        TmpRoot["tmp_project_root<br/>Creates a temporary folder<br/>with sample files"]
        TmpWorkspace["tmp_workspace<br/>Creates a temporary<br/>workspace/ directory"]
    end

    subgraph Tests["Test Files"]
        TestTools["test_tools.py<br/>• read_file works<br/>• write_file creates<br/>• sandbox blocks escape<br/>• search finds text"]
        TestConfig["test_config.py<br/>• load_config merges defaults<br/>• save_config persists<br/>• round-trip works"]
        TestProjects["test_projects.py<br/>• list_projects finds dirs<br/>• create_project works<br/>• switch project works"]
        TestAgent["test_agent.py<br/>• Agent creates successfully<br/>• Stream function exists"]
        TestEnv["test_env_loading.py<br/>• .env loads into os.environ<br/>• Keys update correctly"]
    end

    Fixtures --> Tests

    style Fixtures fill:#f59e0b,color:#000
    style Tests fill:#1e40af,color:#fff
```

**Run tests with:**
```bash
make test  # or: .venv/bin/pytest tests/ -v
```

---

## 13. Glossary

| Term | Definition |
|------|-----------|
| **Agent** | An AI system that can take actions (use tools) to complete tasks, not just generate text |
| **ReAct** | A pattern where AI alternates between Reasoning (thinking) and Acting (using tools) |
| **LangChain** | Python library providing a unified interface to multiple AI model providers |
| **LangGraph** | Library built on LangChain for creating stateful AI agents with tool use |
| **Gradio** | Python library for quickly building web UIs for machine learning applications |
| **Tool** | A function the AI can call to interact with the outside world (files, shell, browser) |
| **Streaming** | Sending data piece by piece as it's generated, rather than all at once |
| **Sandbox** | A security boundary that restricts where the AI can read/write files |
| **System Prompt** | Instructions given to the AI that define its behavior and capabilities |
| **Provider** | A company offering AI model APIs (OpenAI, Anthropic, Google, Ollama) |
| **Closure** | A function that remembers variables from its enclosing scope (used in the tool factory) |
| **Factory Pattern** | A design pattern where a function creates and returns other objects/functions |
| **Adapter Pattern** | A design pattern that wraps different interfaces behind a common one |
| **WebSocket** | A protocol for real-time bidirectional communication between browser and server |
| **Fixture** | In testing, a reusable setup that creates test data (like a temporary directory) |
| **Headless Browser** | A browser without a visible window, used for automation and screenshots |

---

> **Next Steps for Learning:**
> 1. Read through `agent/tools.py` — it's the simplest file and shows how tools work
> 2. Try modifying the system prompt in `agent/agent.py` to change the AI's behavior
> 3. Add a new tool (e.g., `count_lines` that counts lines in a file)
> 4. Run `make test` and study how the tests validate each component
> 5. Read the [LangGraph documentation](https://python.langchain.com/docs/langgraph) to learn more about agents
