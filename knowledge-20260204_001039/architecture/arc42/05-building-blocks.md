# 05 – Building Block View

## 5.1 Whitebox Overall System (Level 1)

The **uvz** system is realised as five Docker containers that together constitute the complete runtime environment.  The containers are defined in a single `docker‑compose.yml` file, which orchestrates their start‑up order, network connectivity and resource limits.  All containers run on an Ubuntu‑based host image, guaranteeing a uniform OS layer.

| Container (exact name) | Technology / Image | Primary Role |
|------------------------|--------------------|--------------|
| **backend** | Spring Boot (Java) – `backend` image built from the provided `Dockerfile` | Hosts the core business logic, REST controllers, services, repositories and all XNP integration adapters. Exposes the public API (`/uvz/v1/...`) and Actuator health endpoints. |
| **frontend** | Angular (TypeScript) –