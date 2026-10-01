# ADR 0001: Medallion layers and the ERP boundary
Status: accepted. **Context:** Business Central, HubSpot and others each hold part of the truth; reporting and AI need one consistent view without turning any operational system into the data platform.
**Decision:** Raw (bronze) -> typed/conformed (silver) -> governed models (gold). Operational systems remain writers of their own domains; the platform only reads and publishes governed copies.
**Consequences:** Replayable history, clear ownership, no analytics load on the ERP. Cost: storage and one more moving part, justified by auditability.
