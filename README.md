# Neural Claude

A fully autonomous, multi-threaded LLM Coding Agent engine built with Textual TUI. 
Neural Claude allows you to run a powerful prompt-driven application seamlessly isolated natively in any of your folders.

## Global Installation 

To install `neuralclaude` as a global command on your machine from the source:

```bash
# Clone the repository
git clone https://github.com/Ayush-soni-12/AI-AGENT.git
cd AI-AGENT

# Install globally using pip
pip install .
```

*Note: You can also use `pipx install .` if you prefer managed isolated binaries!*

## Configuration & API Key

You do **not** need to mess with `.env` files. The very first time you type `neuralclaude` in your terminal, the application will automatically pause and run a CLI **Setup Wizard**.
It will ask you to supply your Provider (Gemini or OpenRouter) and securely lock your API key globally inside your Operating System at `~/.config/neuralclaude/settings.json`.

If you ever need to view your keys or change your models, type `/config` inside the application!

## How It Works

Because Neural Claude is context-aware via SQLite databases and Session management, you simply navigate into **ANY** project folder on your computer and start typing.

```bash
cd ~/path/to/any/project/
neuralclaude
```

Upon launching:
1. Neural Claude will automatically generate a localized `.agent_memory.db` for the project.
2. It tracks multiple conversation branches within `.agent_sessions/`.
3. Use `/new` to create a new session thread.
4. Use `/past` to navigate backwards to a previous conversation context.

## Extending with MCP Servers (Model Context Protocol)

Neural Claude natively supports the **Model Context Protocol (MCP)**. This means the AI can use any custom tools, talk to databases (like PostgreSQL), or interact with third-party APIs (like GitHub, Slack, or Brave Search) **without writing any code**.

Just add your MCP servers to `~/.config/neuralclaude/mcp_servers.json`:

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

Once configured, launch `neuralclaude` and type `/mcp` to see all connected tools!
