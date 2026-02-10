## Security Policy

### 🔒 Local-First Design

**OptiSchema Slim** is designed as a **local-only tool** that runs entirely on your machine via Docker. Your database credentials, queries, and AI API keys **never leave your localhost**.

### 🔑 API Key Management (Best Practices)

**For Local LLM (Ollama):**
- No API keys required. Runs entirely offline.
- Recommended for maximum privacy and security.

**For Cloud LLMs (OpenAI, Gemini, DeepSeek):**
1. **Use Environment Variables**: Store keys in your `.env` file (never commit this to git!)
2. **Rotate Keys Regularly**: Consider using read-only or rate-limited API keys.
3. **File Permissions**: Ensure your `.env` file has restricted permissions:
   ```bash
   chmod 600 .env
   ```

**Storage Details:**
- API keys entered via the Settings UI are stored in `backend/optischema.db` (SQLite).
- This database resides in your local Docker volume.
- **Not encrypted at rest** (acceptable for single-user local deployments).
- For multi-user or shared environments, consider using Docker Secrets or Kubernetes ConfigMaps.

### 🐛 Reporting Security Issues

If you believe you have discovered a security vulnerability in OptiSchema, please **do not** open a public GitHub issue.

Instead, responsibly disclose it by:
- Going to the **Security** tab of this repository
- Clicking **"Report a vulnerability"**

Please provide as much detail as possible in your private report, including:
- A clear description of the issue
- Steps to reproduce (a minimal reproducible example is greatly appreciated)
- Potential impact and any proof-of-concept if available

This allows us to investigate and address the issue quickly and safely before public disclosure.

Thank you for helping keep OptiSchema secure!
