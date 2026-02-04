# C4 Container Diagram – UVZ System

## Overview
The UVZ System is realised as a set of five deployable units (containers) that together provide a **Deed‑Entry Management Platform**. The containers are packaged as Docker images and run on an Ubuntu‑based host.

## Containers (Level 2)

| Container ID | Name / Role | Technology | Evidence | Primary Responsibility |
|--------------|-------------|------------|----------|------------------------|
| **backend** | Spring Boot application (modular monolith) | Spring Boot (Java) | `ev_container_0001` (build.gradle) | Implements all business capabilities (Deed Management, Number Management, Workflow, XNP integration, infrastructure) and exposes a REST API (30 endpoints). |
| **frontend** | Angular single‑page application | Angular (TypeScript) | `ev_container_0002` (angular.json) | Provides the web UI for end‑users; communicates with the backend via HTTP/REST. |
| **docker** | Ubuntu OS container used as the runtime host | Ubuntu 20.04 | `ev_docker_0001` (Dockerfile) | Hosts the other containers; provides the OS layer for container orchestration. |
| **postgres** | PostgreSQL relational database | PostgreSQL | `ev_compose_0002` (docker‑compose.yml) | Persists domain entities such as DeedEntry, Handover, Successor, NumberManagement, Workflow, etc. |
| **broker_app** | Pact Broker for contract testing | pact‑broker | `ev_compose_0003` (docker‑compose.yml) | Stores consumer‑provider contracts; accessed by the backend during contract‑testing pipelines. |

## Inter‑Container Relationships

| Source | Target | Communication / Protocol | Description |
|--------|--------|--------------------------|-------------|
| **docker** → **backend** | runs on | Docker container runtime | Ubuntu host provides the execution environment for the Spring Boot app. |
| **docker** → **frontend** | runs on | Docker container runtime | Ubuntu host provides the execution environment for the Angular SPA (served via a web server inside the container). |
| **docker** → **postgres** | runs on | Docker container runtime | Ubuntu host provides the execution environment for the PostgreSQL database. |
| **docker** → **broker_app** | runs on | Docker container runtime | Ubuntu host provides the execution environment for the Pact Broker. |
| **frontend** → **backend** | HTTP/REST (JSON) | Web UI calls backend API (`/uvz/v1/**`). |
| **backend** → **postgres** | JDBC / SQL | Persistence of domain entities. |
| **backend** → **broker_app** | HTTP | Retrieval of contract definitions for Pact‑based tests. |

## Diagram
The container diagram is available as a Draw.io file:

**`c4/c4-container.drawio`**

It visualises:

* The **docker** host container encompassing all runtime containers.
* The **frontend** and **backend** communicating via HTTP/REST.
* The **backend** interacting with **postgres** (JDBC) and **broker_app** (HTTP contracts).

--- 

*All names, technologies and evidence references are taken verbatim from **architecture_facts.json**. The architectural style (Modular Monolith) and quality context are derived from **analyzed_architecture.json**.*