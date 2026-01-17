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

- **`search_logs`**: Search application logs by pattern and time range
- **`query_metrics`**: Query time-series metrics (error rate, response time, CPU, memory)
- **`create_ticket`**: Create incident tickets (requires approval)
- **`generate_report`**: Generate investigation reports with findings

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

- **Backend:** FastAPI, SQLAlchemy, Redis, Anthropic Claude API
- **Frontend:** Next.js 15, React, Tailwind CSS, TypeScript
- **Database:** SQLite (dev), PostgreSQL-ready
- **Deployment:** Docker Compose

### Key Design Decisions

1. **Explicit State Machine**: Makes agent behavior predictable and debuggable
2. **Approval Workflows**: Prevents autonomous actions from causing issues
3. **Audit Trail**: Every step, tool call, and decision is logged
4. **Retry Logic**: Redis-backed exponential backoff for API failures
5. **Tool Abstraction**: Clean interface for adding new capabilities

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