# OpsPilot

**Autonomous LLM-powered agent for ops automation with explicit state machine control**

OpsPilot is an intelligent operations agent that investigates incidents, analyzes metrics, searches logs, and creates tickets - all while maintaining full transparency through an explicit finite state machine and approval workflows.

---

## Features

- **Autonomous Investigation**: Agent autonomously investigates issues using available tools
- **Explicit State Machine**: Plan → Execute → Evaluate loop with full transparency
- **Approval Workflows**: High-risk actions (like ticket creation) require human approval
- **Real-time Monitoring**: Live dashboard shows agent reasoning and progress
- **Tool Integration**: Extensible tool system (logs, metrics, ticketing, reports)
- **Production-Ready**: Docker Compose setup with Redis, SQLite, and hot reload

---

### **Model Context Protocol (MCP) Integration**

OpsPilot uses the [Model Context Protocol](https://modelcontextprotocol.io) for standardized tool discovery and execution:

- **7 Tools via MCP**: Operations tools (log search, metrics, tickets, reports) + filesystem tools (read, write, list)
- **Dynamic Tool Discovery**: Agent discovers available tools at runtime via MCP protocol
- **MCP Aggregator**: Node.js server combines multiple tool sources (ops + filesystem)
- **Standardized Interface**: Tools exposed via JSON-RPC 2.0 over stdio
- **Interoperability**: External Claude instances can connect to OpsPilot's MCP server

**MCP Architecture:**
```
Agent (Python) ←─ stdio ─→ MCP Aggregator (Node.js) ─┬─→ OpsPilot Tools (Python)
                                                       └─→ Filesystem Tools (Node.js)
```
---

## Architecture
```
┌─────────────┐
│   Frontend  │ ← Next.js dashboard with real-time updates
│  (Next.js)  │
└──────┬──────┘
       │ HTTP/REST
┌──────▼──────┐
│   Backend   │ ← FastAPI server managing runs and agent lifecycle
│  (FastAPI)  │
└──────┬──────┘
       │
┌──────▼──────┐
│    Agent    │ ← Autonomous agent with explicit state machine
│  (Python)   │   States: PLAN → EXECUTE_TOOL → EVALUATE
└──────┬──────┘
       │
       ├─→ Redis (retry logic, state management)
       ├─→ SQLite (run history, audit trail)
       └─→ Anthropic Claude API (LLM reasoning)
```

### State Machine
```
PLAN ──────→ EXECUTE_TOOL ──────→ EVALUATE
  ↑              │                    │
  │              │                    │
  │              ▼                    │
  │      NEEDS_APPROVAL               │
  │              │                    │
  └──────────────┴────────────────────┘
                 │
                 ▼
              DONE/FAILED
```

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Anthropic API key ([get one here](https://console.anthropic.com/))

### Setup

1. **Clone the repository:**
```bash
   git clone https://github.com/yourusername/opspilot.git
   cd opspilot
```

2. **Set up environment variables:**
```bash
   echo "ANTHROPIC_API_KEY=your_key_here" > agent_service/.env
```

3. **Start all services:**
```bash
   docker-compose -f docker/docker-compose.yml up
```

4. **Access the application:**
   - **Frontend Dashboard:** http://localhost:3000
   - API Documentation: http://localhost:8000/docs

### Stop Services
```bash
docker-compose -f docker/docker-compose.yml down
```

### Troubleshooting

**If containers aren't starting or changes aren't reflecting:**
```bash
# Hard restart (fixes most issues)
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml build --no-cache
docker-compose -f docker/docker-compose.yml up
```

**If MCP tools aren't working:**
```bash
# Verify MCP server files exist
docker-compose -f docker/docker-compose.yml exec agent ls -la /app/mcp-server/

# Check MCP initialization
docker-compose -f docker/docker-compose.yml logs agent | grep "MCP initialized"
```

**Common Issues:**
- **Port conflicts**: Make sure ports 3000 and 8000 aren't in use
- **Volume mounts**: Changes to Python/Node files may require a rebuild
- **Database reset**: Remove `RUN python init_db.py` from Dockerfile if you want to preserve data between rebuilds
```

---

**Update "Project Structure" to include MCP:**
```
opspilot/
├── agent_service/          # Backend API and agent
│   ├── agent.py           # Core agent with state machine
│   ├── main.py            # FastAPI server
│   ├── models.py          # SQLAlchemy models
│   ├── state_machine.py   # State definitions
│   ├── database.py        # Database configuration
│   ├── tools/             # Tool implementations
│   │   ├── __init__.py    # Tool registry
│   │   ├── search_logs.py
│   │   ├── query_metrics.py
│   │   ├── create_ticket.py
│   │   └── generate_report.py
│   ├── init_db.py         # Database initialization
│   └── requirements.txt
├── mcp-server/            # MCP server (Node.js)
│   ├── aggregator.js      # MCP aggregator combining tool sources
│   ├── opspilot-tools.js  # OpsPilot operations tools
│   ├── server.js          # Original MCP server
│   └── package.json
├── frontend/              # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx       # Home page with run list
│   │   ├── runs/[id]/     # Run detail page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── FinalReport.tsx
│   │   ├── Timeline.tsx
│   │   └── ToolCallCard.tsx
│   ├── lib/
│   │   └── api.ts         # API client
│   └── package.json
├── docker/                # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile.agent
│   └── Dockerfile.frontend
├── data/                  # Mock data for testing
│   ├── logs/
│   ├── metrics/
│   └── tickets/
└── README.md

---

## Local Development (Without Docker)

### Backend Setup
```bash
cd agent_service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
echo "ANTHROPIC_API_KEY=your_key_here" > .env
echo "REDIS_URL=redis://localhost:6379" >> .env

# Initialize database
python init_db.py

# Start Redis
brew services start redis  # macOS
# or: sudo systemctl start redis  # Linux

# Run server
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Access at http://localhost:3000

---

## Usage Examples

### Example 1: Investigate Error Spike

**Goal:** "Investigate error spikes in the last hour and create an incident ticket if needed"

**Agent Actions:**
1. Searches logs for error patterns
2. Queries error rate metrics
3. Analyzes severity and frequency
4. Creates incident ticket if threshold exceeded

### Example 2: Database Performance Issue

**Goal:** "Investigate database timeouts in the last 5 hours and create ticket if required"

**Agent Actions:**
1. Searches logs for timeout errors
2. Queries response time metrics
3. Correlates logs with metrics
4. Generates performance report
5. Requests approval to create ticket
6. Creates ticket with evidence

---

## Available Tools

### Operations Tools
- **`search_logs`**: Search application logs by pattern and time range
- **`query_metrics`**: Query time-series metrics (error_rate, response_time, cpu_usage, memory_usage)
- **`create_ticket`**: Create incident tickets (requires approval)
- **`generate_report`**: Generate investigation reports with findings

### Filesystem Tools (via MCP)
- **`read_file`**: Read contents from /app/data directory
- **`write_file`**: Write contents to /app/data directory
- **`list_directory`**: List files and directories in /app/data

All tools are dynamically discovered via MCP protocol at runtime.

### Adding New Tools

1. Create tool file in `agent_service/tools/`
2. Implement tool function with clear docstring
3. Add tool to `agent_service/agent.py` tool registry
4. Restart agent

---

## Project Structure
```
opspilot/
├── agent_service/          # Backend API and agent
│   ├── agent.py           # Core agent with state machine
│   ├── main.py            # FastAPI server
│   ├── models.py          # SQLAlchemy models
│   ├── state_machine.py   # State definitions
│   ├── database.py        # Database configuration
│   ├── tools/             # Tool implementations
│   │   ├── search_logs.py
│   │   ├── query_metrics.py
│   │   ├── create_ticket.py
│   │   └── generate_report.py
│   ├── init_db.py         # Database initialization
│   └── requirements.txt
├── frontend/              # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx       # Home page with run list
│   │   ├── runs/[id]/     # Run detail page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── FinalReport.tsx
│   │   ├── Timeline.tsx
│   │   └── ToolCallCard.tsx
│   ├── lib/
│   │   └── api.ts         # API client
│   └── package.json
├── docker/                # Docker configuration
│   ├── docker-compose.yml
│   ├── Dockerfile.agent
│   └── Dockerfile.frontend
├── data/                  # Mock data for testing
│   ├── logs/
│   ├── metrics/
│   └── tickets/
└── README.md
```

---

## Configuration

### Environment Variables

**Backend (`agent_service/.env`):**
```bash
ANTHROPIC_API_KEY=your_api_key_here
REDIS_URL=redis://redis:6379  # For Docker
DATABASE_URL=sqlite:///./opspilot.db
```

**Frontend:**
Set in `docker-compose.yml` or as env variable:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Testing

### Create Test Run via API
```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"goal": "Search logs for errors in the last hour"}'
```

### Execute Run
```bash
curl -X POST http://localhost:8000/runs/1/execute
```

### Check Run Status
```bash
curl http://localhost:8000/runs/1
```

---

## Technical Details

### Technologies

- **Backend:** FastAPI, SQLAlchemy, Redis, Anthropic Claude API (Sonnet 4)
- **MCP Server:** Node.js, @modelcontextprotocol/sdk
- **Frontend:** Next.js 15, React, Tailwind CSS, TypeScript
- **Database:** SQLite (dev), PostgreSQL-ready
- **Deployment:** Docker Compose

### Key Design Decisions

1. **Explicit State Machine**: Makes agent behavior predictable and debuggable
2. **MCP Integration**: Standardized protocol for tool discovery and execution
3. **Tool Aggregation**: Combines multiple tool sources (ops + filesystem) via MCP
4. **Approval Workflows**: Prevents autonomous actions from causing issues
5. **Audit Trail**: Every step, tool call, and decision is logged
6. **Retry Logic**: Redis-backed exponential backoff for API failures
7. **Tool Abstraction**: Clean interface for adding new capabilities

---

## Future Enhancements

- [ ] Multi-agent collaboration
- [ ] Custom tool library per organization
- [ ] Advanced approval policies (role-based)
- [ ] Slack/email notifications
- [ ] Metrics visualization charts
- [ ] PostgreSQL support for production
- [ ] Kubernetes deployment configs

---

## 📝 License

MIT License - feel free to use for learning or production!

---

## Contributing

Built as a personal project. Feedback and suggestions welcome!

---

## Author

**Ahan Jain**
- Northeastern University, Computer Science (AI Concentration)
- [GitHub](https://github.com/yourusername)
- [LinkedIn](https://linkedin.com/in/yourprofile)

---

## Acknowledgments

- Built with Anthropic's Claude API
- Inspired by production ops automation needs