```markdown
[![DMC - Developer Agent Demo](https://via.placeholder.com/1200x400?text=DMC+-+Developer+Agent+Demo)](https://example.com/demo-video-url)

```text
██████╗ ███████╗██████╗ ██╗   ██╗ ██████╗     ███╗   ███╗ ██████╗
██╔══██╗██╔════╝██╔══██╗██║   ██║██╔════╝     ████╗ ████║██╔════╝
██║  ██║█████╗  ██████╔╝██║   ██║██║  ███╗    ██╔████╔██║██║     
██║  ██║██╔══╝  ██╔══██╗██║   ██║██║   ██║    ██║╚██╔╝██║██║     
██████╔╝███████╗██████╔╝╚██████╔╝╚██████╔╝    ██║ ╚═╝ ██║╚██████╗
╚═════╝ ╚══════╝╚═════╝  ╚═════╝  ╚═════╝     ╚═╝     ╚═╝ ╚═════╝                                                              
```

# DMC – Developer Agent

DMC – Developer Agent is a **Python desktop application** built with **PyQt6** that acts as an intelligent, locally‑aware coding assistant.

Unlike traditional *web-based* chat AIs, DMC connects directly to your **local file system** to:

- Extract your **project folder structure**,
- Optionally read **file contents**, and
- Use that context to provide **precise, project-aware answers** to your questions.

It is designed as a practical tool for developers who want a tightly integrated assistant that understands their *actual* codebase.

---

## Key Features

### 🧠 Project-Aware Coding Assistant

- Built on **PyQt6** for a responsive desktop GUI.
- Integrates with your **local project directory**:
  - Extracts folder structure.
  - Reads selected file contents for richer context.
- Lets you ask questions like:
  - “Where is the API client defined and how does it work?”
  - “Refactor the main window logic to use a controller pattern.”
  - “Explain how authentication is implemented in this project.”

### 🧩 Smart Context Filtering (Brain + Worker)

DMC implements a **Smart Context Filtering** pipeline to reduce token usage and mitigate rate limits:

- **Brain Model** (`gpt-5-mini` in the app logic):
  - Receives the **project structure** and the **user question**.
  - Selects only the **most relevant files** (JSON list of paths).
  - Can run in:
    - Normal mode – “include anything that might be relevant”.
    - Aggressive mode – “only the top few critical files”.

- **Worker Model** (`gpt-5.1` in the app logic):
  - Receives:
    - A **system prompt** built from:
      - The full structure, and
      - The contents of the files selected by the Brain.
    - The **chat history** and the **current user prompt**.
  - Produces the **final answer** to the user.

- **Fallback & Retry Logic**:
  - Handles **rate limit errors (429)** with retries:
    1. Smart filtering.
    2. Aggressive filtering.
    3. Structure‑only (no content) as a last resort.
  - Ensures the app remains usable even for **large projects**.

### 💬 Project Chat Tab

- **Project Folder Selection**:
  - Select a folder.
  - Extract its structure (and optionally contents).
- **Smart filtering toggle**:
  - Enable / disable Smart Context Filtering.
- **Markdown Rendering**:
  - Optional Markdown formatting of AI responses.
- **Chat Controls**:
  - Copy / export conversation.
  - Clear chat.
  - Switch between:
    - **“Use API”** – normal mode.
    - **“Show Prompt”** – display the full prompt that would be sent (for debugging / transparency).

### 🧪 Code Sandbox Tab

DMC also includes a **Code Sandbox** for rapid prototyping:

- **Generate Code**:
  - Describe a function, script, or snippet.
  - The agent generates:
    - A short explanation.
    - A complete `python` code block.
- **Edit In-Place**:
  - Generated code is copied into an **editable text area**.
  - You can tweak it before running.
- **Execute Code Safely**:
  - Sandbox executes the code in a **separate Python process**.
  - Captures:
    - `stdout`
    - `stderr`
  - Protects the GUI thread from freezing.
- **Auto-Debugging Flow**:
  - If execution fails:
    - You can let the agent analyze:
      - The **original request**,
      - The **failed code**, and
      - The **error message**.
    - It proposes **corrected code** in a new block.

> ⚠️ **Security notice:** Never execute untrusted code. Review all generated code before running it on your machine.

---

## Context & Credits

This project is part of the **“Coding for IA” (Coding for AI & Data Science)** curriculum.

- **Authors**:
  - **Jérémie ONDZAGHE**
  - **Dylan ONDO**

The project was **initially started during an internship**, then **improved and modernized** by the authors to:

- Update the UI/UX,
- Integrate a more robust context extraction system,
- Add Smart Context Filtering (Brain + Worker),
- Introduce the Code Sandbox with auto-debugging.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/dmc-developer-agent.git
cd dmc-developer-agent
```

### 2. Create & Activate a Virtual Environment (Recommended)

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies

Minimal runtime requirements (as used in the codebase):

```bash
pip install PyQt6 requests
```

Optional extras (for enhanced rendering and document parsing):

```bash
pip install pygments markdown python-docx openpyxl xlrd
```

These provide:

- **Markdown** rendering with **code highlighting** in the chat.
- Ability to parse:
  - `.docx` documents,
  - `.xlsx` / `.xls` spreadsheets,
  - `.ipynb` notebooks (via JSON parsing).

---

## Configuration & Launch

DMC requires a valid **OpenAI API key** provided via the `OPENAI_API_KEY` environment variable.  
On Windows, you can use the following **Batch (.bat)** script to configure and launch the application.

1. Create a new file, e.g. `run_dmc.bat`.
2. Paste the following content.
3. **Modify the path** and **API key placeholder** before use.

```bat
@echo off
:: Change the current working directory to the project folder
:: The /d switch ensures the drive letter changes correctly if needed
cd /d "C:\Users\#########################"

:: Set the OpenAI API Key as an environment variable for this session
set OPENAI_API_KEY=sk-proj-#####################

:: Execute the Python script and pass any command-line arguments (%*)
python main.py %*

:: Check the exit code (%errorlevel%)
:: If it is not equal to 0, an error occurred, so we pause to read the output
if %errorlevel% neq 0 (
    echo.
    echo An error occurred.
    pause
)
```

### Notes

- **Important**: Replace:
  - `C:\Users\#########################` with the **actual path** to your project folder.
  - `sk-proj-#####################` with your **real OpenAI API key**.
- The `OPENAI_API_KEY` variable is set **only for the lifetime of this console session** (it is not stored permanently).
- On double‑clicking the `.bat` file:
  - The script changes to your project directory.
  - Sets the API key.
  - Runs `python main.py`.

### Direct Launch (Alternative)

If you prefer running directly from a terminal (after setting the env var):

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-proj-#####################"
python main.py
```

```bash
# macOS / Linux (bash/zsh)
export OPENAI_API_KEY="sk-proj-#####################"
python main.py
```

---

## Usage Overview

### 1. Select Project Folder

1. Start the application.
2. Click **“Select Project Folder”**.
3. Choose the root folder of the project you want DMC to analyze.
4. Click **“Reload”** to refresh the extracted structure if you change settings.

The **left panel** displays:

- The **ASCII logo**.
- Buttons for:
  - Folder selection,
  - File extensions,
  - Exclusions,
  - Font size controls.
- A **read‑only context view** of:
  - Folder structure,
  - (Optionally) file contents.

### 2. Adjust Extensions & Exclusions

- **Extensions**:
  - Control which file types are scanned for content.
- **Exclusions**:
  - Exclude virtual environments, caches, `.git`, `node_modules`, and other heavy directories by default.
  - Add your own rules for large or irrelevant folders.

### 3. Use the Project Chat

In the **Project Chat** tab:

- Type your question in the **prompt input**.
- Click **“Ask”** to query the Worker model through Smart Context Filtering.
- Optionally:
  - Enable **Markdown** rendering.
  - Toggle **Smart Context Filtering**.
  - Use **“Show Prompt”** mode to inspect the full prompt DMC builds.

You can:

- **Copy Response** – copy the conversation to the clipboard.
- **Export Response** – save the conversation to a text file.
- **Clear Chat** – reset history.

### 4. Use the Code Sandbox

In the **Code Sandbox** tab:

1. Enter a **code request** (e.g., “Write a function to parse this log file format…”).
2. Click **“Generate Code”**:
   - DMC injects:
     - Project context (if loaded),
     - Current sandbox code (if any),
     - Your request.
   - The agent responds with:
     - Explanation,
     - Full Python code block.
3. Review and optionally **edit** the generated code in the **sandbox editor**.
4. Click **“Execute Sandbox Code”** to run it in a separate process.
5. If an error occurs, you can authorize the agent to **auto‑debug** it.

---

## Project Structure (Simplified)

Typical high‑level structure:

```text
.
├── main.py        # PyQt6 GUI: Project Chat and Code Sandbox
├── utils.py       # GPT workers, code execution, project context extraction, markdown rendering
├── README.md      # This documentation
└── (optional assets: icons, screenshots, batch launchers, etc.)
```

---

## License

This project is distributed under the **MIT License**.

You are free to:

- Use,
- Modify,
- Distribute,

the software, provided that the MIT License terms are respected and the original copyright 
and license notice are included in your copies or substantial portions of the software.

See the `LICENSE` file (or the standard MIT License text) for full details.

---
```
