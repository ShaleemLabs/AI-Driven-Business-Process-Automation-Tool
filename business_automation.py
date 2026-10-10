"""
AI-Driven Business Process Automation Tool
-----------------------------------------
A lightweight Tkinter desktop app that:
- Accepts unstructured business text
- Summarizes it, categorizes it, and extracts actionable tasks
- Uses a local Ollama model when available, with a rule-based fallback
- Logs every result to SQLite
- Exports the log to CSV

Requirements:
  Python 3.10+
  Optional: Ollama installed and running locally, with a model pulled
             (for example: ollama pull llama3.2)

Run:
  python business_automation.py
"""

import csv
import json
import sqlite3
import threading
import urllib.error
import urllib.request
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Business Process Automation"
DB_FILE = "business_automation.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2"


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source_text TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT NOT NULL,
                tasks_json TEXT NOT NULL,
                route_to TEXT NOT NULL,
                method TEXT NOT NULL
            )
        """)
        conn.commit()


def save_record(source_text, category, summary, tasks, route_to, method):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO processed_items
            (created_at, source_text, category, summary, tasks_json, route_to, method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            source_text,
            category,
            summary,
            json.dumps(tasks, ensure_ascii=False),
            route_to,
            method
        ))
        conn.commit()


def get_history(limit=100):
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute("""
            SELECT id, created_at, category, summary, route_to, method
            FROM processed_items
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()


def export_csv(path):
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute("""
            SELECT id, created_at, source_text, category, summary,
                   tasks_json, route_to, method
            FROM processed_items ORDER BY id DESC
        """).fetchall()

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ID", "Created At", "Source Text", "Category", "Summary",
            "Tasks (JSON)", "Route To", "Method"
        ])
        writer.writerows(rows)


def call_ollama(text, model):
    prompt = f"""
You are a business workflow assistant. Analyze the input below.
Return ONLY valid JSON with this exact structure:
{{
  "category": "one of: Customer Support, Sales, Operations, Finance, HR, IT, Product, General",
  "summary": "a concise 1-3 sentence summary",
  "tasks": [
    {{"task": "clear action", "owner": "suggested team or role", "priority": "High|Medium|Low", "due_date": "date or Not specified"}}
  ],
  "route_to": "the team or role that should handle this"
}}
Extract concrete tasks only. If no action is needed, return an empty tasks array.
Do not invent dates, names, or facts.

INPUT:
{text}
"""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Return valid JSON only. Do not use markdown fences."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "format": "json"
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))

    content = data.get("message", {}).get("content", "")
    result = json.loads(content)
    return normalize_result(result), f"Ollama ({model})"


def normalize_result(result):
    categories = {
        "customer support", "sales", "operations", "finance", "hr",
        "it", "product", "general"
    }
    category = str(result.get("category", "General")).strip()
    if category.lower() not in categories:
        category = "General"

    summary = str(result.get("summary", "")).strip() or "No summary provided."
    route_to = str(result.get("route_to", "General")).strip() or "General"

    tasks = result.get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []

    clean_tasks = []
    for item in tasks:
        if isinstance(item, str):
            item = {"task": item}
        if not isinstance(item, dict):
            continue
        task = str(item.get("task", "")).strip()
        if not task:
            continue
        priority = str(item.get("priority", "Medium")).title()
        if priority not in {"High", "Medium", "Low"}:
            priority = "Medium"
        clean_tasks.append({
            "task": task,
            "owner": str(item.get("owner", route_to)).strip() or route_to,
            "priority": priority,
            "due_date": str(item.get("due_date", "Not specified")).strip()
        })

    return {
        "category": category,
        "summary": summary,
        "tasks": clean_tasks,
        "route_to": route_to
    }


def rule_based_analyze(text):
    """A no-API fallback so the app remains usable without Ollama."""
    lower = text.lower()

    keyword_groups = {
        "Customer Support": ["complaint", "customer", "refund", "support", "broken", "issue", "ticket"],
        "Sales": ["lead", "prospect", "quote", "pricing", "sales", "purchase"],
        "Finance": ["invoice", "payment", "budget", "expense", "billing", "refund"],
        "HR": ["employee", "hiring", "interview", "leave", "onboarding", "payroll"],
        "IT": ["password", "laptop", "software", "access", "network", "bug", "system"],
        "Product": ["feature", "roadmap", "design", "product", "feedback"],
        "Operations": ["shipment", "schedule", "process", "vendor", "delivery", "inventory"]
    }

    scores = {
        category: sum(1 for word in words if word in lower)
        for category, words in keyword_groups.items()
    }
    category = max(scores, key=scores.get) if max(scores.values(), default=0) else "General"
    route_to = {
        "Customer Support": "Customer Support",
        "Sales": "Sales",
        "Finance": "Finance",
        "HR": "Human Resources",
        "IT": "IT",
        "Product": "Product Team",
        "Operations": "Operations"
    }.get(category, "General / Review")

    # Split into sentence-like chunks and identify likely action statements.
    chunks = []
    for part in text.replace("\n", ". ").replace(";", ".").split("."):
        part = " ".join(part.split()).strip(" -•\t")
        if part:
            chunks.append(part)

    action_words = (
        "please", "need to", "needs to", "must", "should", "follow up",
        "send", "call", "email", "review", "create", "update", "fix",
        "schedule", "prepare", "confirm", "investigate", "assign",
        "contact", "refund", "sub mit", "check", "resolve"
    )
    tasks = []
    for chunk in chunks:
        if any(word in chunk.lower() for word in action_words):
            tasks.append({
                "task": chunk,
                "owner": route_to,
                "priority": "Medium",
                "due_date": "Not specified"
            })

    summary = " ".join(chunks[:2])
    if len(summary) > 360:
        summary = summary[:357].rsplit(" ", 1)[0] + "..."
    if not summary:
        summary = "No text was provided."

    return {
        "category": category,
        "summary": summary,
        "tasks": tasks,
        "route_to": route_to
    }, "Rule-based fallback"


class BusinessAutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1000x760")
        self.root.minsize(780, 600)
        self.current_result = None

        self._configure_style()
        self._build_ui()
        self.refresh_history()

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="Business Process Automation", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Turn unstructured notes into categorized, actionable work.",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 12))

        settings = ttk.Frame(outer)
        settings.pack(fill="x", pady=(0, 8))
        ttk.Label(settings, text="Ollama model:").pack(side="left")
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        ttk.Entry(settings, textvariable=self.model_var, width=20).pack(side="left", padx=(6, 14))
        ttk.Label(settings, text="If Ollama is unavailable, the app uses a basic rule-based fallback.").pack(side="left")

        ttk.Label(outer, text="Paste meeting notes, customer feedback, or a request:", style="Section.TLabel").pack(anchor="w")
        self.input_text = tk.Text(outer, height=8, wrap="word", font=("Segoe UI", 10), undo=True)
        self.input_text.pack(fill="x", pady=(6, 8))
        self.input_text.insert(
            "1.0",
            "Customer says their order arrived damaged and requests a refund. "
            "Please contact the customer today and ask Operations to investigate the packaging."
        )

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 10))
        self.process_button = ttk.Button(
            controls, text="Analyze & Route", style="Accent.TButton", command=self.process_text
        )
        self.process_button.pack(side="left")
        ttk.Button(controls, text="Clear", command=self.clear_input).pack(side="left", padx=6)
        ttk.Button(controls, text="Export History to CSV", command=self.export_history).pack(side="right")

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w", pady=(0, 6))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        results_tab = ttk.Frame(self.notebook, padding=10)
        history_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(results_tab, text="Analysis")
        self.notebook.add(history_tab, text="History")

        self.category_var = tk.StringVar(value="—")
        self.route_var = tk.StringVar(value="—")
        self.method_var = tk.StringVar(value="—")

        meta = ttk.Frame(results_tab)
        meta.pack(fill="x")
        for label, variable in (
            ("Category", self.category_var),
            ("Route to", self.route_var),
            ("Method", self.method_var)
        ):
            group = ttk.Frame(meta)
            group.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ttk.Label(group, text=label, style="Section.TLabel").pack(anchor="w")
            ttk.Label(group, textvariable=variable, wraplength=250).pack(anchor="w", pady=(3, 8))

        ttk.Label(results_tab, text="Summary", style="Section.TLabel").pack(anchor="w")
        self.summary_text = tk.Text(results_tab, height=4, wrap="word", font=("Segoe UI", 10), state="disabled")
        self.summary_text.pack(fill="x", pady=(4, 10))

        ttk.Label(results_tab, text="Action items", style="Section.TLabel").pack(anchor="w")
        columns = ("task", "owner", "priority", "due")
        self.tasks_tree = ttk.Treeview(results_tab, columns=columns, show="headings", height=7)
        self.tasks_tree.heading("task", text="Task")
        self.tasks_tree.heading("owner", text="Suggested owner")
        self.tasks_tree.heading("priority", text="Priority")
        self.tasks_tree.heading("due", text="Due date")
        self.tasks_tree.column("task", width=420, minwidth=180)
        self.tasks_tree.column("owner", width=150, minwidth=100)
        self.tasks_tree.column("priority", width=80, anchor="center")
        self.tasks_tree.column("due", width=110)
        self.tasks_tree.pack(fill="both", expand=True)

        history_columns = ("id", "created", "category", "summary", "route", "method")
        self.history_tree = ttk.Treeview(history_tab, columns=history_columns, show="headings", height=15)
        headings = {
            "id": ("ID", 45), "created": ("Created", 145),
            "category": ("Category", 110), "summary": ("Summary", 330),
            "route": ("Route to", 130), "method": ("Method", 130)
        }
        for col, (heading, width) in headings.items():
            self.history_tree.heading(col, text=heading)
            self.history_tree.column(col, width=width, minwidth=60)
        self.history_tree.pack(fill="both", expand=True)
        ttk.Button(history_tab, text="Refresh History", command=self.refresh_history).pack(anchor="e", pady=(8, 0))

    def clear_input(self):
        self.input_text.delete("1.0", "end")

    def process_text(self):
        source_text = self.input_text.get("1.0", "end").strip()
        if not source_text:
            messagebox.showwarning("Nothing to analyze", "Paste some business text first.")
            return

        self.process_button.configure(state="disabled")
        self.status_var.set("Analyzing…")
        model = self.model_var.get().strip() or DEFAULT_MODEL
        threading.Thread(
            target=self._analyze_worker,
            args=(source_text, model),
            daemon=True
        ).start()

    def _analyze_worker(self, source_text, model):
        try:
            result, method = call_ollama(source_text, model)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            result, method = rule_based_analyze(source_text)
            method += f" (Ollama unavailable: {type(exc).__name__})"
        except Exception as exc:
            result, method = rule_based_analyze(source_text)
            method += f" (fallback: {type(exc).__name__})"

        try:
            save_record(
                source_text,
                result["category"],
                result["summary"],
                result["tasks"],
                result["route_to"],
                method
            )
        except sqlite3.Error as exc:
            self.root.after(0, lambda: messagebox.showerror("Database error", str(exc)))

        self.root.after(0, lambda: self._show_result(result, method))

    def _show_result(self, result, method):
        self.current_result = result
        self.category_var.set(result["category"])
        self.route_var.set(result["route_to"])
        self.method_var.set(method)

        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", result["summary"])
        self.summary_text.configure(state="disabled")

        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
        for task in result["tasks"]:
            self.tasks_tree.insert("", "end", values=(
                task["task"], task["owner"], task["priority"], task["due_date"]
            ))

        if not result["tasks"]:
            self.tasks_tree.insert("", "end", values=("No action items detected", "—", "—", "—"))

        self.status_var.set("Analysis complete. Result saved to local history.")
        self.process_button.configure(state="normal")
        self.refresh_history()
        self.notebook.select(0)

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for row in get_history():
            row = list(row)
            row[3] = row[3][:180] + ("…" if len(row[3]) > 180 else "")
            self.history_tree.insert("", "end", values=row)

    def export_history(self):
        path = filedialog.asksaveasfilename(
            title="Export processing history",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            export_csv(path)
            messagebox.showinfo("Export complete", f"History exported to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))


def main():
    init_db()
    root = tk.Tk()
    BusinessAutomationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
