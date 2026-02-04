**File:** `c4/c4-container.md`

# UVZ System – C4 Container Diagram (Level 2)

## 1. Overview  

The UVZ System is composed of five deployable containers that run together (orchestrated via Docker Compose).  
Each container is a distinct runtime unit with its own technology stack and responsibilities.

| Container (ID) | Type | Technology (as recorded in *architecture_facts.json*) | Main Responsibility |
|----------------|------|------------------------------------------------------|----------------------|
| **backend** | application | Spring Boot (Java, Gradle) | Hosts the public **REST API**, implements the business‑logic layer (controllers, services, repositories), integrates with XNP and other external services, and accesses the database. |
| **frontend** | application | Angular (TypeScript, npm) | Provides the single‑page UI (SPA) that users interact with; consumes the backend REST API. |
| **postgres** | database | PostgreSQL | Persists all domain entities (deed entries, hand‑over data, numbers, workflow state, etc.). |
| **broker_app** | application | pact‑broker | Stores and serves consumer‑provider contract definitions for contract‑testing pipelines (CI/CD). |
| **docker** | application | Ubuntu (base OS) | Docker‑Compose host that starts the other four containers; represents the underlying runtime environment. |

### External System (outside the container set)

| System | Type | Technology | Interaction |
|--------|------|------------|-------------|
| **XNP Platform** | external API | REST/HTTPS | Called by the **backend** for authentication, document handling, notifications and other integration points. |

## 2. Container Inter‑connections  

| Source → Target | Communication protocol / transport | Purpose |
|-----------------|-----------------------------------|---------|
| **frontend → backend** | **HTTPS / REST (JSON)** | UI calls the public API (e.g., `/uvz/v1/deedentries`). |
| **backend → postgres** | **JDBC / SQL** | Persistence of domain data via Spring Data JPA. |
| **backend → broker_app** | **HTTP** | Publishes / retrieves Pact contracts during CI/CD. |
| **backend → XNP Platform** | **HTTPS / REST (JSON)** | Integration with external XNP services. |
| **docker → backend** | **Docker‑Compose** | Starts the backend container. |
| **docker → frontend** | **Docker‑Compose** | Starts the SPA container. |
| **docker → postgres** | **Docker‑Compose** | Starts the PostgreSQL container. |
| **docker → broker_app** | **Docker‑Compose** | Starts the Pact‑Broker container. |

## 3. Diagram  

The visual container diagram is stored in **`c4/c4-container.drawio`**.  
It shows the five containers, the external XNP Platform, and the communication links listed above, with each container labelled by its exact name and technology.

---  

*All container names, types and technologies are taken directly from **architecture_facts.json**; the architectural style (modular monolith) and quality context are taken from **analyzed_architecture.json**.*