"""
Architecture Facts Pipeline (Phase 1)

Deterministic extraction of architecture facts from source code.
NO LLM. NO interpretation. Only facts + evidence.

This is the SINGLE SOURCE OF TRUTH for architecture.
Everything not in architecture_facts.json must not be written by Phase 2.

Usage:
    from aicodegencrew.pipelines.architecture_facts import ArchitectureFactsPipeline
    
    pipeline = ArchitectureFactsPipeline(repo_path="/path/to/repo")
    result = pipeline.kickoff()
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from .container_detector import ContainerDetector
from .spring_collector import SpringCollector
from .angular_collector import AngularCollector
from .infra_collector import InfraCollector
from .database_collector import DatabaseCollector
from .architecture_style_collector import ArchitectureStyleCollector
from .integration_collector import IntegrationCollector
from .endpoint_flow_builder import EndpointFlowBuilder
from .writer import FactsWriter
from .base_collector import CollectedEvidence, CollectedComponent, CollectedInterface, CollectedRelation
from ...shared.utils.logger import logger


class ArchitectureFactsPipeline:
    """
    Phase 1: Architecture Facts Pipeline
    
    Deterministic extraction - NO LLM!
    
    Outputs:
    - knowledge/architecture/architecture_facts.json
    - knowledge/architecture/evidence_map.json
    
    What gets extracted:
    - Containers (backend, frontend, database, infrastructure)
    - Components (@RestController, @Service, @Repository, @Component, etc.)
    - Interfaces (REST endpoints, routes)
    - Relations (dependency injection, imports)
    
    What does NOT get extracted:
    - C4 names like "Application Layer"
    - Responsibilities
    - Architecture decisions
    - Flows
    - Summaries
    """
    
    def __init__(
        self,
        repo_path: str,
        output_dir: Optional[str] = None,
    ):
        """
        Initialize the Architecture Facts Pipeline.
        
        Args:
            repo_path: Path to the repository to analyze
            output_dir: Output directory (defaults to knowledge/architecture)
        """
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = Path(output_dir) if output_dir else Path("knowledge/architecture")
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")
        
        logger.info(f"[Phase1] ArchitectureFactsPipeline initialized")
        logger.info(f"[Phase1] Repository: {self.repo_path}")
        logger.info(f"[Phase1] Output: {self.output_dir}")
    
    def _archive_and_clean_old_outputs(self) -> None:
        """Archive and clean old Phase 1 outputs before new run."""
        import shutil
        from datetime import datetime
        
        output_files = [
            "architecture_facts.json",
            "evidence_map.json",
        ]
        
        existing_files = [f for f in output_files if (self.output_dir / f).exists()]
        
        if existing_files:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_dir = self.output_dir / "archive" / f"run_{timestamp}"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            for filename in existing_files:
                src = self.output_dir / filename
                dst = archive_dir / filename
                shutil.copy2(src, dst)
                src.unlink()
                logger.info(f"   [ARCHIVED+DELETED] {filename}")
            
            logger.info(f"   [OK] {len(existing_files)} old files archived to: {archive_dir}")
        else:
            logger.info("   [OK] No old outputs to clean (first run)")
    
    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the Architecture Facts Pipeline.
        
        Args:
            inputs: Optional input parameters (for orchestrator compatibility)
        
        Returns:
            Dictionary with extraction results
        """
        logger.info("=" * 60)
        logger.info("[Phase1] Starting Architecture Facts Extraction")
        logger.info("[Phase1] Mode: DETERMINISTIC (no LLM)")
        logger.info("=" * 60)
        
        # Archive and clean old outputs first
        logger.info("[Phase1] Step 0: Archive and clean old outputs...")
        self._archive_and_clean_old_outputs()
        
        all_components: List[CollectedComponent] = []
        all_interfaces: List[CollectedInterface] = []
        all_relations: List[CollectedRelation] = []
        all_evidence: Dict[str, CollectedEvidence] = {}
        all_containers: List[Dict] = []
        
        try:
            # Step 1: Detect containers
            logger.info("\n[Phase1] Step 1: Detecting containers...")
            container_detector = ContainerDetector(self.repo_path)
            detected_containers, container_evidence = container_detector.detect()
            all_containers.extend(detected_containers)
            all_evidence.update(container_evidence)
            logger.info(f"[Phase1] Detected {len(detected_containers)} containers")
            
            # Step 2: Collect components based on detected technology
            logger.info("\n[Phase1] Step 2: Collecting components per detected technology...")
            for container in detected_containers:
                technology = container.get("technology", "")
                container_path = self.repo_path / container.get("root_path", ".")
                container_id = container["id"]
                
                # ============================================================
                # BACKEND TECHNOLOGIES (dynamically selected)
                # ============================================================
                if technology == "Spring Boot":
                    # Spring Boot / Java Backend
                    spring_collector = SpringCollector(
                        self.repo_path,
                        container_id=container_id,
                        java_root=container_path / "src" / "main" / "java" if (container_path / "src" / "main" / "java").exists() else None
                    )
                    components, interfaces, relations, evidence = spring_collector.collect()
                    all_components.extend(components)
                    all_interfaces.extend(interfaces)
                    all_relations.extend(relations)
                    all_evidence.update(evidence)
                    
                    # Extract backend metadata
                    backend_metadata = spring_collector.extract_backend_metadata()
                    if backend_metadata:
                        container["backend_metadata"] = backend_metadata
                        logger.info(f"[Phase1] {technology}: {len(backend_metadata.get('spring_profiles', []))} profiles")
                    
                    # Database scripts for this container
                    db_collector = DatabaseCollector(container_path, container_id=container_id)
                    db_components, db_interfaces, db_relations, db_evidence = db_collector.collect()
                    all_components.extend(db_components)
                    all_interfaces.extend(db_interfaces)
                    all_relations.extend(db_relations)
                    all_evidence.update(db_evidence)
                    if db_components:
                        logger.info(f"[Phase1] Found {len(db_components)} database components in {container_id}")
                    
                    # Architecture Styles for this container
                    arch_collector = ArchitectureStyleCollector(container_path, container_id=container_id)
                    arch_components, arch_interfaces, arch_relations, arch_evidence = arch_collector.collect()
                    all_components.extend(arch_components)
                    all_interfaces.extend(arch_interfaces)
                    all_relations.extend(arch_relations)
                    all_evidence.update(arch_evidence)
                    
                    # Integrations for this container
                    int_collector = IntegrationCollector(container_path, container_id=container_id)
                    int_components, int_interfaces, int_relations, int_evidence = int_collector.collect()
                    all_components.extend(int_components)
                    all_interfaces.extend(int_interfaces)
                    all_relations.extend(int_relations)
                    all_evidence.update(int_evidence)
                
                # TODO: Add QuarkusCollector when needed
                # elif technology == "Quarkus":
                #     quarkus_collector = QuarkusCollector(...)
                
                # TODO: Add NodeCollector when needed (Express, NestJS, Fastify)
                # elif technology == "Node.js":
                #     node_collector = NodeCollector(...)
                
                # TODO: Add DotNetCollector when needed
                # elif technology == ".NET":
                #     dotnet_collector = DotNetCollector(...)
                
                # TODO: Add PythonCollector when needed (Flask, Django, FastAPI)
                # elif technology == "Python":
                #     python_collector = PythonCollector(...)
                
                # ============================================================
                # FRONTEND TECHNOLOGIES (dynamically selected)
                # ============================================================
                elif technology == "Angular":
                    angular_collector = AngularCollector(
                        self.repo_path,
                        container_id=container_id,
                        angular_root=container_path / "src" / "app" if (container_path / "src" / "app").exists() else None
                    )
                    components, interfaces, relations, evidence = angular_collector.collect()
                    all_components.extend(components)
                    all_interfaces.extend(interfaces)
                    all_relations.extend(relations)
                    all_evidence.update(evidence)
                    
                    # Extract frontend metadata
                    frontend_metadata = angular_collector.extract_frontend_metadata()
                    if frontend_metadata:
                        container["frontend_metadata"] = frontend_metadata
                        logger.info(f"[Phase1] {technology}: version={frontend_metadata.get('angular_version')}, UI={frontend_metadata.get('ui_library')}")
                
                # TODO: Add ReactCollector when needed
                # elif technology == "React":
                #     react_collector = ReactCollector(...)
                
                # TODO: Add VueCollector when needed
                # elif technology == "Vue.js":
                #     vue_collector = VueCollector(...)
                
                else:
                    logger.info(f"[Phase1] No specific collector for technology: {technology} (container: {container_id})")
            
            # Step 3: Collect infrastructure facts
            logger.info("\n[Phase1] Step 3: Collecting infrastructure facts...")
            infra_collector = InfraCollector(self.repo_path, container_id="infrastructure")
            infra_components, infra_interfaces, infra_relations, infra_evidence = infra_collector.collect()
            all_components.extend(infra_components)
            all_interfaces.extend(infra_interfaces)
            all_relations.extend(infra_relations)
            all_evidence.update(infra_evidence)
            
            # Merge infrastructure-detected containers
            infra_containers = infra_collector.get_detected_containers()
            for ic in infra_containers:
                # Check if container already exists
                existing_ids = [c["id"] for c in all_containers]
                if ic["id"] not in existing_ids:
                    all_containers.append(ic)
            
            # Step 4: Build endpoint flows (runtime workflow evidence)
            logger.info("\n[Phase1] Step 4: Building endpoint flows...")
            flow_builder = EndpointFlowBuilder(
                components=all_components,
                interfaces=all_interfaces,
                relations=all_relations,
                evidence=all_evidence,
            )
            endpoint_flows = flow_builder.build_flows()
            logger.info(f"[Phase1] Built {len(endpoint_flows)} endpoint flows")

            # Step 5: Write output
            logger.info("\n[Phase1] Step 5: Writing output files...")
            writer = FactsWriter(self.output_dir)
            result = writer.write(
                system_name=self.repo_path.name,
                containers=all_containers,
                components=all_components,
                interfaces=all_interfaces,
                relations=all_relations,
                endpoint_flows=endpoint_flows,
                evidence=all_evidence,
            )
            
            logger.info("\n" + "=" * 60)
            logger.info("[Phase1] Architecture Facts Extraction COMPLETE")
            logger.info("=" * 60)
            logger.info(f"[Phase1] Containers: {result['statistics']['containers']}")
            logger.info(f"[Phase1] Components: {result['statistics']['components']}")
            logger.info(f"[Phase1] Interfaces: {result['statistics']['interfaces']}")
            logger.info(f"[Phase1] Relations: {result['statistics']['relations']}")
            logger.info(f"[Phase1] Evidence items: {result['statistics']['evidence_items']}")
            
            return {
                "phase": "phase1_architecture_facts",
                "status": "success",
                "facts_path": result["facts_path"],
                "evidence_path": result["evidence_path"],
                "statistics": result["statistics"],
            }
            
        except Exception as e:
            logger.error(f"[Phase1] Error: {e}", exc_info=True)
            return {
                "phase": "phase1_architecture_facts",
                "status": "failed",
                "error": str(e),
            }
