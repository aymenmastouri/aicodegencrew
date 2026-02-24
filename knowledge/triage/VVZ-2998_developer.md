# Developer Brief: VVZ-2998

## Root Cause Hypothesis

The import routine stores participants via the `check` logic in `ActionServiceImpl`. During the validation step the code incorrectly filters out participants that do not meet a strict criteria (e.g., missing metadata fields). As a result the participant list is cleared, the VM is marked as faulty and the UI no longer shows the imported parties. The DTOs `NotaryChamberServiceDto`, `NotaryChamberServiceShortDto` and `NotaryMetaDataFieldDto` are involved in mapping the JSON data, and the `BasicAction` class may also apply the same validation when the edit view is opened.

## Affected Files

- `backend/src/main/java/de/bnotk/vvz/module/action/logic/impl/ActionServiceImpl.java`
- `backend/src/main/java/de/bnotk/vvz/module/action/logic/impl/BasicAction.java`
- `backend/src/main/java/de/bnotk/vvz/module/adapters/metadataresolver/impl/xnp/model/NotaryChamberServiceDto.java`
- `backend/src/main/java/de/bnotk/vvz/module/adapters/metadataresolver/impl/xnp/model/NotaryChamberServiceShortDto.java`
- `backend/src/main/java/de/bnotk/vvz/module/adapters/metadataresolver/impl/xnp/model/NotaryMetaDataFieldDto.java`

## Affected Components

- ActionServiceImpl (service)
- BasicAction (service)
- NotaryChamberServiceDto (data model)
- NotaryChamberServiceShortDto (data model)
- NotaryMetaDataFieldDto (data model)

## Action Steps

- 1. Review the `check` method in `ActionServiceImpl.java` – identify any filtering that removes participants without required metadata and adjust the logic to keep valid participants even if optional fields are missing.
- 2. Verify the mapping code in `NotaryChamberServiceDto.java`, `NotaryChamberServiceShortDto.java` and `NotaryMetaDataFieldDto.java` – ensure all participant identifiers from the JSON are persisted correctly.
- 3. Update `BasicAction.java` if it re‑invokes the same validation when opening the edit view; make it tolerant to already‑imported participants.
- 4. Add unit tests that import a JSON file containing participants (e.g., "Sparkasse") and then open the edit view, asserting that the participants remain present and the VM is not marked as faulty.
- 5. Add an integration test that performs the full workflow described in the ticket (import → open → edit → save) and verifies no data loss.
- 6. Deploy the fix to a test environment and confirm that the issue no longer occurs with the problematic JSON file.

## Test Strategy

Create a dedicated test case in the backend test suite that loads the provided JSON (the one that reproduces the issue), runs the import service, opens the edit view via the action service, and asserts that the participant list contains the expected organisations. Include negative tests with the sample‑amount‑of‑custody‑max.json to ensure existing behaviour is unchanged.

## Architecture Notes

The participant validation is part of the core action service; any change should respect the overall validation contract for VVs. Consider extracting the participant‑filtering logic into a reusable validator component to avoid duplication between import and edit paths.