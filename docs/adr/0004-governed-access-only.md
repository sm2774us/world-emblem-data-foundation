# ADR 0004: Governed access only
Status: accepted. **Decision:** Consumers (Power BI, internal apps, AI agents) use gold via semantic model, API or allow-listed tools. RBAC and masking come from `policies.yaml`; every read is written to a hash-chained audit log. Agents get parameterised tools, never SQL.
**Consequences:** Direct production grants can be revoked; AI usage is monitored and attributable.
