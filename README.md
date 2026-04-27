# Neural Claude

A fully autonomous, multi-threaded LLM Coding Agent engine built with Textual TUI. 
Neural Claude allows you to run a powerful prompt-driven application seamlessly isolated natively in any of your folders.

## Global Installation 

To install `neuralclaude` as a global command on your machine from the source:

```bash
# Clone the repository
git clone https://github.com/ayush/neuralclaude.git
cd neuralclaude

# Install globally using pip
pip install -e .
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
