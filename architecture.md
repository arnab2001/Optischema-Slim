
## 3. Tech Stack

### Frontend Framework
- **Next.js 15.4.1** with React 19.1.0 and TypeScript 4.9.5
- **UI Components**: Radix UI primitives (@radix-ui/react-dialog, @radix-ui/react-toast)
- **Styling**: Tailwind CSS 3.3.3 with custom design system
- **Charts & Visualization**: Recharts 3.1.0 for performance metrics
- **State Management**: SWR 2.2.4 for data fetching and caching
- **Icons**: Lucide React 0.525.0
- **Additional Libraries**:
  - React Heatmap Grid for query performance heatmaps
  - React Markdown for AI-generated content display
  - HTML2Canvas + jsPDF for export functionality
  - WebSocket client for real-time updates

### Backend Framework
- **FastAPI 0.104.1** with Python 3.11+ (async/await architecture)
- **ASGI Server**: Uvicorn 0.24.0 with standard extensions
- **Database ORM**: AsyncPG 0.29.0 for PostgreSQL async operations
- **Configuration**: Pydantic 2.5.0 with Pydantic Settings 2.1.0
- **Data Processing**: 
  - Pandas 2.1.3 for metrics analysis
  - SQLGlot 27.0.0 for SQL parsing and manipulation
  - NumPy 1.24.3 for numerical computations
- **HTTP Client**: HTTPX 0.25.2 for external API calls
- **Logging**: Structlog 23.2.0 for structured logging

### Database & Storage
- **Primary Database**: PostgreSQL 14 with pg_stat_statements extension
- **Cache Layer**: DiskCache 5.6.3 for LLM response caching
- **Recommendation Storage**: 
  - SQLite 3 (recommendations.db) for structured data
  - JSON file-based storage (simple_recommendations.json) for fallback
- **Sandbox Environment**: Isolated PostgreSQL 14 instance for safe testing
- **Connection Pooling**: AsyncPG connection pool for concurrent database access

### AI/ML Tools
- **Multi-LLM Support**:
  - **Google Gemini 2.0 Flash** (primary) via Google AI API
  - **OpenAI GPT-4o** (fallback) via OpenAI API
  - **DeepSeek Chat** (alternative) via DeepSeek API
- **AI Integration**:
  - Custom prompt engineering for PostgreSQL optimization
  - Structured JSON response parsing with fallback handling
  - Response caching with fingerprint-based keys
  - Multi-model failover system
- **Query Analysis**: 
  - SQL parsing and fingerprinting
  - Execution plan analysis and normalization
  - Heuristic-based issue detection

### Infrastructure & DevOps
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose with service networking
- **Development Environment**:
  - Hot reload for both frontend and backend
  - Volume mounting for live code changes
  - Environment variable management via .env files
- **Networking**: 
  - Internal Docker network (optischema-network)
  - Service discovery via container names
  - Port mapping for external access
- **Data Persistence**: 
  - Named Docker volumes for PostgreSQL data
  - Cache volume for API responses
  - Sandbox data volume for testing

### Monitoring & Observability
- **Health Checks**: Built-in health endpoints for all services
- **Logging**: Structured logging with configurable levels
- **WebSocket**: Real-time updates for dashboard metrics
- **Error Handling**: Comprehensive error catching and user-friendly messages

## 4. Architecture

### High-Level System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   AI Services   │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Multi-LLM)   │
│   Port: 3000    │    │   Port: 8080    │    │   (External)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌────────▼────────┐              │
         │              │   PostgreSQL    │              │
         │              │   (Primary)     │              │
         │              │   Port: 5432    │              │
         │              └─────────────────┘              │
         │                       │                       │
         │              ┌────────▼────────┐              │
         │              │   PostgreSQL    │              │
         │              │   (Sandbox)     │              │
         │              │   Port: 5433    │              │
         │              └─────────────────┘              │
         │                       │                       │
         │              ┌────────▼────────┐              │
         │              │   Cache Layer   │              │
         │              │   (DiskCache)   │              │
         │              └─────────────────┘              │
         └───────────────────────────────────────────────┘
```

### Data Flow Architecture

#### 1. Real-Time Query Monitoring Flow
```
User Dashboard → Next.js Frontend → API Gateway (Next.js rewrites) → FastAPI Backend → PostgreSQL (pg_stat_statements) → WebSocket → Real-time UI Updates
```

#### 2. AI-Powered Analysis Flow
```
Query Metrics → Analysis Pipeline → LLM API (Gemini/OpenAI/DeepSeek) → Response Caching → Recommendation Storage → Frontend Display
```

#### 3. Sandbox Testing Flow
```
Optimization Suggestion → Sandbox Environment → Benchmark Execution → Performance Comparison → Results Storage → UI Feedback
```

#### 4. Apply/Rollback Flow
```
User Approval → Apply Manager → Production Database → Audit Logging → Rollback SQL Generation → Status Updates → UI Notification
```

### Detailed Component Interactions

#### Frontend Layer (Next.js)
- **Dashboard Components**: Real-time metrics display with WebSocket integration
- **API Routes**: Next.js API routes that proxy requests to FastAPI backend
- **State Management**: SWR for data fetching with automatic revalidation
- **WebSocket Client**: Real-time updates for live metrics and recommendations

#### Backend Layer (FastAPI)
- **REST API**: Comprehensive REST endpoints for all operations
- **WebSocket Server**: Real-time communication with frontend
- **Analysis Pipeline**: Automated query analysis and recommendation generation
- **Connection Manager**: Database connection pooling and management
- **Cache Manager**: LLM response caching and invalidation

#### AI Integration Layer
- **Multi-LLM Router**: Intelligent routing between different AI providers
- **Prompt Engineering**: Specialized prompts for PostgreSQL optimization
- **Response Parser**: JSON parsing with fallback to text parsing
- **Cache System**: Fingerprint-based caching for cost optimization

#### Database Layer
- **Primary PostgreSQL**: Main application database with pg_stat_statements
- **Sandbox PostgreSQL**: Isolated testing environment
- **SQLite**: Lightweight storage for recommendations and metadata
- **Connection Pooling**: AsyncPG for efficient database connections

### Service Communication Patterns

#### 1. Synchronous Communication
- **Frontend ↔ Backend**: REST API calls via Next.js rewrites
- **Backend ↔ Database**: AsyncPG connection pool
- **Backend ↔ AI APIs**: HTTPX async client with retry logic

#### 2. Asynchronous Communication
- **WebSocket**: Real-time metrics updates and notifications
- **Background Tasks**: Analysis pipeline and recommendation generation
- **Event-driven**: Cache invalidation and data synchronization

#### 3. Data Persistence Patterns
- **Write-through Cache**: LLM responses cached immediately after generation
- **Event Sourcing**: Audit trail for all database changes
- **Snapshot Storage**: Periodic snapshots of query performance metrics

### Security & Safety Features

#### Database Safety
- **Read-only by default**: Production database connections are read-only
- **Whitelisted DDL**: Only safe DDL operations (CREATE INDEX CONCURRENTLY)
- **Rollback SQL**: Automatic rollback SQL generation for all changes
- **Audit Trail**: Complete logging of all database modifications

#### AI Safety
- **Response Validation**: JSON schema validation for AI responses
- **Fallback Mechanisms**: Heuristic-based recommendations when AI fails
- **Cost Controls**: Caching to minimize API costs
- **PII Protection**: Configurable PII-safe mode for sensitive data

#### Infrastructure Safety
- **Container Isolation**: Each service runs in isolated containers
- **Network Segmentation**: Internal Docker network for service communication
- **Environment Variables**: Secure configuration management
- **Health Monitoring**: Continuous health checks for all services

## 5. Issues & Pain Points

### Technical Blockers

**Infrastructure & Scaling:**
- **Single-instance limitation**: Current architecture doesn't support horizontal scaling
- **Database connection pooling**: Limited connection management for high-concurrency scenarios
- **Memory usage**: Analysis pipeline can consume significant memory with large datasets
- **Latency issues**: Some API endpoints have inconsistent response times
- **Docker resource constraints**: Development environment resource limitations

**Data Management:**
- **Sandbox synchronization**: Manual, error-prone process for syncing production data
- **Data consistency**: Potential drift between production and sandbox environments
- **Storage fragmentation**: Multiple recommendation storage systems causing data inconsistency
- **Cache invalidation**: Inconsistent cache management across different components

**AI/ML Integration:**
- **LLM response variability**: Inconsistent quality of AI-generated recommendations
- **Cost management**: No proper cost controls for LLM API usage
- **Model switching**: Limited ability to switch between different AI providers dynamically
- **Response caching**: Inefficient caching strategy for AI responses

### Product Blockers

**User Experience:**
- **Learning curve**: Complex interface requires significant user training
- **Limited customization**: Dashboard lacks user-specific customization options
- **Mobile responsiveness**: Limited mobile device support
- **Onboarding process**: No guided setup or tutorial system
- **Error messaging**: Technical error messages not user-friendly

**Feature Gaps:**
- **Multi-tenant support**: No support for multiple database instances per user
- **Scheduling**: No ability to schedule optimizations during maintenance windows
- **Notifications**: Limited alerting and notification system
- **Reporting**: No comprehensive reporting or export capabilities
- **Integration**: Limited third-party integrations (monitoring tools, CI/CD)

**Performance & Reliability:**
- **Query timeout handling**: Some long-running queries cause UI freezing
- **Real-time updates**: WebSocket connections can be unstable
- **Data refresh**: Inconsistent data refresh intervals
- **Error recovery**: Limited automatic error recovery mechanisms

### Team/Resource Constraints

**Development Resources:**

- **Documentation debt**: Limited documentation for complex components
- **Code quality**: Some technical debt in legacy components

**Infrastructure Constraints:**
- **Development environment**: Limited resources for comprehensive testing
- **Production readiness**: Not yet optimized for production deployment
- **Security review**: Limited security audit and penetration testing
- **Performance testing**: No load testing for high-traffic scenarios

**Business Constraints:**
- **Market validation**: Limited user feedback and market research
- **Competitive analysis**: Insufficient analysis of competing solutions
- **Pricing strategy**: No clear pricing model or business strategy
- **Go-to-market**: No defined customer acquisition strategy
