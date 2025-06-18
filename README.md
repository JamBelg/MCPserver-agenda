# 🩺 Medical Agenda Manager with LLM and PostgreSQL

This project combines the power of Large Language Models (LLMs) with a PostgreSQL database to manage a medical appointment agenda through natural language interactions. It leverages [FastMCP](https://github.com/multion-org/mcp), an LLM tool interface, to provide a flexible, type-safe, and extensible way to read and create appointments using simple, conversational commands.

## 📌 Features

- Read and filter agenda entries using LLM input
- Create new medical appointments through natural language
- Filter appointments by treatment type (e.g., mane or number)
- PostgreSQL backend for robust and structured data handling
- Lifespan context management for clean startup/shutdown
- CLI-friendly with optional local or network-based deployment

## 🚀 Quick Start

### 1. Project Setup

```bash
mkdir myproject
cd myproject

uv venv
source .venv/bin/activate  # For Linux/Mac

uv pip install "mcp[cli]" asyncpg psycopg2 psycopg2-binary dotenv
touch postgres.py
```


### 2. Configure Environment Variables

Create a .env file in your root directory with your PostgreSQL settings:

PG_HOST=localhost
PG_PORT=5432
PG_USER=your_user
PG_PASSWORD=your_password
PG_DATABASE=your_db

### 3. Application Lifecycle Management

The app uses an async context manager to handle database connections safely:

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manage application lifecycle with type-safe context"""
    ...

### 4. Start the MCP Server

mcp = FastMCP("appointments", lifespan=app_lifespan)

The server can be tested using localhost during development. To enable external access, consider deploying it to a non-localhost network.
🔐 Data Security

Be mindful of data privacy when working with LLMs. For sensitive information such as patient names, addresses, or phone numbers, implement encoding or anonymization techniques to ensure data protection.
💡 Use Case Example

You can instruct the LLM to:

    "Show me all mane treatments for a date / week"

    "Book a new appointment for John Doe on June 21 at 10 AM"

The tool will parse the input and interact with the database to retrieve or modify appointment data accordingly.

## 🧪 Free LLM Access
At the time of writing, only Claude 4 Sonnet is available for free use, which you can experiment with via platforms like claude.ai.

## 📄 License
MIT License
