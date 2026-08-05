# OniRoute CLI Experience Specification (Phase P6.D1)

## 1. Supported Command Syntaxes

OniRoute v1.2 supports zero-configuration natural language CLI commands:

```bash
# Build web applications and websites
oniroute build a real estate website

# Create full-stack apps and SaaS products
oniroute create SaaS CRM

# Fix bugs or resolution requests
oniroute fix database connection pool leak

# Refactor components
oniroute refactor extract auth middleware

# Migrate frameworks or versions
oniroute migrate upgrade to Next.js 14 App Router

# Review codebase or quality results
oniroute review
```

---

## 2. Rich Console Display

During and after execution, the CLI displays:
1. **Mission & Intelligence Summary**: Mission ID, Primary Intent, Intent Confidence Score, End-to-End Latency.
2. **Detected Technology Stack & Smart Defaults**: Inferred project type, tech stack, database, authentication, deployment target, etc.
3. **Autonomous Engineering & Release Summary**: Count of created/modified files, quality score (0-10), production readiness status, and SHA-256 release certification ID.
