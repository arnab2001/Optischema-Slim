# 🎯 OptiSchema

An AI-assisted database tuning service that monitors PostgreSQL workloads, identifies performance bottlenecks, and delivers actionable, one-click fixes with projected cost/latency savings.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- AI API Key (Gemini or DeepSeek)
- Git

### Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd optischema
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your AI API key and other settings
   ```

3. **Start the development stack**
   ```bash
   make dev
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 🏗️ Architecture

### Backend (Python 3.12 + FastAPI)
- **Database Poller**: Monitors `pg_stat_statements` every 30 seconds with adaptive filtering
- **Analysis Engine**: Multi-model AI integration (Gemini 2.0 Flash, DeepSeek Chat)
- **Query Fingerprinting**: Intelligent query normalization and deduplication
- **Execution Plan Analysis**: Deep PostgreSQL explain plan parsing and bottleneck detection
- **Real-time Communication**: WebSocket server for live updates
- **Caching System**: SQLite-based caching for AI responses to reduce costs
- **Data Processing**: Robust metrics collection with fallback to calculated scores

### Frontend (Next.js 14 + TypeScript + Tailwind)
- **Live Dashboard**: Real-time performance metrics with responsive design
- **Interactive Query Analysis**: Detailed query breakdowns with execution plans
- **AI Recommendations**: Interactive modals with confidence scoring and benchmarks
- **Connection Management**: Database connection wizard with secure credential storage
- **Dark Mode Support**: Full dark/light theme support with keyboard navigation
- **Markdown Rendering**: Rich formatting for AI recommendations and explanations
- **Advanced Analytics**: Interactive charts with heat maps and trend analysis

### Infrastructure (Docker Compose)
- **PostgreSQL 14**: Main database with `pg_stat_statements` extension
- **PostgreSQL Sandbox**: Isolated instance for safe optimization testing
- **API Service**: FastAPI backend container with hot-reload
- **UI Service**: Next.js frontend container with hot-reload

## 📊 Features

### Real-time Monitoring
- Continuous PostgreSQL query performance tracking with smart filtering
- Automatic identification of hot queries and performance bottlenecks
- Execution plan analysis with detailed bottleneck detection
- Business query filtering (excludes system queries)
- Graceful fallback to calculated performance scores when metrics unavailable

### AI-Powered Analysis
- Multi-model AI support (Gemini, DeepSeek) for query optimization
- Plain-English explanations of execution plans with markdown formatting
- Intelligent query rewrite suggestions with proper JSON formatting
- Strategic index and configuration recommendations
- Confidence scoring and risk assessment
- Transparent data source indicators (actual metrics vs calculated scores)

### One-Click Optimization
- Safe sandbox environment for testing patches
- Before/after performance benchmarking
- Automatic rollback SQL generation
- Cost-benefit projections for each optimization
- Clean recommendation display without raw markdown artifacts

### Advanced UI Features
- Responsive design with mobile optimization
- Real-time WebSocket updates
- Interactive query tables with sorting and filtering
- Performance badges and visual indicators
- Keyboard navigation and accessibility features
- Advanced analytics with heat maps and trend visualization
- Export functionality for reports and data

## 🛠️ Development

### Project Structure
```
optischema/
├── backend/          # FastAPI application
│   ├── analysis/     # AI analysis engine
│   ├── routers/      # API endpoints
│   └── models.py     # Data models
├── frontend/         # Next.js application
│   ├── app/          # App router pages
│   ├── components/   # React components
│   └── hooks/        # Custom hooks
├── scripts/          # Demo and utility scripts
├── docs/             # Documentation
│   └── archive/      # Historical documentation
├── docker-compose.yml
├── DEMO.md           # Demo guide
├── PROJECT_CONTEXT.md # Project overview
└── README.md
```

### Available Commands
- `make dev` - Start development stack with hot-reload
- `make demo` - Seed demo data and start the application
- `make clean` - Stop and clean all containers
- `make logs` - View logs from all services
- `make sandbox` - Start sandbox environment for testing

### Development Workflow
1. **Backend Development**: Edit files in `backend/` - auto-reloads
2. **Frontend Development**: Edit files in `frontend/` - auto-reloads
3. **Database Changes**: Use `make demo` to reset with fresh data

## 🔧 Configuration

### Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `GEMINI_API_KEY` - Google Gemini API key
- `DEEPSEEK_API_KEY` - DeepSeek API key
- `LLM_PROVIDER` - AI provider preference (gemini/deepseek)
- `UI_WS_URL` - WebSocket URL for real-time updates
- `POSTGRES_PASSWORD` - PostgreSQL password

### API Endpoints
- `GET /health` - Health check
- `GET /api/metrics/raw` - Raw query metrics with pagination
- `GET /api/suggestions/latest` - Latest optimization suggestions
- `POST /api/suggestions/apply` - Apply optimization in sandbox
- `POST /api/suggestions/benchmark` - Benchmark optimization
- `WS /ws` - WebSocket for real-time updates

## 📈 Performance Metrics

### Technical Targets
- **API Response Time**: < 100ms
- **Real-time Updates**: < 2s latency
- **AI Response Time**: < 5s
- **Dashboard Load Time**: < 3s

### Quality Targets
- **Recommendation Accuracy**: > 80%
- **Apply Success Rate**: > 95%
- **System Uptime**: > 99%

## 🧪 Demo

Run the demo to see OptiSchema in action:

```bash
make demo
```

This will:
1. Start all services
2. Seed the database with realistic demo data
3. Generate intentional performance bottlenecks
4. Show the system identifying and suggesting optimizations

See [DEMO.md](DEMO.md) for detailed demo scenarios and troubleshooting.

## 📚 Documentation

- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) - Project overview and architecture
- [ENHANCED_IMPLEMENTATION_PLAN.md](ENHANCED_IMPLEMENTATION_PLAN.md) - Development roadmap
- [DEMO.md](DEMO.md) - Demo guide and scenarios
- [docs/archive/](docs/archive/) - Historical documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `make dev`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions or issues:
1. Check the documentation in the project root
2. Review the API documentation at `http://localhost:8000/docs`
3. Open an issue on GitHub

---

**OptiSchema** - Making PostgreSQL optimization accessible to everyone. 🚀 