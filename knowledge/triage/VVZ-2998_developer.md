# Developer Context: VVZ-2998

## Big Picture

The issue lives at the intersection of the import pipeline (backend Spring Boot services that parse the JSON into domain DTOs), the persistence layer (repositories storing participants, bookings and custody‑mass entities), and the UI layer (Angular components for the "Beteiligte" and "Buchungen" tabs). The import service creates DTOs (e.g., NotaryChamberServiceDto) which are handed to the ActionServiceImpl for validation and saving. The UI then reads the persisted state via REST endpoints. A mismatch between what is persisted and what the UI displays causes the observed loss of data.

## Scope Boundary

IN SCOPE: JSON import parsing, DTO‑to‑entity mapping, validation logic in ActionServiceImpl/BasicAction, repository persistence of Participant and Booking entities, and the Angular components that render the participants and bookings tabs. OUT OF SCOPE: authentication, PKI handling, unrelated modules such as metadata resolver, other business processes not touching the import or edit flow, and front‑end styling.

## Classification Assessment

Evidence FOR bug:
- The observed behaviour (participants disappearing after edit) directly violates the functional requirement that all imported participants must remain visible and linked to bookings.
- The test steps consistently reproduce the issue with the provided JSON file, while a different sample file does NOT trigger it, indicating a data‑specific processing defect.
- The system incorrectly allows a VM flagged as faulty to be saved, contradicting the expected rule that such VMs must be rejected.
- Deterministic findings label the issue as a bug with 0.99 confidence and highlight the ActionServiceImpl component, which is responsible for validation and persistence.

Evidence AGAINST bug:
- No explicit error logs or stack traces are provided; the problem could stem from user actions (e.g., not confirming a save) or from missing required fields in the JSON.
- The specification PDF is not parsed, so we cannot confirm whether the current behaviour might be an undocumented edge case.
- The UI may be caching stale data, which would be a front‑end refresh issue rather than a backend bug.

Reference to supplementary docs:
- The requirement document (VVZ‑Q‑08 Notarsoftware Import) is mentioned but not readable in the provided excerpt; however, the expected outcome described in the issue aligns with typical import specifications.

Overall assessment: The preponderance of evidence points to a defect in the import‑to‑persistence‑to‑UI flow rather than user error or a missing feature. (Confirmed bug — 95%)

## Affected Components

- Import Service (backend)
- ActionServiceImpl / BasicAction (service layer)
- Participant & Booking Repositories (persistence)
- Angular Participants Tab Component (frontend)
- Angular Bookings Tab Component (frontend)

## Relevant Dimensions

**Technologies:** Backend runs on Java 17 with Spring Boot; frontend uses Angular 18. DTO mapping and validation are performed in Java, while the UI relies on RxJS streams to display data.

**Patterns:** The system follows a Service‑Repository pattern with DTOs for transport. Validation logic is likely implemented via Spring validation annotations and custom checks in ActionServiceImpl.

**Conventions:** Error handling is centralized in DefaultExceptionHandler. The observed missing‑entity symptom may stem from a validation exception being swallowed or an incomplete transaction rollback.


## Architecture Notes

Pay attention to transaction boundaries in the import service – a partial commit could leave participant records orphaned. Validation rules that mark a VM as "faulty" must abort the whole save operation. UI components should refresh their data after a successful edit to avoid stale views.