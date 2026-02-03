"""Pydantic schemas for architecture analysis JSON output.

This schema defines the MASTER BLUEPRINT for all downstream phases:
- Phase 2: Architecture Synthesis (needs complete facts for C4 + arc42)
- Phase 3: Review & Consistency (validates synthesis quality)
- Phase 4: Development (needs exact paths, patterns, structures)

The output MUST be precise, complete, and deterministic so that
synthesis agents know EXACTLY what architecture exists.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Evidence supporting an analysis claim."""
    file_path: str = Field(..., description="Relative path to the source file")
    chunk_id: str = Field(..., description="Unique identifier of the text chunk")
    snippet: str = Field(..., description="Relevant text snippet from the source (5-20 lines)")


class Technology(BaseModel):
    """Technology identified in the codebase."""
    name: str = Field(..., description="Technology name (e.g., Spring Boot, Angular)")
    version: Optional[str] = Field(None, description="Version if detectable")
    category: str = Field(..., description="Category: backend, frontend, database, infrastructure, etc.")
    evidence: List[Evidence] = Field(..., description="Supporting evidence")


# =============================================================================
# CODE GENERATION STRUCTURES - Critical for downstream phases
# =============================================================================

class SourceDirectory(BaseModel):
    """Source directory structure for code generation."""
    path: str = Field(..., description="Relative path to directory")
    language: str = Field(..., description="Primary language: java, typescript, python, etc.")
    package_pattern: str = Field(default="", description="Package naming pattern (e.g., com.company.app.module.*)")
    file_count: int = Field(default=0, description="Number of source files")


class ApiEndpoint(BaseModel):
    """REST API endpoint for code generation context."""
    method: str = Field(..., description="HTTP method: GET, POST, PUT, DELETE, PATCH")
    path: str = Field(..., description="URL path (e.g., /api/v1/users/{id})")
    controller_class: str = Field(..., description="Controller class name")
    controller_file: str = Field(..., description="Relative path to controller file")
    request_dto: Optional[str] = Field(None, description="Request DTO class name")
    response_dto: Optional[str] = Field(None, description="Response DTO class name")
    evidence: List[Evidence] = Field(default_factory=list)


class ServiceClass(BaseModel):
    """Service layer class for code generation context."""
    name: str = Field(..., description="Class name (e.g., UserService)")
    file_path: str = Field(..., description="Relative path to file")
    interface_name: Optional[str] = Field(None, description="Interface name if exists")
    methods: List[str] = Field(default_factory=list, description="Public method names")
    dependencies: List[str] = Field(default_factory=list, description="Injected dependencies")


class EntityClass(BaseModel):
    """Entity/Model class for code generation context."""
    name: str = Field(..., description="Entity class name")
    file_path: str = Field(..., description="Relative path to file")
    table_name: Optional[str] = Field(None, description="Database table name")
    fields: List[Dict[str, str]] = Field(default_factory=list, description="Field definitions [{name, type, annotations}]")
    relationships: List[str] = Field(default_factory=list, description="Relationship annotations")


class ComponentClass(BaseModel):
    """Frontend component for code generation context."""
    name: str = Field(..., description="Component name")
    file_path: str = Field(..., description="Relative path to file")
    type: str = Field(..., description="Type: page, component, service, module, directive")
    template_file: Optional[str] = Field(None, description="Associated template file")
    style_file: Optional[str] = Field(None, description="Associated style file")


class CodingPattern(BaseModel):
    """Coding pattern discovered in the codebase - for consistent code gen."""
    name: str = Field(..., description="Pattern name (e.g., Repository Pattern, DTO Pattern)")
    description: str = Field(..., description="How this pattern is implemented")
    example_file: str = Field(..., description="Example file path showing the pattern")
    snippet: str = Field(..., description="Code example (10-30 lines)")


class Interface(BaseModel):
    """Interface/API definition."""
    name: str = Field(..., description="Interface name or endpoint")
    type: str = Field(..., description="Type: REST, GraphQL, gRPC, Kafka, etc.")
    description: str = Field(..., description="Interface description")
    evidence: List[Evidence] = Field(..., description="Supporting evidence")


class DataHint(BaseModel):
    """Hint about data structure or entity."""
    name: str = Field(..., description="Entity or table name")
    type: str = Field(..., description="Type: entity, table, collection, schema")
    description: str = Field(..., description="Data structure description")
    evidence: List[Evidence] = Field(..., description="Supporting evidence")


class DeploymentHint(BaseModel):
    """Deployment or infrastructure hint."""
    name: str = Field(..., description="Deployment component name")
    type: str = Field(..., description="Type: docker, kubernetes, helm, terraform")
    description: str = Field(..., description="Deployment description")
    evidence: List[Evidence] = Field(..., description="Supporting evidence")


class ProjectUnit(BaseModel):
    """A logical project unit (module, service, app) - CRITICAL for code gen."""
    name: str = Field(..., description="Unit name")
    type: str = Field(..., description="Type: backend-module, frontend-app, library, e2e-tests, deployment")
    root_path: str = Field(..., description="Relative root path of the unit")
    
    # Source structure for code generation
    source_dirs: List[SourceDirectory] = Field(default_factory=list, description="Source directories")
    
    detected_tech: List[str] = Field(default_factory=list, description="Detected technologies")
    interfaces: List[Interface] = Field(default_factory=list, description="Exposed interfaces")
    data_hints: List[DataHint] = Field(default_factory=list, description="Data structure hints")
    deployment_hints: List[DeploymentHint] = Field(default_factory=list, description="Deployment hints")
    evidence: List[Evidence] = Field(..., description="Evidence for unit detection")


class CodeGenContext(BaseModel):
    """Context specifically for code generation phases - THE BLUEPRINT."""
    
    # Backend structures
    api_endpoints: List[ApiEndpoint] = Field(default_factory=list, description="All REST endpoints discovered")
    service_classes: List[ServiceClass] = Field(default_factory=list, description="All service classes discovered")
    entity_classes: List[EntityClass] = Field(default_factory=list, description="All entity/model classes discovered")
    
    # Frontend structures
    components: List[ComponentClass] = Field(default_factory=list, description="All frontend components discovered")
    
    # Coding patterns for consistent generation
    patterns: List[CodingPattern] = Field(default_factory=list, description="Coding patterns to follow")
    
    # Package/namespace conventions
    backend_base_package: str = Field(default="", description="Base package for backend (e.g., com.company.app)")
    frontend_base_path: str = Field(default="", description="Base path for frontend (e.g., src/app)")
    
    # Naming conventions
    naming_conventions: Dict[str, str] = Field(default_factory=dict, description="Naming patterns discovered")


class ArchitectureAnalysis(BaseModel):
    """Complete architecture analysis output - MASTER BLUEPRINT for all phases."""
    repo_name: str = Field(..., description="Repository name")
    repo_path: str = Field(..., description="Repository path analyzed")
    analysis_timestamp: str = Field(..., description="Analysis timestamp ISO format")
    
    technologies: List[Technology] = Field(default_factory=list, description="All technologies found")
    project_units: List[ProjectUnit] = Field(default_factory=list, description="All project units/submodules")
    
    # NEW: Code generation context
    codegen_context: Optional[CodeGenContext] = Field(None, description="Context for code generation phases")
    
    summary: str = Field(..., description="High-level architecture summary")
    recommendations: List[str] = Field(default_factory=list, description="Architecture recommendations")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
