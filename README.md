# Neural Claude 🧠🤖

A fully autonomous, multi-threaded LLM Coding Agent engine built with a beautiful Textual TUI. 

Unlike standard conversational AIs, Neural Claude is a **general-purpose autonomous developer**. It seamlessly isolates its memory natively inside any of your project folders and possesses the tools to read files, write code, run terminal commands, visually debug web apps, and manage your Git repository.

---

## 🚀 Key Features: What makes it different?

Most AI agents are just chat wrappers or force you into a specific IDE. Neural Claude acts as an independent developer residing directly in your terminal.

* **👀 Visual Self-Correction (Autonomous Frontend Developer):** Neural Claude features full Multimodal Vision support. You can drag and drop mockups directly into the terminal. Even better, it uses an invisible Playwright browser to **take screenshots of its own local dev servers** (like `localhost:5173`) and automatically fixes its own CSS/UI mistakes!
* **🔄 Autonomous Execution & Self-Healing:** The agent loops infinitely to complete complex tasks. If it runs tests and they fail, or if it hallucinates invalid JSON, its built-in sanitizers and loop engine automatically catch the error, feed it back to the LLM, and self-correct without crashing.
* **📂 Localized Project Memory:** Neural Claude isolates its memory per project using SQLite (`.agent_memory.db`). It knows exactly what you were working on in `Project A` without bleeding context into `Project B`.
* **🌲 Multi-threaded Sessions:** Don't like the direction the AI is taking? Type `/new` to branch into a fresh session, or use `/past` to navigate backwards to a previous conversation context.
* **✨ Real-time Diff Previews:** When the agent modifies your codebase, it instantly renders Git-style unified diffs directly in the chat UI so you always know exactly what changed.
* **🛠️ Native MCP Support:** Seamlessly connect to external databases, Slack, or Brave Search by adding any Model Context Protocol (MCP) server without writing a single line of code.

---

## 🧰 Built-in Capabilities (Tools)

Neural Claude comes pre-installed with a suite of built-in tools that give it full system access (with your permission):
* `browser_screenshot`: Launches a headless browser, navigates to a URL, and captures a screenshot for visual debugging.
* `shell`: Runs arbitrary bash commands (install dependencies, start servers, etc).
* `replace_in_file` / `write_file` / `read_file`: Granular file operations for precise code editing.
* `grep_search` / `list_dir`: Navigates and searches your entire codebase instantly.
* `run_tests`: Automatically runs your test suite and pipes failures back for autonomous fixing.
* `web_search`: Accesses the internet to read documentation or search for solutions.

---

## 💻 Commands

Neural Claude is entirely prompt-driven, but provides powerful slash commands for meta-operations:

| Command | Description |
|---|---|
| `/new` | Branch into a fresh session thread (old thread saved to `/past`) |
| `/past` | List all saved session threads for this project |
| `/past [N]` | Resume session thread number N |
| `/clear` | Clear the screen only — session keeps going |
| `/clear memory` | Wipe ALL project data (memory + sessions) for a fresh start |
| `/commit` | AI writes a commit message for your changes, opens preview |
| `/pr` | AI writes a PR title + description, opens preview to create PR |
| `/test` | Run tests/linter; if they fail the agent auto-fixes and retries |
| `/mcp` | Show connected MCP servers and their available tools |
| `/config` | Open the UI Settings panel to swap models (Claude, Gemini, GPT-4o) |
| `/help` | Show the help message |

---

## ⚙️ Installation & Setup

To install `neuralclaude` as a global command on your machine from the source:

```bash
# Clone the repository
git clone https://github.com/Ayush-soni-12/AI-AGENT.git
cd AI-AGENT

# Install globally
pip install . 
# Note: You can also use `pipx install .` for an isolated binary
```

### Configuration
You do **not** need to mess with `.env` files. The very first time you type `neuralclaude` in your terminal, the application will automatically pause and run a UI **Setup Wizard**.
It will securely lock your API key globally inside your Operating System at `~/.config/neuralclaude/settings.json`.

### Usage
Simply navigate to **ANY** folder on your computer and start typing!

```bash
cd ~/path/to/any/project/
neuralclaude
```

## 🔌 Extending with MCP
To add custom MCP servers (like PostgreSQL, GitHub, etc.), edit `~/.config/neuralclaude/mcp_servers.json`:
```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/username"]
    }
  ]
}
```
Launch `neuralclaude` and type `/mcp` to verify they are connected!
