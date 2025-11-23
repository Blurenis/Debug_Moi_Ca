# -----------------------------------------------------------------------------
# Imports and Initial Setup
# -----------------------------------------------------------------------------
import sys
import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Union

from PyQt6 import QtWidgets, QtGui, QtCore

# --- Custom Utilities Import ---
# Ensure utils.py is present in the same directory
from utils import (
    GptWorker,
    CodeExecutionWorker,
    ProjectContextExtractor,
    markdown_to_html,
    MARKDOWN_AVAILABLE
)

# -----------------------------------------------------------------------------
# GUI Main Application
# -----------------------------------------------------------------------------
class HolaIbotApp(QtWidgets.QWidget):
    """
    Main application window for the DMC Developer Agent.
    
    This class handles the GUI initialization, signal/slot connections, 
    and state management for both the Project Chat and the Code Sandbox.
    """

    def __init__(self) -> None:
        super().__init__()
        
        # --- State Management: Tab 1 (Project Chat) ---
        self.extractor: ProjectContextExtractor = ProjectContextExtractor()
        self.chat_history: List[Dict[str, str]] = []
        self.loaded_context: str = ""  # Stores the directory structure text
        self.loaded_path: Optional[str] = None
        self.gpt_worker: Optional[GptWorker] = None
        
        # Configuration Defaults
        self.context_font_size: int = 7
        self.conversation_font_size: int = 8
        self.markdown_enabled: bool = False 
        self.pre_analysis_enabled: bool = True 
        
        # --- Retry & Smart Filtering Logic State ---
        self.current_query_attempt: int = 0
        self.current_user_prompt: str = ""
        self.is_smart_filtering: bool = False
        
        # --- State Management: Tab 2 (Code Sandbox) ---
        self.sandbox_history: List[Dict[str, str]] = []
        self.current_sandbox_code: str = ""
        self.exec_worker: Optional[CodeExecutionWorker] = None 

        # --- Window Configuration ---
        self.setWindowTitle("DMC - Developer Agent")
        self.setGeometry(100, 60, 1400, 900) 
        self.setupUI()

    def setupUI(self) -> None:
        """Configures the main UI layout and applies global stylesheets."""
        self.setStyleSheet("""
            QWidget {
                background-color: #181c24;
                color: #f0f0f0;
            }
            QTextEdit, QLineEdit {
                background-color: #12151b;
                color: #e0e0e0;
                border: 1px solid #444;
                font-family: 'Fira Mono', 'Consolas', 'Courier New', monospace;
            }
            QLineEdit {
                font-size: 11pt;
                padding: 4px;
            }
            QPushButton {
                background-color: #28354a;
                color: #F2B134;
                border: 1px solid #444;
                padding: 6px 12px;
                font-weight: bold;
                font-family: 'Fira Mono', 'Consolas', 'Courier New';
            }
            QPushButton:hover {
                background-color: #484857;
            }
            QPushButton:disabled {
                background-color: #2a2a30;
                color: #777;
            }
            QLabel {
                color: #F2B134;
                font-weight: bold;
                font-size: 10pt;
                margin-top: 4px;
            }
            QGroupBox {
                border: 2px solid #28354a;
                margin-top: 0.6em;
                color: #f0f0f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 4px;
            }
            QRadioButton, QCheckBox { color: #f0f0f0; }
            QTabWidget::pane {
                border: 1px solid #28354a;
                border-top: 0px;
            }
            QTabBar::tab {
                background: #181c24;
                border: 1px solid #28354a;
                border-bottom: none;
                padding: 8px 16px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #12151b;
                border-bottom: 1px solid #12151b;
            }
        """)

        main_layout = QtWidgets.QHBoxLayout(self)

        # ==== LEFT PANEL (Configuration & Context) ====
        left_panel = self.create_left_panel()
        main_layout.addLayout(left_panel, 2)

        # ==== RIGHT PANEL (Tabs) ====
        self.tab_widget = QtWidgets.QTabWidget()
        
        # Tab 1: Project Chat
        self.project_chat_tab = QtWidgets.QWidget()
        self.project_chat_layout = QtWidgets.QVBoxLayout(self.project_chat_tab)
        self.create_project_chat_tab(self.project_chat_layout)
        self.tab_widget.addTab(self.project_chat_tab, "🤖 Project Chat")

        # Tab 2: Code Sandbox
        self.sandbox_tab = QtWidgets.QWidget()
        self.sandbox_layout = QtWidgets.QVBoxLayout(self.sandbox_tab)
        self.create_sandbox_tab(self.sandbox_layout)
        self.tab_widget.addTab(self.sandbox_tab, "🐍 Code Sandbox")

        main_layout.addWidget(self.tab_widget, 5) 

    def create_left_panel(self) -> QtWidgets.QVBoxLayout:
        """Constructs the left sidebar containing controls and context display."""
        left_panel = QtWidgets.QVBoxLayout()

        # Logo / ASCII Art
        logoLabel = QtWidgets.QLabel(self.holaibot_ascii())
        logoLabel.setFont(QtGui.QFont("Courier New", 10))
        logoLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        logoLabel.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        logoLabel.setStyleSheet("color:#F2B134; font-size:12pt;")
        left_panel.addWidget(logoLabel)
        left_panel.addSpacing(16)

        # Folder Selection Controls
        folder_btns = QtWidgets.QHBoxLayout()
        self.selectButton = QtWidgets.QPushButton("Select Project Folder")
        self.selectButton.clicked.connect(self.select_folder)
        folder_btns.addWidget(self.selectButton)
        self.reloadButton = QtWidgets.QPushButton("Reload")
        self.reloadButton.clicked.connect(self.reload_context)
        folder_btns.addWidget(self.reloadButton)
        left_panel.addLayout(folder_btns)

        # Configuration Controls
        config_btns = QtWidgets.QHBoxLayout()
        self.extButton = QtWidgets.QPushButton("Extensions")
        self.extButton.clicked.connect(self.set_extensions)
        self.excludeButton = QtWidgets.QPushButton("Exclusions")
        self.excludeButton.clicked.connect(self.set_exclusions)
        config_btns.addWidget(self.extButton)
        config_btns.addWidget(self.excludeButton)
        left_panel.addLayout(config_btns)

        # Font Controls
        font_size_layout = QtWidgets.QHBoxLayout()
        context_font_btn = QtWidgets.QPushButton("Context Font Size")
        context_font_btn.clicked.connect(self.change_context_font_size)
        conversation_font_btn = QtWidgets.QPushButton("Conversation Font Size")
        conversation_font_btn.clicked.connect(self.change_conversation_font_size)
        font_size_layout.addWidget(context_font_btn)
        font_size_layout.addWidget(conversation_font_btn)
        left_panel.addLayout(font_size_layout)
        left_panel.addSpacing(2)

        # Context Display Area
        group_ctx = QtWidgets.QGroupBox("Extracted Project Context")
        group_ctx.setFont(QtGui.QFont("Fira Mono", 10))
        ctx_layout = QtWidgets.QVBoxLayout()
        self.contextEdit = QtWidgets.QTextEdit(self)
        self.contextEdit.setFont(QtGui.QFont("Fira Mono", self.context_font_size))
        self.contextEdit.setReadOnly(True)
        context_copy_btn = QtWidgets.QPushButton("Copy Context")
        context_copy_btn.clicked.connect(self.copy_context)
        ctx_layout.addWidget(self.contextEdit)
        ctx_layout.addWidget(context_copy_btn)
        group_ctx.setLayout(ctx_layout)
        left_panel.addWidget(group_ctx, stretch=2)
        left_panel.addStretch()
        
        return left_panel

    def create_project_chat_tab(self, chat_layout: QtWidgets.QVBoxLayout) -> None:
        """Constructs the UI elements for the Project Chat tab."""
        chatbox = QtWidgets.QGroupBox("DMC Chat")
        ctx_font = QtGui.QFont("Fira Mono", self.conversation_font_size)
        
        inner_layout = QtWidgets.QVBoxLayout()

        # Options
        self.markdown_checkbox = QtWidgets.QCheckBox("Format conversation as Markdown")
        self.markdown_checkbox.setChecked(self.markdown_enabled)
        self.markdown_checkbox.stateChanged.connect(self.toggle_markdown)
        inner_layout.addWidget(self.markdown_checkbox)
        
        self.pre_analysis_checkbox = QtWidgets.QCheckBox("Enable Smart Context Filtering (Reduce Token Usage)")
        self.pre_analysis_checkbox.setChecked(self.pre_analysis_enabled)
        self.pre_analysis_checkbox.stateChanged.connect(self.toggle_pre_analysis)
        inner_layout.addWidget(self.pre_analysis_checkbox)

        # Mode Selection
        mode_box = QtWidgets.QGroupBox("Mode")
        mode_layout = QtWidgets.QHBoxLayout()
        self.mode_show_prompt = QtWidgets.QRadioButton("Show Prompt")
        self.mode_use_api = QtWidgets.QRadioButton("Use API")
        self.mode_use_api.setChecked(True) 
        mode_layout.addWidget(self.mode_show_prompt)
        mode_layout.addWidget(self.mode_use_api)
        mode_box.setLayout(mode_layout)
        inner_layout.addWidget(mode_box)

        # Response Area
        self.responseEdit = QtWidgets.QTextEdit(self)
        self.responseEdit.setReadOnly(True)
        self.responseEdit.setFont(ctx_font)
        self.responseEdit.setAcceptRichText(True)
        inner_layout.addWidget(self.responseEdit, stretch=8)

        # Prompt Input
        prompt_hbox = QtWidgets.QHBoxLayout()
        self.promptEdit = QtWidgets.QLineEdit(self)
        self.promptEdit.setFont(ctx_font)
        self.promptEdit.setPlaceholderText("Question about the project...")
        prompt_hbox.addWidget(self.promptEdit, stretch=8)
        self.askButton = QtWidgets.QPushButton("Ask")
        self.askButton.clicked.connect(self.ask_gpt)
        prompt_hbox.addWidget(self.askButton, stretch=1)
        inner_layout.addLayout(prompt_hbox)

        # Action Buttons
        btnbox = QtWidgets.QHBoxLayout()
        copy_btn = QtWidgets.QPushButton("Copy Response")
        copy_btn.clicked.connect(self.copy_response)
        export_btn = QtWidgets.QPushButton("Export Response")
        export_btn.clicked.connect(self.export_response)
        clear_btn = QtWidgets.QPushButton("Clear Chat")
        clear_btn.clicked.connect(self.clear_response)
        btnbox.addWidget(copy_btn)
        btnbox.addWidget(export_btn)
        btnbox.addWidget(clear_btn)
        inner_layout.addLayout(btnbox)

        chatbox.setLayout(inner_layout)
        chat_layout.addWidget(chatbox)

    def create_sandbox_tab(self, sandbox_layout: QtWidgets.QVBoxLayout) -> None:
        """Constructs the UI elements for the Code Sandbox tab."""
        sandbox_group = QtWidgets.QGroupBox("Agent Code Sandbox")
        layout = QtWidgets.QVBoxLayout()
        
        # Splitter for Conversation vs Code Editor
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        
        convo_widget = QtWidgets.QWidget()
        convo_layout = QtWidgets.QVBoxLayout(convo_widget)
        convo_layout.setContentsMargins(0,0,0,0)
        convo_label = QtWidgets.QLabel("Conversation with the Coding Agent:")
        self.sandboxResponseEdit = QtWidgets.QTextEdit()
        self.sandboxResponseEdit.setReadOnly(True)
        self.sandboxResponseEdit.setFont(QtGui.QFont("Fira Mono", self.conversation_font_size))
        convo_layout.addWidget(convo_label)
        convo_layout.addWidget(self.sandboxResponseEdit)
        splitter.addWidget(convo_widget)
        
        code_widget = QtWidgets.QWidget()
        code_layout = QtWidgets.QVBoxLayout(code_widget)
        code_layout.setContentsMargins(0,0,0,0)
        code_label = QtWidgets.QLabel("Code Sandbox (Editable):")
        self.sandboxCodeEdit = QtWidgets.QTextEdit()
        self.sandboxCodeEdit.setFont(QtGui.QFont("Fira Mono", 9))
        self.sandboxCodeEdit.setPlaceholderText("AI-generated code will appear here...")
        code_layout.addWidget(code_label)
        code_layout.addWidget(self.sandboxCodeEdit)
        splitter.addWidget(code_widget)
        
        splitter.setSizes([200, 300]) 
        layout.addWidget(splitter, stretch=1) 

        # Input Area
        prompt_label = QtWidgets.QLabel("Your code request:")
        layout.addWidget(prompt_label)
        self.sandboxPromptEdit = QtWidgets.QLineEdit()
        self.sandboxPromptEdit.setPlaceholderText("Ex: Write a function that sorts a list...")
        layout.addWidget(self.sandboxPromptEdit)
        
        # Action Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.sandboxAskButton = QtWidgets.QPushButton("Generate Code")
        self.sandboxAskButton.clicked.connect(self.ask_sandbox_gpt)
        self.sandboxExecuteButton = QtWidgets.QPushButton("Execute Sandbox Code")
        self.sandboxExecuteButton.clicked.connect(self.execute_current_sandbox_code)
        self.sandboxClearButton = QtWidgets.QPushButton("Clear Sandbox")
        self.sandboxClearButton.clicked.connect(self.clear_sandbox)
        
        button_layout.addWidget(self.sandboxAskButton)
        button_layout.addWidget(self.sandboxExecuteButton)
        button_layout.addWidget(self.sandboxClearButton)
        layout.addLayout(button_layout)
        
        sandbox_group.setLayout(layout)
        sandbox_layout.addWidget(sandbox_group)

    # -------------------------------------------------------------------------
    # UI Control Slots (Fonts, Toggles)
    # -------------------------------------------------------------------------
    def change_context_font_size(self) -> None:
        size, ok = QtWidgets.QInputDialog.getInt(self, "Context Font", "Font Size (context):", value=self.context_font_size, min=6, max=32)
        if ok:
            self.context_font_size = size
            self.contextEdit.setFont(QtGui.QFont("Fira Mono", self.context_font_size))

    def change_conversation_font_size(self) -> None:
        size, ok = QtWidgets.QInputDialog.getInt(self, "Conversation Font", "Font Size (chats):", value=self.conversation_font_size, min=6, max=32)
        if ok:
            self.conversation_font_size = size
            font = QtGui.QFont("Fira Mono", self.conversation_font_size)
            self.responseEdit.setFont(font)
            self.promptEdit.setFont(font)
            self.sandboxResponseEdit.setFont(font)
            self.sandboxPromptEdit.setFont(font)

    def toggle_markdown(self, state: int) -> None:
        self.markdown_enabled = bool(state)

    def toggle_pre_analysis(self, state: int) -> None:
        self.pre_analysis_enabled = bool(state)

    def holaibot_ascii(self) -> str:
        return (
            "██████╗ ███████╗██████╗ ██╗   ██╗ ██████╗    ███╗   ███╗ ██████╗\n"
            "██╔══██╗██╔════╝██╔══██╗██║   ██║██╔════╝    ████╗ ████║██╔════╝\n"
            "██║  ██║█████╗  ██████╔╝██║   ██║██║  ███╗   ██╔████╔██║██║     \n"
            "██║  ██║██╔══╝  ██╔══██╗██║   ██║██║   ██║   ██║╚██╔╝██║██║     \n"
            "██████╔╝███████╗██████╔╝╚██████╔╝╚██████╔╝   ██║ ╚═╝ ██║╚██████╗\n"
            "╚═════╝ ╚══════╝╚═════╝  ╚═════╝  ╚═════╝    ╚═╝     ╚═╝ ╚═════╝"
        )
    
    def set_buttons_enabled(self, enabled: bool) -> None:
        self.selectButton.setEnabled(enabled)
        self.reloadButton.setEnabled(enabled)
        self.extButton.setEnabled(enabled)
        self.excludeButton.setEnabled(enabled)
        self.askButton.setEnabled(enabled)

    def _display_agent_message(self, prefix: str, message: str, color: str = "#F2B134") -> None:
        msg = f'<b style="color:{color};">[{prefix}]</b> <i>{message}</i>'
        self.responseEdit.append(msg)
        QtCore.QCoreApplication.processEvents()

    # -------------------------------------------------------------------------
    # Project Context Logic (Files, Exclusions, Structure)
    # -------------------------------------------------------------------------
    def select_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Folder", os.getcwd())
        if folder:
            self.loaded_path = folder
            self.reload_context()

    def reload_context(self) -> None:
        """
        Loads the project structure. 
        Note: We intentionally only load structure initially to save resources.
        Content is loaded dynamically during the query phase if smart mode is active.
        """
        if not self.loaded_path:
            QtWidgets.QMessageBox.warning(self, "No Folder", "Please select a folder first")
            return
        self.clear_response()
        self.contextEdit.clear()
        self.set_buttons_enabled(False)

        self.contextEdit.setPlainText("Extracting project structure...")
        self._display_agent_message("System", "Extracting structure (Lazy Loading)...")
        
        try:
            # Always extract just structure first. 
            structure_only_text = self.extractor.build_context(self.loaded_path, extract_content=False)
            
            self.loaded_context = structure_only_text  # Store structure
            
            self.contextEdit.setPlainText(f"Structure Ready:\n\n{structure_only_text}")
            self._display_agent_message("System", "Project Structure Loaded. Content will be fetched on demand.", color="#8ede64")
            
            self.promptEdit.clear()
            self.chat_history = []
            self.set_buttons_enabled(True)
            
        except Exception as e:
            self.contextEdit.setPlainText(f"Error during structure extraction: {e}")
            self._display_agent_message("Error", f"Structure extraction error : {e}", color="#FF6347")
            self.set_buttons_enabled(True)

    def set_extensions(self) -> None:
        cur = ",".join(sorted(x.lstrip('.') for x in self.extractor.extensions))
        txt, ok = QtWidgets.QInputDialog.getText(self, "Set Extensions", "Extensions (comma separated):", QtWidgets.QLineEdit.EchoMode.Normal, text=cur)
        if ok:
            exts = [x.strip().lower() for x in txt.split(',') if x.strip()]
            self.extractor.set_extensions(exts)
            if self.loaded_path: self.reload_context()

    def set_exclusions(self) -> None:
        current_exclusions = self.extractor.DEFAULT_EXCLUSIONS.union(self.extractor.exclusions)
        cur = ",".join(sorted(current_exclusions))
        txt, ok = QtWidgets.QInputDialog.getText(self, "Set Exclusions", "Exclusions (comma separated):", QtWidgets.QLineEdit.EchoMode.Normal, text=cur)
        if ok:
            xs = [x.strip() for x in txt.split(',') if x.strip()]
            self.extractor.set_exclusions(xs)
            if self.loaded_path: self.reload_context()

    def copy_context(self) -> None:
        QtGui.QGuiApplication.clipboard().setText(self.contextEdit.toPlainText())
        QtWidgets.QMessageBox.information(self, "Copied", "Context copied to clipboard.")

    def build_system_prompt(self, specific_context: str) -> str:
        return f"""You are an expert coding assistant.
Project context:
#####
{specific_context}
#####
If the context above is just a structure, it means the project is too large. Do your best with just filenames.
"""

    def display_user_prompt(self, prompt: str) -> None:
        if self.markdown_enabled:
            self.responseEdit.append(f'<span style="color:#AAA;">You:</span>\n<pre style="background:#222;color:#ddd">{prompt}</pre>\n')
        else:
            self.responseEdit.append(f'You: {prompt}\n')

    def display_gpt_output(self, response: str) -> None:
        if self.markdown_enabled and MARKDOWN_AVAILABLE:
            html = markdown_to_html(response)
            styled = f"<div style='font-family:\"Fira Mono\",monospace; font-size:{self.conversation_font_size}pt;'>{html}</div>"
            self.responseEdit.append(styled)
        else:
            self.responseEdit.append(response)

    # -------------------------------------------------------------------------
    # Smart Query & Retry Logic
    # -------------------------------------------------------------------------
    def ask_gpt(self) -> None:
        """
        Entry point when the user submits a query.
        Initiates the multi-step retrieval process or simply displays the prompt in prompt-view mode.
        """
        prompt = self.promptEdit.text().strip()
        if not prompt: return
        if not self.loaded_context:
            QtWidgets.QMessageBox.warning(self, "No Project", "Please load a project context first.")
            return

        # Save prompt and state
        self.current_user_prompt = prompt
        self.chat_history.append({"role": "user", "content": prompt})
        self.display_user_prompt(prompt)
        self.responseEdit.insertPlainText('\n')
        self.promptEdit.clear()

        # Check interaction mode
        if self.mode_show_prompt.isChecked():
            self._display_agent_message("System", "Generating full prompt (Reading files)...")
            
            # 1. Force full content reading
            # This reads all code except what is defined in 'Exclusions'
            full_ctx = self.extractor.build_context(self.loaded_path, extract_content=True)
            
            # 2. Get the actual System Prompt
            system_instruction = self.build_system_prompt(full_ctx)
            
            # 3. Build final block without character limits
            final_prompt_block = (
                "### FINAL PROMPT (FULL CONTENT) ###\n\n"
                "--- [PART 1: SYSTEM INSTRUCTION & CONTEXT] ---\n"
                f"{system_instruction}\n\n"
                "--- [PART 2: USER REQUEST] ---\n"
                f"User: {prompt}\n"
            )
            
            # 4. Display result and stop
            self.display_gpt_output(final_prompt_block)
            return

        self.askButton.setEnabled(False)
        
        # Initialize Retry Logic Sequence
        self.current_query_attempt = 1
        self.execute_smart_query_step()

    def execute_smart_query_step(self) -> None:
        """
        Determines the retrieval strategy based on the current attempt count.
        Handles fallback from Smart Filter -> Aggressive Filter -> Structure Only.
        """
        
        # ATTEMPT 1: Standard Smart Filter
        if self.current_query_attempt == 1:
            self._display_agent_message(f"Brain", "Analyzing query to select relevant files...")
            self.run_mini_filter(aggressive=False)
            
        # ATTEMPT 2: Aggressive Filter (Triggered after a 429)
        elif self.current_query_attempt == 2:
            self._display_agent_message(f"Brain (Attempt {self.current_query_attempt})", "Previous context too large. Switching to aggressive filtering...", color="#FFA500")
            self.run_mini_filter(aggressive=True)
            
        # ATTEMPT 3: Structure Only (Last Resort)
        elif self.current_query_attempt == 3:
            self._display_agent_message(f"Brain (Attempt {self.current_query_attempt})", "Still failing. Sending structure ONLY (No file content).", color="#FF6347")
            # Skip Brain, go straight to Worker with Structure Only
            self.send_to_worker(context_content=self.loaded_context) 
            
        # FAILED
        else:
            self._display_agent_message("System", "Error: Project is too voluminous. Even structure-only failed or max retries reached.", color="#FF0000")
            self.askButton.setEnabled(True)

    def run_mini_filter(self, aggressive: bool = False) -> None:
        """
        Uses a smaller, faster model (the 'Brain') to identify relevant files.
        """
        self.is_smart_filtering = True
        
        if aggressive:
            instruction = "Select ONLY the top 5 absolute most critical files needed to answer. Be extremely strict."
        else:
            instruction = "Select all files that might be relevant to the user request."

        brain_prompt = f"""
You are the Context Optimizer. 
Project Structure:
{self.loaded_context}

User Request: "{self.current_user_prompt}"

Task: {instruction}
Return a JSON list of file paths (strings) relative to root. Example: ["src/main.py", "utils.py"]
Do not write markdown, just the JSON array.
"""
        messages = [{"role": "user", "content": brain_prompt}]
        self.gpt_worker = GptWorker(messages, model_name="gpt-5-mini")
        self.gpt_worker.finished.connect(self.on_filter_response)
        self.gpt_worker.start()

    def on_filter_response(self, response: str) -> None:
        """Processes the file list returned by the 'Brain' model."""
        self.gpt_worker = None 
        
        # Parse JSON
        relevant_files: List[str] = []
        try:
            # Cleanup code blocks if present
            clean_resp = response.strip()
            if "```" in clean_resp:
                match = re.search(r'\[.*\]', clean_resp, re.DOTALL)
                if match:
                    clean_resp = match.group(0)
            
            relevant_files = json.loads(clean_resp)
            if not isinstance(relevant_files, list): raise ValueError("Not a list")
        except Exception as e:
            self._display_agent_message("Brain (Error)", f"Failed to parse file list: {e}. Using structure only fallback.")
            # If parsing fails, jump to Attempt 3 logic immediately
            self.send_to_worker(context_content=self.loaded_context)
            return

        # Build Custom Context
        self._display_agent_message("Brain", f"Selected {len(relevant_files)} files: {', '.join(relevant_files[:3])}...", color="#87CEEB")
        
        try:
            custom_context = self.extractor.build_targeted_context(self.loaded_path, relevant_files)
            self.send_to_worker(context_content=custom_context)
        except Exception as e:
            self._display_agent_message("System", f"Error building context: {e}", color="#FF0000")
            self.askButton.setEnabled(True)

    def send_to_worker(self, context_content: str) -> None:
        """Final step: Sends the constructed context and user prompt to the main LLM."""
        self.is_smart_filtering = False 
        
        system_prompt = self.build_system_prompt(context_content)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.chat_history)

        self._display_agent_message("Worker (GPT-5.1)", "Transmitting request...", color="#8ede64")
        
        self.gpt_worker = GptWorker(messages, model_name="gpt-5.1") 
        self.gpt_worker.finished.connect(self.on_gpt_response)
        self.gpt_worker.start()

    def on_gpt_response(self, response: str) -> None:
        """Handles the final API response or triggers retry on 429 errors."""
        self.gpt_worker = None
        
        # --- RETRY LOGIC CHECK ---
        if "API Error (429)" in response:
            self._display_agent_message("System", "Rate Limit (429) exceeded.", color="#FF6347")
            # Increment attempt counter and recurse
            self.current_query_attempt += 1
            self.execute_smart_query_step()
            return
            
        # --- SUCCESS ---
        self.askButton.setEnabled(True)
        self._display_agent_message("Worker (GPT-5.1)", "Response received.", color="#87CEEB")
        self.chat_history.append({"role": "assistant", "content": response})
        
        if self.markdown_enabled and MARKDOWN_AVAILABLE:
             self.responseEdit.append("<b style='color:#87CEEB'>Worker (GPT-5.1):</b>")
        else:
             self.responseEdit.append("\n--- Worker (GPT-5.1) says: ---\n")
        
        self.display_gpt_output(response)

    def copy_response(self) -> None:
        QtGui.QGuiApplication.clipboard().setText(self.responseEdit.toPlainText())
        QtWidgets.QMessageBox.information(self, "Copied", "Chat response copied.")

    def export_response(self) -> None:
        txt = self.responseEdit.toPlainText()
        if not txt.strip(): return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export response", "chat_response.txt", "Text Files (*.txt)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f: f.write(txt)

    def clear_response(self) -> None:
        self.responseEdit.clear()
        self.promptEdit.clear()
        self.chat_history = []

    # -------------------------------------------------------------------------
    # Code Sandbox Logic
    # -------------------------------------------------------------------------
    def clear_sandbox(self) -> None:
        """Clears history and editors of the sandbox."""
        self.sandboxResponseEdit.clear()
        self.sandboxCodeEdit.clear()
        self.sandboxPromptEdit.clear()
        self.sandbox_history = []
        self.current_sandbox_code = ""
        self.sandboxResponseEdit.append("<i>Sandbox cleared. Ready for a new task.</i>")

    def ask_sandbox_gpt(self) -> None:
        """Step 1: User asks for code (With Dynamic Context Injection)."""
        prompt = self.sandboxPromptEdit.text().strip()
        if not prompt:
            QtWidgets.QMessageBox.warning(self, "Empty Prompt", "Please enter a code request.")
            return

        # UI Display (Short prompt only)
        self.sandboxResponseEdit.append(f"<b style='color:#AAA;'>You:</b> {prompt}\n")
        self.sandboxPromptEdit.clear()
        
        # Initialize system history if this is the first request
        if not self.sandbox_history:
            self.sandbox_history.append({
                "role": "system",
                "content": "You are a Python coding assistant. Provide a brief explanation, "
                        "then the complete Python code in a single block ```python ... ```. "
                        "Only include executable code."
            })
        
        # 1. Retrieve Dynamic Context (Project + Current Sandbox Code)
        project_context_str = self.loaded_context 
        current_sandbox_code_str = self.sandboxCodeEdit.toPlainText()
        
        full_context_injection = ""
        if project_context_str.strip():
            full_context_injection += f"--- PROJECT CONTEXT (FILES AND STRUCTURE) ---\n{project_context_str}\n\n"
        
        if current_sandbox_code_str.strip():
            full_context_injection += f"--- CURRENT SANDBOX CODE (TO MODIFY OR USE) ---\n{current_sandbox_code_str}\n\n"
            
        # 2. Build final message for API (Invisible in chat)
        final_prompt_content = f"{full_context_injection}--- USER REQUEST ---\n{prompt}"

        # 3. Create temporary message list for sending
        messages_for_api = list(self.sandbox_history) 
        messages_for_api.append({"role": "user", "content": final_prompt_content})

        # 4. Update PERSISTENT history
        self.sandbox_history.append({"role": "user", "content": prompt})
        
        self.sandboxResponseEdit.append("<i>[Agent] Generating code... (Calling GPT-5T with Context)</i>\n")
        self.sandboxAskButton.setEnabled(False)
        self.sandboxExecuteButton.setEnabled(False)
        
        self.gpt_worker = GptWorker(messages_for_api, model_name="gpt-5-mini")
        self.gpt_worker.finished.connect(self.on_sandbox_gpt_response)
        self.gpt_worker.start()

    def on_sandbox_gpt_response(self, response: str) -> None:
        """Step 2: AI returns the code."""
        self.gpt_worker = None
        self.sandboxAskButton.setEnabled(True)
        self.sandboxExecuteButton.setEnabled(True)
        
        self.sandbox_history.append({"role": "assistant", "content": response})

        # Parse response to separate explanation from code
        code_block_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        
        if code_block_match:
            self.current_sandbox_code = code_block_match.group(1).strip()
            explanation = re.sub(r'```python\n(.*?)\n```', '[Code block below]', response, flags=re.DOTALL).strip()
            
            self.sandboxResponseEdit.append(f"<b style='color:#87CEEB;'>Agent:</b> {explanation}\n")
            self.sandboxCodeEdit.setPlainText(self.current_sandbox_code)
            
            reply = QtWidgets.QMessageBox.question(
                self, 
                "Execution Permission", 
                "The Agent has generated code. Do you want to execute it in the sandbox?\n\n"
                "WARNING: Never execute untrusted code.",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.execute_current_sandbox_code()
            else:
                self.sandboxResponseEdit.append("<i>[User] Execution cancelled.</i>\n")
                
        else:
            self.sandboxResponseEdit.append(f"<b style='color:#87CEEB;'>Agent:</b> {response}\n")
            self.current_sandbox_code = ""
            self.sandboxCodeEdit.clear()

    def execute_current_sandbox_code(self) -> None:
        """Step 3: Execute code (if user clicks or grants permission)."""
        code_to_run = self.sandboxCodeEdit.toPlainText().strip()
        if not code_to_run:
            self.sandboxResponseEdit.append("<i>[System] No code in sandbox to execute.</i>\n")
            return
            
        self.current_sandbox_code = code_to_run 
        
        self.sandboxResponseEdit.append(f"<i>[System] Executing code...</i>\n")
        self.sandboxAskButton.setEnabled(False)
        self.sandboxExecuteButton.setEnabled(False)
        
        self.exec_worker = CodeExecutionWorker(self.current_sandbox_code)
        self.exec_worker.finished.connect(self.on_sandbox_execution_finished)
        self.exec_worker.start()

    def on_sandbox_execution_finished(self, stdout: str, stderr: str) -> None:
        """Step 4: Execution finished, check for errors."""
        self.exec_worker = None
        self.sandboxAskButton.setEnabled(True)
        self.sandboxExecuteButton.setEnabled(True)

        if stdout:
            self.sandboxResponseEdit.append(f"<b>Output (stdout):</b>\n<pre>{stdout}</pre>\n")
        
        if stderr:
            self.sandboxResponseEdit.append(f"<b>Error (stderr):</b>\n<pre style='color:red;'>{stderr}</pre>\n")
            
            reply = QtWidgets.QMessageBox.question(
                self,
                "Debugging Permission",
                "Execution failed. Do you want the Agent to attempt to fix the error?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.debug_sandbox_code(stderr)
            else:
                self.sandboxResponseEdit.append("<i>[User] Debugging cancelled.</i>\n")
        else:
            self.sandboxResponseEdit.append("<i>[System] Execution finished successfully.</i>\n")

    def debug_sandbox_code(self, stderr: str) -> None:
        """Step 5: AI attempts to debug (if permission granted)."""
        self.sandboxResponseEdit.append("<i>[Agent] Analyzing error for debugging... (Calling GPT-5T)</i>\n")
        
        debug_prompt = f"""
The previous code failed with the following error:
--- ERROR ---
{stderr}
--- FAILED CODE ---
{self.current_sandbox_code}
---

Please analyze the initial request, the failed code, and the error.
Provide an explanation of the fix, then the complete corrected Python code in a new block ```python ... ```.
"""
        self.sandbox_history.append({"role": "user", "content": debug_prompt})
        
        self.sandboxAskButton.setEnabled(False)
        self.sandboxExecuteButton.setEnabled(False)
        
        self.gpt_worker = GptWorker(self.sandbox_history, model_name="gpt-5-mini")
        self.gpt_worker.finished.connect(self.on_sandbox_gpt_response) 
        self.gpt_worker.start()


# -----------------------------------------------------------------------------
# Application Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Initializes and launches the PyQt application."""
    if getattr(sys, 'frozen', False):
        script_dir = Path(sys.executable).parent
    elif '__file__' in locals():
        script_dir = Path(__file__).parent.resolve()
    else:
        script_dir = Path.cwd()

    # Optional: Load an icon if it exists
    icon_path = script_dir / "erreur.png"
    app = QtWidgets.QApplication(sys.argv)
    if icon_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))

    win = HolaIbotApp()
    if icon_path.exists():
        win.setWindowIcon(QtGui.QIcon(str(icon_path)))
        
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()