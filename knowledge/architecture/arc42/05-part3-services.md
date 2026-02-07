# 5.4 Business Layer (Services)

## 5.4.1 Layer Overview
The Business Layer (Services) implements the core domain logic of the **uvz** system.  It sits between the **Presentation Layer** (Angular front‑end) and the **Data Access Layer** (repositories, JPA entities).  Services are **stateless** Spring beans that orchestrate use‑cases, enforce business rules, and coordinate transactions across bounded contexts.  Each service belongs to a bounded context (e.g. *DeedEntry*, *Archive*, *NumberManagement*) and is packaged in a dedicated module, following the **Domain‑Driven Design** principle of **separation of concerns**.

Key characteristics:
- **Transactional boundaries** are defined at the service level using `@Transactional`.
- Services expose **application‑level APIs** (Java interfaces) that are consumed by controllers, other services, or external REST endpoints.
- They depend on **repositories** for persistence and may publish **domain events** for asynchronous processing.
- All services are registered as Spring `@Service` beans and are part of the `container.backend` runtime container.

## 5.4.2 Service Inventory
| # | Service | Package (module) | Description |
|---|-------------------------------|----------------------------------------------|-------------|
" +
  "1 | ActionServiceImpl | de.bnotk.uvz.module.action.logic.impl | |
" +
  "2 | ActionWorkerService | de.bnotk.uvz.module.action.logic.impl | |
" +
  "3 | HealthCheck | de.bnotk.uvz.module.adapters.actuator.service | |
" +
  "4 | ArchiveManagerServiceImpl | de.bnotk.uvz.module.adapters.archivemanager.logic.impl | |
" +
  "5 | MockKmService | de.bnotk.uvz.module.adapters.km.impl.mock | |
" +
  "6 | XnpKmServiceImpl | de.bnotk.uvz.module.adapters.km.impl.xnp | |
" +
  "7 | KeyManagerServiceImpl | de.bnotk.uvz.module.adapters.km.logic.impl | |
" +
  "8 | WaWiServiceImpl | de.bnotk.uvz.module.adapters.wawi.impl | |
" +
  "9 | ArchivingOperationSignerImpl | de.bnotk.uvz.module.archive.logic.impl | |
" +
  "10 | ArchivingServiceImpl | de.bnotk.uvz.module.archive.logic.impl | |
" +
  "11 | DeedEntryConnectionDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "12 | DeedEntryLogsDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "13 | DocumentMetaDataCustomDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "14 | HandoverDataSetDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "15 | ApplyCorrectionNoteService | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "16 | BusinessPurposeServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "17 | CorrectionNoteService | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "18 | DeedEntryConnectionServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "19 | DeedEntryLogServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "20 | DeedEntryServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "21 | DeedRegistryServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "22 | DeedTypeServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "23 | DeedWaWiOrchestratorServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "24 | DeedWaWiServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "25 | DocumentMetaDataServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "26 | HandoverDataSetServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "27 | SignatureFolderServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "28 | ReportServiceImpl | de.bnotk.uvz.module.deedreports.logic.impl | |
" +
  "29 | JobServiceImpl | de.bnotk.uvz.module.job.logic.impl | |
" +
  "30 | NumberManagementServiceImpl | de.bnotk.uvz.module.numbermanagement.logic.impl | |
" +
  "31 | OfficialActivityMetaDataServiceImpl | de.bnotk.uvz.module.officialactivity.logic.impl | |
" +
  "32 | ReportMetadataServiceImpl | de.bnotk.uvz.module.reportmetadata.logic.impl | |
" +
  "33 | TaskServiceImpl | de.bnotk.uvz.module.task.logic.impl | |
" +
  "34 | DocumentMetadataWorkService | de.bnotk.uvz.module.work.logic | |
" +
  "35 | WorkServiceProviderImpl | de.bnotk.uvz.module.work.logic | |
" +
  "36 | ChangeDocumentWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "37 | DeletionWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "38 | SignatureWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "39 | SubmissionWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "40 | WorkflowServiceImpl | de.bnotk.uvz.module.workflow.logic.impl | |
" +
  "41 | ReencryptionWorkflowStateMachine | de.bnotk.uvz.module.logic.impl.state | |
" +
  "42 | WorkflowStateMachineProvider | de.bnotk.uvz.module.logic.impl.state | |
" +
  "43 | ActivateIfUserAuthorized | de.bnotk.uvz.module.frontend.authorization | |
" +
  "44 | WorkflowModuleMockService | de.bnotk.uvz.module.frontend.services_workflow.rest_mock | |
" +
  "45 | LogData | de.bnotk.uvz.module.frontend.adapters.xnp | |
" +
  "46 | ActionBaseService | de.bnotk.uvz.module.frontend.services.action.api.generated | |
" +
  "47 | ReencryptionFinalizationConfirmService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.finalization.confirm | |
" +
  "48 | DomainWorkflowService | de.bnotk.uvz.module.frontend.services.workflow.rest.domain | |
" +
  "49 | ImportHandlerServiceVersion1Dot6Dot1 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_6_1.handler | |
" +
  "50 | ImportHandlerServiceVersion1Dot4Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_4_0.handler | |
" +
  "51 | FieldValidationService | de.bnotk.uvz.module.frontend.forms.field-validation-service | |
" +
  "52 | DeedRegistryBaseService | de.bnotk.uvz.module.frontend.services.deed-registry.api.generated | |
" +
  "53 | ApplicationInitializerService | de.bnotk.uvz.module.frontend.core | |
" +
  "54 | WorkflowDeletionService | de.bnotk.uvz.module.frontend.workflow.services.workflow.deletion | |
" +
  "55 | ReencryptionFinalizationDoneService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.finalization.done | |
" +
  "56 | NotaryOfficialTitleStaticMapperService | de.bnotk.uvz.module.frontend.authentication.xnp.services | |
" +
  "57 | TaskApiConfiguration | de.bnotk.uvz.module.frontend.services.workflow.rest.api.generated | |
" +
  "58 | AsyncDocumentHelperService | de.bnotk.uvz.module.frontend.components.deed-form-page.services | |
" +
  "59 | ButtonDeactivationService | de.bnotk.uvz.module.frontend.services | |
" +
  "60 | CustomDatepickerParserFormatter | de.bnotk.uvz.module.frontend.page.custom-datepicker | |
" +
  "61 | WorkflowArchiveJobService | de.bnotk.uvz.module.frontend.workflow.services.workflow.archive | |
" +
  "62 | GlobalArchivingHelperService | de.bnotk.uvz.module.frontend.deed-entry.services.archiving | |
" +
  "63 | ReencryptionConfirmService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.confirm | |
" +
  "64 | ReportMetadataService | de.bnotk.uvz.module.frontend.report-metadata.services | |
" +
  "65 | IssueCopyDocumentHelper | de.bnotk.uvz.module.frontend.generic-modal-dialogs.issue-copy-document-modal.dialog | |
" +
  "66 | ImportHandlerServiceVersion1Dot6Dot2 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_6_2.handler | |
" +
  "67 | ImportHandlerServiceVersion1Dot3Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_3_0.handler | |
" +
  "68 | WorkflowReencryptionService | de.bnotk.uvz.module.frontend.workflow.services.workflow.reencryption | |
" +
  "69 | NswDeedImportService | de.bnotk.uvz.module.frontend.deed-import.services.nsw-deed-import | |
" +
  "70 | DeedEntryPageManagerService | de.bnotk.uvz.module.frontend.deed-entry.services.page-manager | |
" +
  "71 | DeedRegistryApiConfiguration | de.bnotk.uvz.module.frontend.services.deed-registry.api.generated | |
" +
  "72 | DocumentCopyService | de.bnotk.uvz.module.frontend.deed-entry.services.document-copy | |
" +
  "73 | WorkflowDeletionWorkService | de.bnotk.uvz.module.frontend.workflow.services.workflow.deletion | |
" +
  "74 | DeedRegistryService | de.bnotk.uvz.module.frontend.deed-registry.api.generated.services | |
" +
  "75 | DeedApprovalService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-approval | |
" +
  "76 | BusyIndicatorService | de.bnotk.uvz.module.frontend.page.busy-indicator.services | |
" +
  "77 | GlobalErrorHandlerService | de.bnotk.uvz.module.frontend.error-handling | |
" +
  "78 | WorkflowArchiveWorkService | de.bnotk.uvz.module.frontend.workflow.services.workflow.archive | |
" +
  "79 | WorkflowChangeAoidService | de.bnotk.uvz.module.frontend.workflow.services.workflow.change-aoid | |
" +
  "80 | WorkflowFinalizeReencryptionWorkService | de.bnotk.uvz.module.frontend.services.workflow.reencryption.job.finalize-reencryption | |
" +
  "81 | DocumentMetaDataService | de.bnotk.uvz.module.frontend.document-metadata.api-generated.services | |
" +
  "82 | DocumentHelperService | de.bnotk.uvz.module.frontend.tabs.document-data-tab.services | |
" +
  "83 | DocumentArchivingRestService | de.bnotk.uvz.module.frontend.deed-entry.services.archiving | |
" +
  "84 | TypeaheadFilterService | de.bnotk.uvz.module.frontend.typeahead.services.typeahead-filter | |
" +
  "85 | MockArchivingRetrievalHelperService | de.bnotk.uvz.module.frontend.deed-entry.services.archiving | |
" +
  "86 | ReportMetadataRestService | de.bnotk.uvz.module.frontend.report-metadata.services | |
" +
  "87 | BusinessPurposeRestService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-entry | |
" +
  "88 | UserContextPermissionCheckService | de.bnotk.uvz.module.frontend.authorization.xnp.service | |
" +
  "89 | OfficialActivityMetadataService | de.bnotk.uvz.module.frontend.deed-entry.services.official-activity-metadata | |
" +
  "90 | ImportHandlerServiceVersion1Dot6Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_6_0.handler | |
" +
  "91 | ReEncryptionHelperService | de.bnotk.uvz.module.frontend.components.deed-successor-page.services | |
" +
  "92 | ImportHandlerServiceVersion1Dot5Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_5_0.handler | |
" +
  "93 | ActionDomainService | de.bnotk.uvz.module.frontend.action.services.action | |
" +
  "94 | ArchivingService | de.bnotk.uvz.module.frontend.adapters.archiving | |
" +
  "95 | JobReencryptionService | de.bnotk.uvz.module.frontend.services.workflow.reencryption.job.reencryption | |
" +
  "96 | TokenDataMapperService | de.bnotk.uvz.module.frontend.token-bar | |
" +
  "97 | ReencryptionBaseService | de.bnotk.uvz.module.frontend.reencryption.xnp.api-generated | |
" +
  "98 | WorkflowReencryptionTaskService | de.bnotk.uvz.module.frontend.services.workflow.reencryption.job.workflow | |
" +
  "99 | KeepUnsavedBusinessObjectsService | de.bnotk.uvz.module.frontend.components.deed-form-page.services | |
" +
  "100 | TooltipConfigService | de.bnotk.uvz.module.frontend.tooltip-table | |
" +
  "101 | DocumentMetadataBaseService | de.bnotk.uvz.module.frontend.services.document-metadata.api-generated | |
" +
  "102 | SettingsInitializer | de.bnotk.uvz.module.frontend.core | |
" +
  "103 | ShortcutService | de.bnotk.uvz.module.frontend.components.deed-form-page.services | |
" +
  "104 | GetDeedEntryLockService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-entry | |
" +
  "105 | ReencryptionFinalizationHasErrorsRetryService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.finalization.has-errors-retry | |
" +
  "106 | ModalService | de.bnotk.uvz.module.frontend.services.modal | |
" +
  "107 | ReportService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-reports | |
