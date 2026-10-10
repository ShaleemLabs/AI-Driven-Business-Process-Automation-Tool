# AI-Driven Business Process Automation Tool

A lightweight Python desktop application that transforms unstructured business text into organized, actionable information. It analyzes business notes, categorizes requests, generates concise summaries, extracts action items, suggests responsible teams, and maintains a searchable processing history through a local SQLite database.

The application uses a locally running AI model through Ollama when available and automatically falls back to rule-based analysis when AI processing fails.

## Features

- **AI-powered text analysis:** Summarizes business notes and identifies actionable tasks using a local Ollama model.
- **Automatic categorization:** Classifies input into Customer Support, Sales, Operations, Finance, HR, IT, Product, or General.
- **Action item extraction:** Identifies tasks and assigns suggested owners, priorities, and due dates when available.
- **Intelligent routing suggestions:** Recommends the team or role best suited to handle each request.
- **Rule-based fallback:** Continues processing text when Ollama is unavailable, without requiring a cloud AI service.
- **Persistent local history:** Stores processing results in an SQLite database.
- **CSV export:** Exports the complete processing history for reporting and further analysis.
- **Desktop GUI:** Provides a Tkinter interface with dedicated analysis and history tabs.
- **Background processing:** Uses a separate thread for analysis to keep the interface responsive.

## Technologies Used

- **Python 3.10+** — Core application logic
- **Tkinter / ttk** — Desktop graphical user interface
- **Ollama** — Local AI inference and structured text analysis
- **SQLite** — Persistent storage of processed business records
- **CSV** — Data export and reporting
- **JSON** — Structured AI responses and task storage
- **Threading** — Background analysis
- **urllib** — Communication with the local Ollama API

## Requirements

- Python 3.10 or later
- Ollama installed and running locally for AI-powered analysis
- A compatible Ollama model downloaded locally

The default model is `llama3.2`.

**Note:** Ollama is optional. The application includes a rule-based fallback that allows it to process business text without a running AI model.

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd <your-repository-folder>
```

Replace the placeholders with your GitHub repository URL and folder name.

### 2. (Optional) Set up Ollama

Download Ollama from:

https://ollama.com/download

Pull the default model:

```bash
ollama pull llama3.2
```

Ensure Ollama is running locally. The application communicates with its chat API at:

```text
http://localhost:11434/api/chat
```

You can also enter a different locally available Ollama model in the application.

### 3. Run the application

Run the Python script from your terminal:

```bash
python business_automation.py
```

No additional Python packages are required for the current implementation because it uses Python's standard library.

## How to Use

1. **Enter business text.** Paste meeting notes, customer feedback, internal requests, or other unstructured business information into the input area.
2. **Configure the model.** Use the default `llama3.2` model or enter another Ollama model name.
3. **Analyze the text.** Click **Analyze & Route** to generate a summary, category, suggested destination team, and action items.
4. **Review the results.** Open the Analysis tab to inspect the summary and extracted tasks, including their suggested owners, priorities, and due dates.
5. **View processing history.** Open the History tab to review previous analyses.
6. **Export records.** Click **Export History to CSV** to save the stored processing history to a CSV file.
7. **Start another analysis.** Click **Clear** to remove the current input and enter new business text.

## Example

### Input

> Customer says their order arrived damaged and requests a refund. Please contact the customer today and ask Operations to investigate the packaging.

### Example output

- **Category:** Customer Support
- **Route to:** Customer Support
- **Summary:** A customer reports receiving a damaged order and requests a refund. The customer needs to be contacted, and Operations should investigate the packaging.
- **Suggested action items:**
  - Contact the customer regarding the damaged order.
  - Review the refund request.
  - Investigate the packaging issue.

The AI model determines the actual output. Task owners, priorities, and dates are suggestions that should be reviewed before work is assigned.

## Data Storage

The application automatically creates a local SQLite database named:

```text
business_automation.db
```

The database stores the following information for each processed item:

| Field | Description |
|---|---|
| ID | Unique record identifier |
| Created At | Date and time of processing |
| Source Text | Original business text |
| Category | Assigned business category |
| Summary | Generated summary |
| Tasks | Extracted tasks stored as JSON |
| Route To | Suggested destination team |
| Method | AI model or fallback method used |

Processing history is stored locally in the application's working directory. The database is initialized automatically when the application starts.

## CSV Export

The exported CSV contains all stored processing records, including the original input, generated summary, task data, category, suggested destination, and processing method.

The file is saved using UTF-8 with a byte-order mark (BOM) to improve compatibility with spreadsheet applications such as Microsoft Excel.

## Privacy and Limitations

- AI analysis uses the locally running Ollama service rather than a cloud AI API.
- The rule-based fallback can categorize text and identify likely action statements without AI, but its results are less sophisticated.
- Suggested task assignments, priorities, and due dates are not guaranteed to be correct.
- The application stores original business text and analysis results in a local database. Avoid entering confidential information unless your organization's data-handling policies permit it.
- The application does not automatically send emails, assign tasks in external platforms, or execute business workflows. It generates recommendations for human review.

## Project Purpose

This project explores how local AI and lightweight automation can help organize unstructured business information into structured, actionable workflows. It combines desktop application development, natural language processing, rule-based logic, database management, and data export in a practical business tool.

## License

No license has been specified yet. Unless a license is added to this repository, the project should be treated as having all rights reserved by its author.
