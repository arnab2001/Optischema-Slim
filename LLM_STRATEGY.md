# OptiSchema LLM Strategy & Model Recommendations

## Executive Summary

OptiSchema uses Large Language Models (LLMs) to generate intelligent database optimization recommendations. This document outlines our multi-tier LLM strategy that supports privacy-first local deployment, enterprise private cloud, and cloud-based SaaS offerings.

---

## 1. LLM Provider Architecture

We've implemented a **flexible provider pattern** that allows OptiSchema to work with multiple LLM backends:

```python
# Current Supported Providers
- Gemini (Google) - Cloud API
- DeepSeek - Cloud API  
- Ollama - Local/Self-Hosted
- Azure OpenAI - Enterprise Cloud (Planned)
- AWS Bedrock - Enterprise Cloud (Planned)
```

### Provider Selection

Set via environment variable:
```bash
LLM_PROVIDER=ollama  # or gemini, deepseek, azure, bedrock
```

---

## 2. Recommended Models for SQL Optimization

### A. Local/Self-Hosted (Ollama)

**Best for**: Privacy, offline usage, no API costs

| Model | Size | Performance | Use Case |
|-------|------|-------------|----------|
| **CodeLlama 13B** ⭐ | 7.4GB | Excellent | **Recommended** - Best for SQL generation |
| **SQLCoder 15B** ⭐⭐ | 8.5GB | Outstanding | **Best** - Fine-tuned specifically for SQL |
| **Llama 3 8B** | 4.7GB | Good | Lightweight option for basic queries |
| **DeepSeek Coder 6.7B** | 3.8GB | Very Good | Fast, good for simple optimizations |

**Installation:**
```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.com

# Pull recommended model
ollama pull sqlcoder

# Configure OptiSchema
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=sqlcoder
export OLLAMA_BASE_URL=http://localhost:11434
```

**Hardware Requirements:**
- **Minimum**: 8GB RAM, CPU-only (slow)
- **Recommended**: 16GB RAM, Apple M1/M2 or NVIDIA GPU
- **Optimal**: 32GB RAM, NVIDIA RTX 3090/4090

### B. Cloud APIs (Public)

**Best for**: Quick setup, no infrastructure

| Provider | Model | Cost | Quality |
|----------|-------|------|---------|
| **Google Gemini** | gemini-2.0-flash | $0.075/1M tokens | Excellent |
| **DeepSeek** | deepseek-chat | $0.14/1M tokens | Very Good |
| **OpenAI** | gpt-4o | $2.50/1M tokens | Outstanding |

**Privacy Concern**: Query data is sent to third-party servers.

### C. Private Cloud (Enterprise)

**Best for**: Enterprise compliance, data sovereignty

| Provider | Service | Benefits |
|----------|---------|----------|
| **Azure** | Azure OpenAI Service | HIPAA/SOC2, VPC isolation, GPT-4 quality |
| **AWS** | Amazon Bedrock | Claude 3.5, VPC endpoints, IAM integration |
| **Google** | Vertex AI | Gemini Pro, Private endpoints |

**Key Advantage**: Data never leaves your VPC/private network.

---

## 3. Context-Aware AI Enhancement

We've implemented `DatabaseContextService` to provide **rich context** to LLMs:

```python
# What we send to the LLM:
{
  "query": "SELECT * FROM users WHERE email = ?",
  "schema_context": {
    "table": "users",
    "columns": ["id", "email", "name", "created_at"],
    "row_count": 1000000,
    "indexes": ["PRIMARY KEY (id)"]  # Missing email index!
  },
  "statistics": {
    "email_cardinality": 0.99,  # Highly selective
    "table_size": "150MB"
  }
}
```

**Result**: Even a smaller local model (CodeLlama 13B) can make **precise** recommendations because it has all the facts.

---

## 4. Performance Comparison

### Test Query: `SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending'`

| Model | Context | Recommendation Quality | Speed |
|-------|---------|----------------------|-------|
| GPT-4 (no context) | ❌ | Generic: "Add index on customer_id" | 2s |
| **SQLCoder + Context** | ✅ | **Specific**: "CREATE INDEX CONCURRENTLY idx_orders_customer_status ON orders(customer_id, status) -- Composite index covers both filters, 10M rows, est. 85% improvement" | 5s |
| Llama 3 8B + Context | ✅ | Good: "Index on (customer_id, status)" | 3s |

**Conclusion**: Context matters more than raw model intelligence for SQL tasks.

---

## 5. Privacy & Compliance Matrix

| Deployment | Data Location | Compliance | Cost |
|------------|---------------|------------|------|
| **Ollama (Local)** | Your laptop/server | ✅ GDPR, HIPAA, Air-gapped | Free |
| **Azure OpenAI** | Your Azure VPC | ✅ HIPAA, SOC2, BAA available | $$$ |
| **AWS Bedrock** | Your AWS VPC | ✅ HIPAA, SOC2 | $$$ |
| **Google Gemini** | Google Cloud (Public) | ⚠️ DPA required | $ |
| **OpenAI API** | OpenAI Servers (Public) | ❌ Not for sensitive data | $$ |

---

## 6. Hybrid Strategy (Recommended for Enterprise)

Use **local models for sensitive operations**, cloud models for general tasks:

```yaml
# Tier 1: Sensitive (Local)
- Schema analysis: Ollama (SQLCoder)
- Query rewriting: Ollama (CodeLlama)

# Tier 2: General (Cloud - Anonymized)
- Query explanations: Azure OpenAI (GPT-4)
- Documentation generation: Gemini
```

**Implementation**: Set fallback providers in config.

---

## 7. Quick Start Examples

### Example 1: Privacy-First (Local)
```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=sqlcoder
ENABLE_AUTHENTICATION=false  # Single user
```

### Example 2: Enterprise (Private Cloud)
```bash
# .env
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com
AZURE_OPENAI_KEY=your-key
ENABLE_AUTHENTICATION=true
```

### Example 3: SaaS (Public Cloud)
```bash
# .env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
ENABLE_AUTHENTICATION=true
```

---

## 8. Benchmarking Your Setup

Run our test script to compare model performance:

```bash
python scripts/benchmark_llm.py --model sqlcoder --queries test_queries.sql
```

**Metrics**:
- Recommendation accuracy
- Response time
- Token usage (cost)

---

## 9. Future Roadmap

- [ ] **Fine-tuned OptiSchema Model**: Train a specialized model on PostgreSQL optimization patterns
- [ ] **Multi-Model Ensemble**: Combine local + cloud for best results
- [ ] **Streaming Responses**: Real-time recommendation generation
- [ ] **Model Caching**: Cache common optimization patterns locally

---

## 10. FAQ

**Q: Can I use OptiSchema without any LLM?**  
A: Yes, basic index recommendations work without AI. AI enhances quality.

**Q: Which model is best for my use case?**  
A: 
- **Privacy-first**: SQLCoder (Ollama)
- **Best quality**: GPT-4 (Azure OpenAI)
- **Best cost**: Gemini Flash

**Q: How much does it cost to run locally?**  
A: Free (after hardware). A 13B model uses ~8GB RAM.

**Q: Can I switch models without code changes?**  
A: Yes, just change `LLM_PROVIDER` environment variable.

---

## Resources

- [Ollama Documentation](https://ollama.com)
- [SQLCoder Model](https://huggingface.co/defog/sqlcoder)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
- [AWS Bedrock](https://aws.amazon.com/bedrock/)
