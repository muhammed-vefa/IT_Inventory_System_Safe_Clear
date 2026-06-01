# DevOps Final Prompt Pack & System Governance Documentation

## 🏛️ System Architecture
The system follows a deterministic **Single Decision Authority** model managed by the `SystemGovernance` layer.

### 🛡️ Hierarchical Decision Matrix
1. **Circuit Breaker:** Stops all automation if stability fails.
2. **Safe Mode:** Read-only state for critical risk (>80 score).
3. **Self-Healing:** Targeted repairs for medium risk (40-80 score).
4. **Monitoring:** Passive observation for healthy states.

## 🚀 Deployment Pipeline (Hardened)
The `core_pipeline.py` manages a secure, atomic-ish deployment flow:
`Git Pull -> Staging -> Validation -> Security Scan -> Backup -> Atomic Swap -> Health Check`.

## 🧠 Schema Normalization
`schema_mapper.py` ensures field consistency across the stack:
- `arizali` -> `is_faulty`
- `is_deleted` -> `is_archived`

## 🔐 Administrative Operations
Admin panel is restricted to 4 core functions:
1. System Health Analysis
2. GitHub Sync & Deploy
3. Data Archiving
4. Last Stable Restore

## ⚠️ Emergency Procedures
- **Kill-Switch:** Set `automation_enabled: false` in `config.json`.
- **Manual Rollback:** Trigger `run_rollback()` via `rollback.py`.
- **Safe Mode Exit:** Manual override or wait for 120s of stability.
