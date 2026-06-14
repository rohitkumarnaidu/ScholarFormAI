# Pipeline Processing System

<cite>
**Referenced Files in This Document**
- [orchestrator.py](file://backend/app/pipeline/orchestrator.py)
- [base.py](file://backend/app/pipeline/base.py)
- [pipeline_document.py](file://backend/app/models/pipeline_document.py)
- [celery_tasks.py](file://backend/app/tasks/celery_tasks.py)
- [retry_guard.py](file://backend/app/pipeline/safety/retry_guard.py)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive documentation for exponential backoff retry mechanisms in PipelineOrchestrator
- Updated error handling and recovery section to include intelligent retry logic for transient Supabase errors
- Enhanced database operations section with details about _run_with_retry function
- Added retry guard functionality documentation for stage-level retry decorators
- Updated troubleshooting guide to include retry-related debugging information

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document describes the 12-stage pipeline processing system used to transform academic manuscripts into properly formatted outputs. The PipelineOrchestrator coordinates a modular set of stages that perform text extraction, metadata enrichment, structure detection, classification, validation, formatting, and persistence. It implements robust error handling, timeouts, concurrency controls, and real-time status updates to support large-scale document processing. The system now includes sophisticated exponential backoff retry mechanisms to handle transient database errors and improve reliability.

## Project Structure
The pipeline is implemented in the backend under the pipeline package and integrates with models, services, and tasks:
- Orchestrator: Central coordinator for the pipeline lifecycle and stage orchestration
- Base stage interface: Defines the contract for all pipeline stages
- Document model: Internal representation of the document and its components across stages
- Task runner: Asynchronous execution via Celery to trigger the orchestrator
- Retry guard: Provides exponential backoff retry mechanisms for resilient operations

```mermaid
graph TB
Celery["Celery Task Runner<br/>backend/app/tasks/celery_tasks.py"] --> Orchestrator["PipelineOrchestrator<br/>backend/app/pipeline/orchestrator.py"]
Orchestrator --> Model["PipelineDocument<br/>backend/app/models/pipeline_document.py"]
Orchestrator --> StageBase["PipelineStage Base<br/>backend/app/pipeline/base.py"]
Orchestrator --> RetryGuard["Retry Guard<br/>backend/app/pipeline/safety/retry_guard.py"]
Orchestrator --> Services["External Services<br/>GROBID, Docling, Crossref, Exporters"]
```

**Diagram sources**
- [celery_tasks.py:41-66](file://backend/app/tasks/celery_tasks.py#L41-L66)
- [orchestrator.py:73-1281](file://backend/app/pipeline/orchestrator.py#L73-L1281)
- [base.py:4-23](file://backend/app/pipeline/base.py#L4-L23)
- [pipeline_document.py:49-207](file://backend/app/models/pipeline_document.py#L49-L207)
- [retry_guard.py:1-63](file://backend/app/pipeline/safety/retry_guard.py#L1-L63)

**Section sources**
- [celery_tasks.py:41-66](file://backend/app/tasks/celery_tasks.py#L41-L66)
- [orchestrator.py:73-1281](file://backend/app/pipeline/orchestrator.py#L73-L1281)
- [base.py:4-23](file://backend/app/pipeline/base.py#L4-L23)
- [pipeline_document.py:49-207](file://backend/app/models/pipeline_document.py#L49-L207)
- [retry_guard.py:1-63](file://backend/app/pipeline/safety/retry_guard.py#L1-L63)

## Core Components
- PipelineOrchestrator: Implements the end-to-end pipeline, stage coordination, timeouts, retries, cancellation checks, and persistence
- PipelineStage (base): Abstract interface that all stages implement
- PipelineDocument: Internal document model carrying content, metadata, formatting options, validation results, and processing history
- RetryGuard: Provides exponential backoff retry mechanisms for resilient operations

Key responsibilities:
- Orchestrate sequential and parallel stages with intelligent retry logic
- Enforce runtime flags (fast mode, semantic parser, crossref enrichment, AI reasoning)
- Manage concurrency limits and timeouts
- Persist partial results on failure and update statuses in real time
- Support an edit reprocessing flow for iterative refinement
- Implement exponential backoff retry mechanisms for transient database errors

**Section sources**
- [orchestrator.py:73-1281](file://backend/app/pipeline/orchestrator.py#L73-L1281)
- [base.py:4-23](file://backend/app/pipeline/base.py#L4-L23)
- [pipeline_document.py:49-207](file://backend/app/models/pipeline_document.py#L49-L207)
- [retry_guard.py:1-63](file://backend/app/pipeline/safety/retry_guard.py#L1-L63)

## Architecture Overview
The pipeline follows a staged design with explicit phases and optional AI layers. It supports:
- Direct parsing for supported formats
- Conversion to DOCX for unsupported formats
- Parallel extraction via GROBID and Docling for PDFs
- Structure detection and optional semantic parsing
- Classification and content analysis
- Caption matching for figures and tables
- Reference parsing and normalization
- Validation and AI reasoning integration
- Formatting and export
- Persistence and real-time status updates with intelligent retry mechanisms

```mermaid
sequenceDiagram
participant Client as "Client"
participant Celery as "Celery Task"
participant Orchestrator as "PipelineOrchestrator"
participant RetryGuard as "Retry Guard"
participant Parser as "ParserFactory"
participant GROBID as "GROBIDClient"
participant Docling as "DoclingClient"
participant Validator as "DocumentValidator"
participant Formatter as "Formatter"
participant Exporter as "Exporter"
Client->>Celery : "Submit document job"
Celery->>Orchestrator : "run_pipeline(input_path, job_id)"
Orchestrator->>RetryGuard : "wrap database operations with retry"
Orchestrator->>Parser : "parse input (direct or via DOCX)"
Orchestrator->>GROBID : "parallel header extraction (PDF)"
Orchestrator->>Docling : "parallel layout analysis (PDF)"
Orchestrator->>Orchestrator : "structure detection, classification"
Orchestrator->>Validator : "validate document"
Orchestrator->>Formatter : "apply template/style"
Formatter-->>Orchestrator : "generated_doc"
Orchestrator->>Exporter : "export formatted output"
Exporter-->>Orchestrator : "output_path"
Orchestrator-->>Celery : "result (success/error)"
Celery-->>Client : "completion status"
```

**Diagram sources**
- [celery_tasks.py:41-66](file://backend/app/tasks/celery_tasks.py#L41-L66)
- [orchestrator.py:576-1146](file://backend/app/pipeline/orchestrator.py#L576-L1146)
- [retry_guard.py:10-62](file://backend/app/pipeline/safety/retry_guard.py#L10-L62)

## Detailed Component Analysis

### PipelineOrchestrator
The orchestrator coordinates all pipeline stages, manages runtime flags, enforces timeouts, and persists results. It includes:
- Semaphore-based concurrency control to limit simultaneous jobs
- Safe execution wrappers and retry guards for resilience
- Conditional execution flags (fast mode, semantic parser, crossref enrichment, AI reasoning)
- Parallel extraction for PDFs using GROBID and Docling
- Timeout enforcement per stage using thread pools
- Cancellation checks against user actions
- Partial result persistence on failures
- Real-time status updates and SSE event emission
- Edit reprocessing flow for iterative refinement
- **Intelligent retry mechanisms for transient database errors using exponential backoff**

```mermaid
classDiagram
class PipelineOrchestrator {
+run_pipeline(input_path, job_id, template_name, formatting_options)
+run_edit_flow(job_id, edited_structured_data, template_name)
+_run_with_timeout(func, timeout_sec, ...)
+_persist_partial_result(job_id, doc_obj, sb)
+_update_status(document_id, phase, status, message, progress)
+_resolve_runtime_flags(formatting_options)
+_run_extraction_stage(...)
+_run_structure_detection(doc_obj)
+_run_semantic_parsing(doc_obj)
+_run_classification(doc_obj)
+_run_validation_stage(doc_obj)
+_run_formatting_stage(doc_obj)
+_export_document(doc_obj, input_path, job_id)
+_run_with_retry(operation_name, callback)
}
```

**Diagram sources**
- [orchestrator.py:73-1281](file://backend/app/pipeline/orchestrator.py#L73-L1281)

**Section sources**
- [orchestrator.py:73-1281](file://backend/app/pipeline/orchestrator.py#L73-L1281)

### Retry Guard and Exponential Backoff Mechanisms
The system implements sophisticated retry mechanisms to handle transient failures:

#### Stage-Level Retry Decorators
Multiple pipeline stages are wrapped with retry decorators that provide exponential backoff:
- `_run_extraction_stage`: 2 retries with 1.0s backoff factor
- `_run_structure_detection`: 1 retry with 1.0s backoff factor  
- `_run_semantic_parsing`: 2 retries with 1.0s backoff factor
- `_run_classification`: 2 retries with 1.0s backoff factor
- `_run_validation_stage`: 2 retries with 1.0s backoff factor
- `_run_formatting_stage`: 2 retries with 1.0s backoff factor

#### Database Operation Retry Logic
The `_run_with_retry` function provides intelligent retry logic for database operations:
- **3 attempts total** with exponential backoff (0.15s, 0.30s, 0.60s delays)
- **Transient error detection** for Supabase connection issues
- **Automatic client refresh** to handle stale connections
- **Operation-specific naming** for detailed logging

```mermaid
flowchart TD
Start(["Database Operation"]) --> Attempt1["Attempt 1"]
Attempt1 --> Success1{"Success?"}
Success1 --> |Yes| Complete["Complete Operation"]
Success1 --> |No| CheckTransient{"Transient Error?"}
CheckTransient --> |No| Fail["Permanent Failure"]
CheckTransient --> |Yes| Delay1["Wait 0.15s (2^0)"]
Delay1 --> Attempt2["Attempt 2"]
Attempt2 --> Success2{"Success?"}
Success2 --> |Yes| Complete
Success2 --> |No| CheckTransient2{"Transient Error?"}
CheckTransient2 --> |No| Fail
CheckTransient2 --> |Yes| Delay2["Wait 0.30s (2^1)"]
Delay2 --> Attempt3["Attempt 3"]
Attempt3 --> Success3{"Success?"}
Success3 --> |Yes| Complete
Success3 --> |No| Fail
```

**Diagram sources**
- [orchestrator.py:127-150](file://backend/app/pipeline/orchestrator.py#L127-L150)
- [retry_guard.py:10-62](file://backend/app/pipeline/safety/retry_guard.py#L10-L62)

**Section sources**
- [orchestrator.py:127-150](file://backend/app/pipeline/orchestrator.py#L127-L150)
- [orchestrator.py:505-518](file://backend/app/pipeline/orchestrator.py#L505-L518)
- [orchestrator.py:520-524](file://backend/app/pipeline/orchestrator.py#L520-L524)
- [orchestrator.py:526-541](file://backend/app/pipeline/orchestrator.py#L526-L541)
- [orchestrator.py:543-546](file://backend/app/pipeline/orchestrator.py#L543-L546)
- [orchestrator.py:548-551](file://backend/app/pipeline/orchestrator.py#L548-L551)
- [orchestrator.py:553-556](file://backend/app/pipeline/orchestrator.py#L553-L556)
- [retry_guard.py:10-62](file://backend/app/pipeline/safety/retry_guard.py#L10-L62)

### PipelineStage Base Interface
All pipeline stages implement a uniform interface to ensure modularity and testability.

```mermaid
classDiagram
class PipelineStage {
<<abstract>>
+process(document) PipelineDocument
}
```

**Diagram sources**
- [base.py:4-23](file://backend/app/pipeline/base.py#L4-L23)

**Section sources**
- [base.py:4-23](file://backend/app/pipeline/base.py#L4-L23)

### PipelineDocument Model
The internal document model carries parsed content, assets, metadata, formatting options, validation outcomes, and processing history.

```mermaid
classDiagram
class PipelineDocument {
+string document_id
+string original_filename
+string source_path
+Block[] blocks
+Figure[] figures
+Table[] tables
+Reference[] references
+Equation[] equations
+DocumentMetadata metadata
+TemplateInfo template
+Dict formatting_options
+bool is_valid
+string[] validation_errors
+string[] validation_warnings
+ReviewMetadata review
+string output_path
+Any generated_doc
+ProcessingStage[] processing_history
+datetime created_at
+datetime updated_at
+add_processing_stage(name, status, message, duration_ms)
+get_block_by_id(id) Block
+get_figure_by_id(id) Figure
+get_equation_by_id(id) Equation
+get_blocks_by_type(type) Block[]
+get_blocks_in_section(section) Block[]
+get_section_names() string[]
+get_stats() Dict
}
class DocumentMetadata {
+string title
+string[] authors
+string[] affiliations
+string abstract
+string[] keywords
+datetime publication_date
+string volume
+string issue
+string journal
+string doi
+string corresponding_author
+string email
+Dict ai_hints
}
class TemplateInfo {
+string template_name
+string template_version
}
class ProcessingStage {
+string stage_name
+string status
+string message
+int duration_ms
+datetime timestamp
}
PipelineDocument --> DocumentMetadata : "has"
PipelineDocument --> TemplateInfo : "has"
PipelineDocument --> ProcessingStage : "history"
```

**Diagram sources**
- [pipeline_document.py:49-207](file://backend/app/models/pipeline_document.py#L49-L207)

**Section sources**
- [pipeline_document.py:49-207](file://backend/app/models/pipeline_document.py#L49-L207)

### Stage Coordination and Control Flow
The orchestrator defines a clear progression of stages with optional branches and parallelism:
- Upload and job creation
- Text extraction (direct or via DOCX conversion)
- Optional Nougat OCR fallback for scanned PDFs
- Parallel GROBID and Docling extraction for PDFs
- Equation standardization and structure detection
- Optional semantic parsing and classification
- Content analysis and caption matching
- Reference parsing and normalization
- Optional CrossRef enrichment
- Optional AI reasoning integration
- Validation and formatting
- Export and persistence
- Real-time status updates and SSE events

```mermaid
flowchart TD
Start(["Start"]) --> Upload["Upload & Job Creation"]
Upload --> Extract["Text Extraction"]
Extract --> DirectCheck{"Direct parse supported?"}
DirectCheck --> |Yes| ParseDirect["Parse directly"]
DirectCheck --> |No| Convert["Convert to DOCX"]
Convert --> ParseDOCX["Parse DOCX"]
ParseDirect --> OCRCheck{"Empty extraction?"}
ParseDOCX --> OCRCheck
OCRCheck --> |Yes & PDF| Nougat["Nougat OCR Fallback"]
OCRCheck --> |No| Parallel["Parallel GROBID + Docling (PDF)"]
Nougat --> Parallel
Parallel --> Structure["Structure Detection"]
Structure --> Semantics{"Fast mode?"}
Semantics --> |No| Semantic["Semantic Parsing"]
Semantics --> |Yes| SkipSemantics["Skip semantic parsing"]
Semantic --> Classify["Classification"]
SkipSemantics --> Classify
Classify --> Analyze["Content Analysis"]
Analyze --> Captions["Caption Matching"]
Captions --> References["References Parsing & Normalization"]
References --> Crossref{"Crossref enrichment?"}
Crossref --> |Yes| CrossRefRun["Validate citations"]
Crossref --> |No| SkipCrossref["Skip enrichment"]
CrossRefRun --> Reasoning{"AI reasoning?"}
SkipCrossref --> Reasoning
Reasoning --> |Yes| AIReason["Generate instruction set"]
Reasoning --> |No| SkipReason["Skip reasoning"]
AIReason --> Validate["Validation"]
SkipReason --> Validate
Validate --> Format["Formatting"]
Format --> Export["Export"]
Export --> Persist["Persist Results"]
Persist --> End(["End"])
```

**Diagram sources**
- [orchestrator.py:576-1146](file://backend/app/pipeline/orchestrator.py#L576-L1146)

**Section sources**
- [orchestrator.py:576-1146](file://backend/app/pipeline/orchestrator.py#L576-L1146)

### Error Handling and Recovery
The orchestrator implements layered safety with sophisticated retry mechanisms:
- Concurrency limiting with rejection and status updates
- **Exponential backoff retry guards around critical stages**
- Timeout enforcement per stage with cancellation events
- Cancellation checks against user-initiated cancellations
- Partial result persistence on early failure
- Downgrade to warnings when artifacts exist despite validation errors
- Atomic completion checks ensuring output readiness before marking success
- **Intelligent retry logic for transient database operations with automatic client refresh**

```mermaid
flowchart TD
TryStart["Try Pipeline Execution"] --> Acquire{"Acquire semaphore?"}
Acquire --> |No| Reject["Reject: Too busy"]
Acquire --> |Yes| Proceed["Proceed with pipeline"]
Proceed --> TryBlock{"Exception?"}
TryBlock --> |No| Success["Mark COMPLETED"]
TryBlock --> |Yes| Partial{"Has output_path?"}
Partial --> |Yes| Warn["Persist with warnings"]
Partial --> |No| Fail["Persist partial result + FAIL"]
Warn --> End
Fail --> End
Success --> End
```

**Diagram sources**
- [orchestrator.py:586-598](file://backend/app/pipeline/orchestrator.py#L586-L598)
- [orchestrator.py:1106-1146](file://backend/app/pipeline/orchestrator.py#L1106-L1146)

**Section sources**
- [orchestrator.py:586-598](file://backend/app/pipeline/orchestrator.py#L586-L598)
- [orchestrator.py:1106-1146](file://backend/app/pipeline/orchestrator.py#L1106-L1146)

### Conditional Execution and Runtime Flags
Runtime flags control optional stages:
- fast_mode: Disables semantic parser, crossref enrichment, and AI reasoning by default
- semantic_parser: Enables optional semantic parsing layer
- crossref_enrichment: Enables optional CrossRef citation validation
- ai_reasoning: Enables optional AI reasoning layer

These flags are resolved from formatting options and environment settings, with tests overriding defaults to ensure determinism.

**Section sources**
- [orchestrator.py:306-323](file://backend/app/pipeline/orchestrator.py#L306-L323)

### Timeout Handling and Concurrency Controls
- Per-stage timeouts enforced via thread pool futures with cancellation events
- Global semaphore limits concurrent pipeline executions
- Configurable timeouts for GROBID, Docling, semantic parsing, and reasoning
- Graceful shutdown handling for server reloads and cancellations

**Section sources**
- [orchestrator.py:266-287](file://backend/app/pipeline/orchestrator.py#L266-L287)
- [orchestrator.py:69-72](file://backend/app/pipeline/orchestrator.py#L69-L72)
- [orchestrator.py:745-769](file://backend/app/pipeline/orchestrator.py#L745-L769)

### Edit Reprocessing Flow
The orchestrator supports an edit flow that:
- Reconstructs a document from edited structured data
- Re-validates and re-formats without re-extracting
- Persists a new version while preserving previous versions
- Updates output hash and status accordingly

```mermaid
sequenceDiagram
participant Client as "Client"
participant Orchestrator as "PipelineOrchestrator"
participant SB as "Supabase"
participant Exporter as "Exporter"
Client->>Orchestrator : "run_edit_flow(job_id, edited_structured_data)"
Orchestrator->>SB : "fetch original document"
Orchestrator->>Orchestrator : "reconstruct PipelineDocument"
Orchestrator->>Orchestrator : "validate_document()"
Orchestrator->>Orchestrator : "formatter.process()"
Orchestrator->>Exporter : "export edited output"
Exporter-->>Orchestrator : "output_path"
Orchestrator->>SB : "save new DocumentResult + version"
Orchestrator-->>Client : "success"
```

**Diagram sources**
- [orchestrator.py:1148-1281](file://backend/app/pipeline/orchestrator.py#L1148-L1281)

**Section sources**
- [orchestrator.py:1148-1281](file://backend/app/pipeline/orchestrator.py#L1148-L1281)

## Dependency Analysis
The orchestrator depends on external services and internal modules:
- ParserFactory for direct parsing and DOCX conversion
- GROBIDClient and DoclingClient for metadata and layout extraction
- Crossref client for citation validation
- Exporter for generating final outputs
- Supabase client for status updates and persistence
- Utilities for safe execution, retries, and hashing
- **RetryGuard for exponential backoff retry mechanisms**

```mermaid
graph TB
Orchestrator["PipelineOrchestrator"] --> ParserFactory["ParserFactory"]
Orchestrator --> GROBID["GROBIDClient"]
Orchestrator --> Docling["DoclingClient"]
Orchestrator --> Crossref["Crossref Client"]
Orchestrator --> Exporter["Exporter"]
Orchestrator --> Supabase["Supabase Client"]
Orchestrator --> Utils["Safe Execution, Hashing"]
Orchestrator --> RetryGuard["RetryGuard"]
RetryGuard --> ExponentialBackoff["Exponential Backoff Logic"]
```

**Diagram sources**
- [orchestrator.py:19-38](file://backend/app/pipeline/orchestrator.py#L19-L38)
- [orchestrator.py:58-61](file://backend/app/pipeline/orchestrator.py#L58-L61)
- [retry_guard.py:10-62](file://backend/app/pipeline/safety/retry_guard.py#L10-L62)

**Section sources**
- [orchestrator.py:19-38](file://backend/app/pipeline/orchestrator.py#L19-L38)
- [orchestrator.py:58-61](file://backend/app/pipeline/orchestrator.py#L58-L61)
- [retry_guard.py:10-62](file://backend/app/pipeline/safety/retry_guard.py#L10-L62)

## Performance Considerations
- Concurrency control: Limit simultaneous jobs to prevent resource exhaustion
- Parallel extraction: Offload GROBID and Docling to separate threads with bounded timeouts
- Fast mode: Disable optional AI layers to reduce latency during testing or constrained environments
- Streaming and SSE: Provide real-time feedback to users without blocking the pipeline
- Hashing and atomic completion: Ensure integrity checks before marking success
- Memory footprint: Prefer incremental processing and avoid loading entire documents into memory when possible
- **Exponential backoff: Minimizes retry overhead while maximizing success probability for transient failures**
- **Client refresh: Automatic connection recovery reduces downtime from stale database connections**

## Troubleshooting Guide
Common issues and remedies:
- Too many concurrent jobs: The semaphore rejects new requests; reduce batch sizes or scale horizontally
- Stage timeouts: Increase stage-specific timeout settings or disable optional stages
- Cancellations: Server reloads or user cancellations are handled gracefully; check status updates
- Partial results: On failure, partial results are persisted to aid debugging
- Output readiness: Atomic checks ensure only valid artifacts are marked as completed
- Edit flow failures: Validate edited structured data and rerun the edit flow
- **Database retry failures: Monitor exponential backoff logs; check transient error markers in database operations**
- **Connection issues: Automatic client refresh handles stale connections; verify network stability**

**Section sources**
- [orchestrator.py:586-598](file://backend/app/pipeline/orchestrator.py#L586-L598)
- [orchestrator.py:1106-1146](file://backend/app/pipeline/orchestrator.py#L1106-L1146)
- [orchestrator.py:127-150](file://backend/app/pipeline/orchestrator.py#L127-L150)

## Conclusion
The pipeline system is designed for reliability, scalability, and extensibility. The PipelineOrchestrator coordinates modular stages with robust error handling, timeouts, and real-time feedback. The implementation of exponential backoff retry mechanisms significantly improves resilience against transient database failures. Optional AI layers and runtime flags enable tuning for performance and quality. The edit reprocessing flow supports iterative refinement, and the document model provides a consistent representation across all stages.

## Appendices

### Pipeline Phases and Responsibilities
- UPLOAD: Job initialization and status updates
- EXTRACTION: Text extraction and optional OCR fallback
- PARALLEL AI EXTRACTION: GROBID and Docling for PDFs
- STRUCTURE DETECTION: Heading and section identification
- SEMANTIC PARSING: Optional NLP layer for confidence scores
- CLASSIFICATION: Content categorization
- CONTENT ANALYSIS: Keyword extraction and metadata enrichment
- CAPTION MATCHING: Figures and tables alignment
- REFERENCES: Parsing and normalization
- CROSSREF ENRICHMENT: Optional citation validation
- AI REASONING: Optional semantic advice
- VALIDATION: Structural and style validation
- FORMATTING: Template-driven styling
- EXPORT: Artifact generation
- PERSISTENCE: Final result storage and status updates

### Retry Mechanism Configuration
**Stage-Level Retry Decorators:**
- Extraction: 2 retries, 1.0s backoff factor
- Structure Detection: 1 retry, 1.0s backoff factor
- Semantic Parsing: 2 retries, 1.0s backoff factor
- Classification: 2 retries, 1.0s backoff factor
- Validation: 2 retries, 1.0s backoff factor
- Formatting: 2 retries, 1.0s backoff factor

**Database Operation Retry Logic:**
- Maximum 3 attempts with exponential backoff
- Delays: 0.15s, 0.30s, 0.60s (2^n-1)
- Transient error detection for Supabase
- Automatic client refresh on retry
- Detailed logging for debugging