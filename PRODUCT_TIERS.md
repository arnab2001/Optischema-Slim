# OptiSchema Product Tiers: Slim, Standalone, and Agent (SaaS)

## Overview

OptiSchema is available in three deployment tiers to serve different user needs, from individual developers to large enterprises to fully managed SaaS.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  OptiSchema     │     │  OptiSchema      │     │  OptiSchema     │
│  SLIM           │     │  STANDALONE      │     │  AGENT (SaaS)   │
│  (Local)        │     │  (Enterprise)    │     │  (Cloud)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
   Developer Tool         Private Cloud           Managed Service
```

---

## 1. OptiSchema Slim (Local Developer Tool)

### Target Users
- Individual developers
- Database administrators
- Small teams (1-5 people)
- Students and learners

### Deployment Model
**Desktop Application** - Runs entirely on your laptop/workstation

```bash
# Installation (Future)
brew install optischema-slim  # macOS
# or
docker-compose up  # Current method
```

### Key Features

| Feature | Implementation |
|---------|----------------|
| **Authentication** | ❌ Disabled (single user) |
| **LLM** | 🏠 Local (Ollama - SQLCoder) |
| **Database** | 📝 Direct connection string |
| **State Storage** | 💾 Local SQLite or Docker volume |
| **Multi-tenancy** | ❌ Not needed |
| **Internet Required** | ❌ No (fully offline capable) |

### Configuration

```bash
# .env for Slim
ENABLE_AUTHENTICATION=false
LLM_PROVIDER=ollama
OLLAMA_MODEL=sqlcoder
DATABASE_URL=postgresql://localhost:5432/mydb
```

### User Experience

1. **Launch**: Double-click app or `docker-compose up`
2. **Connect**: Enter database credentials (saved locally)
3. **Analyze**: Automatic query monitoring starts
4. **Optimize**: Review AI recommendations, apply with one click

### Pricing
**Free** (Open Source)

### Distribution
- Docker Compose (Now)
- Electron Desktop App (Q2 2025)
- Homebrew/Chocolatey packages (Q3 2025)

---

## 2. OptiSchema Standalone (Enterprise Private Cloud)

### Target Users
- Large enterprises (100+ employees)
- Regulated industries (Healthcare, Finance)
- Organizations with strict data sovereignty requirements
- Platform engineering teams

### Deployment Model
**Self-Hosted in Private Cloud** - Kubernetes, AWS VPC, Azure VNet

```bash
# Installation
helm install optischema ./helm-chart \
  --set auth.enabled=true \
  --set llm.provider=azure \
  --set discovery.rds.enabled=true
```

### Key Features

| Feature | Implementation |
|---------|----------------|
| **Authentication** | ✅ JWT, SSO (SAML/OIDC), RBAC |
| **LLM** | ☁️ Private Cloud (Azure OpenAI, AWS Bedrock) |
| **Database** | 🔍 **Auto-Discovery** (RDS, Aurora, Azure SQL) |
| **State Storage** | 🗄️ Managed Postgres (RDS/Aurora) |
| **Multi-tenancy** | ✅ Full isolation per team/project |
| **Internet Required** | ⚠️ Only for LLM (can be VPC-only) |

### Configuration

```yaml
# values.yaml (Helm)
auth:
  enabled: true
  sso:
    provider: okta
    domain: company.okta.com

llm:
  provider: azure
  endpoint: https://company.openai.azure.com
  
discovery:
  aws:
    enabled: true
    regions: [us-east-1, eu-west-1]
    iamRole: arn:aws:iam::123456789:role/OptiSchemaDiscovery
  azure:
    enabled: true
    subscriptionId: xxx-xxx-xxx
```

### User Experience

1. **Deploy**: Platform team deploys via Helm/Terraform
2. **Login**: Users authenticate via corporate SSO
3. **Discover**: OptiSchema scans VPC for RDS instances
4. **Connect**: Select databases from discovered list (IAM auth)
5. **Collaborate**: Share recommendations across teams

### Unique Enterprise Features

#### A. RDS Auto-Discovery
```python
# Discovers all accessible databases
discovered_dbs = await RDSDiscovery.scan_vpc(
    regions=['us-east-1'],
    iam_role='OptiSchemaRole'
)
# Returns: [
#   {name: 'prod-users-db', endpoint: '...', engine: 'postgres'},
#   {name: 'analytics-db', endpoint: '...', engine: 'postgres'}
# ]
```

#### B. IAM Database Authentication
No passwords stored - uses AWS IAM tokens or Azure Managed Identity.

#### C. Audit Logging
```sql
-- Who optimized what?
SELECT user_email, query_optimized, recommendation_applied, timestamp
FROM optischema.audit_log
WHERE applied = true;
```

#### D. RBAC (Role-Based Access Control)
- **Admin**: Can apply optimizations
- **Analyst**: Can view and suggest
- **Viewer**: Read-only access

### Pricing
**Enterprise License** - Contact sales  
(Estimated: $5,000-$50,000/year based on database count)

### Distribution
- Helm Charts (Kubernetes)
- Terraform Modules (AWS/Azure/GCP)
- Docker Compose (for testing)

---

## 3. OptiSchema Agent (SaaS - Managed Cloud)

### Target Users
- Startups and scale-ups
- Teams without DevOps resources
- Companies wanting zero-ops solution
- Trial/proof-of-concept users

### Deployment Model
**Fully Managed SaaS** - We run it, you just use it

```
https://app.optischema.com
```

### Key Features

| Feature | Implementation |
|---------|----------------|
| **Authentication** | ✅ Email/Password, Google SSO, GitHub SSO |
| **LLM** | ☁️ Cloud (Gemini, GPT-4) - We manage |
| **Database** | 🔌 **Secure Tunnel** (SSH/VPN) or Public endpoint |
| **State Storage** | 🗄️ Managed by us (Multi-tenant Postgres) |
| **Multi-tenancy** | ✅ Per organization |
| **Internet Required** | ✅ Yes |

### Configuration

```javascript
// Web UI - No config files
1. Sign up at app.optischema.com
2. Add database connection (encrypted)
3. Install agent (optional, for private DBs)
4. Start optimizing
```

### User Experience

1. **Sign Up**: Email or Google/GitHub
2. **Connect Database**:
   - **Option A**: Direct (if DB has public endpoint)
   - **Option B**: Install lightweight agent in your VPC
3. **Monitor**: Real-time dashboard
4. **Optimize**: AI recommendations delivered to your inbox

### Unique SaaS Features

#### A. Secure Agent (for Private Databases)
```bash
# Install in your VPC
curl -sSL https://get.optischema.com | bash
optischema-agent connect --token YOUR_TOKEN

# Agent creates outbound-only tunnel (no inbound ports)
```

#### B. Slack/Email Notifications
```
🔔 OptiSchema Alert
Database: prod-db
Issue: Missing index on users.email (1M rows)
Impact: 85% query speedup
Action: [Apply Fix] [Review]
```

#### C. Collaborative Workspace
- Share recommendations with team
- Comment and discuss
- Track who applied what

#### D. Managed Upgrades
We handle all updates, security patches, and scaling.

### Pricing

| Plan | Price | Databases | Users | Support |
|------|-------|-----------|-------|---------|
| **Free** | $0/mo | 1 | 1 | Community |
| **Team** | $99/mo | 5 | 10 | Email |
| **Business** | $499/mo | 20 | Unlimited | Priority |
| **Enterprise** | Custom | Unlimited | Unlimited | Dedicated |

### Distribution
- Web Application (app.optischema.com)
- Agent Binary (for private DB access)

---

## 4. Feature Comparison Matrix

| Feature | Slim | Standalone | Agent (SaaS) |
|---------|------|------------|--------------|
| **Deployment** | Local | Private Cloud | Managed Cloud |
| **Setup Time** | 5 min | 1-2 hours | 2 min |
| **Authentication** | None | SSO/RBAC | Email/SSO |
| **LLM** | Local (Free) | Private (Your cost) | Cloud (Included) |
| **Database Discovery** | Manual | Auto (RDS/Azure) | Manual + Agent |
| **Data Privacy** | 100% Local | 100% Your VPC | Encrypted tunnel |
| **Collaboration** | ❌ | ✅ | ✅ |
| **Audit Logs** | ❌ | ✅ | ✅ |
| **Auto-Updates** | Manual | Helm upgrade | Automatic |
| **Cost** | Free | License + Infra | Subscription |
| **Best For** | Solo devs | Enterprises | Teams |

---

## 5. Migration Paths

### From Slim → Standalone
```bash
# Export your connection configs
optischema-slim export --output connections.json

# Import to Standalone
kubectl exec -it optischema-0 -- \
  optischema import --file connections.json
```

### From Slim → SaaS
```bash
# Just add your DB connection in the web UI
# Historical data stays local (privacy preserved)
```

### From SaaS → Standalone
```bash
# Export recommendations
curl https://api.optischema.com/export > recommendations.json

# Deploy Standalone and import
helm install optischema ./chart
kubectl exec -it optischema-0 -- \
  optischema import --file recommendations.json
```

---

## 6. Technical Architecture Comparison

### Slim Architecture
```
┌──────────────────────────────────────┐
│  Your Laptop                         │
│  ┌────────────┐    ┌──────────────┐ │
│  │  Browser   │───▶│  FastAPI     │ │
│  │  (UI)      │    │  Backend     │ │
│  └────────────┘    └──────┬───────┘ │
│                           │          │
│  ┌────────────┐    ┌──────▼───────┐ │
│  │  Ollama    │◀───│  PostgreSQL  │ │
│  │  (Local)   │    │  (Docker)    │ │
│  └────────────┘    └──────────────┘ │
└──────────────────────────────────────┘
```

### Standalone Architecture
```
┌─────────────────────────────────────────────┐
│  Your AWS VPC                               │
│  ┌──────────┐                               │
│  │  ALB     │                               │
│  └────┬─────┘                               │
│       │                                     │
│  ┌────▼──────────────────────────────────┐ │
│  │  Kubernetes Cluster                   │ │
│  │  ┌─────────────┐  ┌─────────────┐    │ │
│  │  │ OptiSchema  │  │ OptiSchema  │    │ │
│  │  │ Pod 1       │  │ Pod 2       │    │ │
│  │  └──────┬──────┘  └──────┬──────┘    │ │
│  └─────────┼─────────────────┼───────────┘ │
│            │                 │             │
│  ┌─────────▼─────────────────▼───────────┐ │
│  │  RDS PostgreSQL (State)               │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  Azure OpenAI (Private Endpoint)      │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### SaaS Architecture
```
┌────────────────────────────────────────────┐
│  OptiSchema Cloud (Our Infrastructure)    │
│  ┌──────────────────────────────────────┐ │
│  │  Web App (Next.js)                   │ │
│  └────────────┬─────────────────────────┘ │
│               │                            │
│  ┌────────────▼─────────────────────────┐ │
│  │  API (FastAPI - Multi-tenant)        │ │
│  └────────────┬─────────────────────────┘ │
│               │                            │
│  ┌────────────▼─────────────────────────┐ │
│  │  Shared Postgres (Tenant-isolated)   │ │
│  └──────────────────────────────────────┘ │
└────────────────┬───────────────────────────┘
                 │ Encrypted Tunnel
┌────────────────▼───────────────────────────┐
│  Customer VPC                              │
│  ┌──────────────────────────────────────┐ │
│  │  OptiSchema Agent (Lightweight)      │ │
│  │  - Connects to customer DB           │ │
│  │  - Sends metrics (encrypted)         │ │
│  │  - Receives recommendations          │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

---

## 7. Roadmap

### Q1 2025
- [x] Slim: Docker Compose version
- [x] Standalone: Stateless backend
- [x] Standalone: Authentication system
- [ ] Standalone: RDS Discovery (AWS)

### Q2 2025
- [ ] Slim: Electron Desktop App
- [ ] Standalone: Helm Charts
- [ ] SaaS: Beta launch (invite-only)

### Q3 2025
- [ ] Slim: Auto-update mechanism
- [ ] Standalone: Azure SQL Discovery
- [ ] SaaS: Public launch

### Q4 2025
- [ ] All: Fine-tuned OptiSchema LLM
- [ ] SaaS: Enterprise tier with dedicated instances

---

## 8. Choosing the Right Tier

### Choose **Slim** if:
- ✅ You're a solo developer or small team
- ✅ You want complete data privacy
- ✅ You don't need collaboration features
- ✅ You're okay with manual setup

### Choose **Standalone** if:
- ✅ You're an enterprise with compliance requirements
- ✅ You need SSO and RBAC
- ✅ You have many databases to manage
- ✅ You have a platform/DevOps team

### Choose **SaaS** if:
- ✅ You want zero setup/maintenance
- ✅ You need quick proof-of-concept
- ✅ You want automatic updates
- ✅ You're okay with managed service

---

## 9. FAQ

**Q: Can I start with Slim and upgrade later?**  
A: Yes! You can export your data and migrate to Standalone or SaaS.

**Q: Is my data safe in SaaS mode?**  
A: Yes. We use encrypted tunnels and never store query results, only metadata.

**Q: Can I run Standalone without internet?**  
A: Yes, if you use a local LLM (Ollama) instead of cloud LLM.

**Q: What's the difference between Standalone and SaaS for enterprises?**  
A: Standalone = you manage infrastructure. SaaS = we manage everything.

**Q: Can I customize the UI?**  
A: Slim/Standalone: Yes (open source). SaaS: Limited (white-label available for Enterprise tier).

---

## Contact

- **Slim (Open Source)**: GitHub Issues
- **Standalone (Enterprise)**: enterprise@optischema.com
- **SaaS**: support@optischema.com
