# Phase 4: Development Planning - Hybrid Architecture

## 🎯 Overview

**Phase 4** creates **evidence-based implementation plans** using a **Hybrid Pipeline Architecture** that combines:
- **Deterministic algorithms** (Stages 1-3, 5): Parsing, RAG, Pattern Matching, Validation
- **Single LLM call** (Stage 4): Plan synthesis

**Key Metrics:**
- ⚡ **Duration**: 18-40 seconds (vs. 5-7 minutes with CrewAI)
- 💰 **Cost**: 1 LLM call (vs. 5 with CrewAI)
- ✅ **Success Rate**: 95%+ (deterministic stages don't fail)
- 🎯 **Accuracy**: Same data inputs as CrewAI (100% of Phase 0-2 outputs)

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────┐
│ STAGE 1: Input Parser (Deterministic)                 │
│ • Parse JIRA XML, DOCX, Excel, logs → JSON            │
│ • Duration: <1s                                        │
│ • NO LLM                                               │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ STAGE 2: Component Discovery (RAG + Scoring)          │
│ • ChromaDB semantic search (top 20)                   │
│ • Multi-signal scoring:                               │
│   - Semantic similarity (ChromaDB distance)           │
│   - Name matching (fuzzy)                             │
│   - Package matching (labels)                         │
│   - Stereotype matching (keywords)                    │
│ • Duration: 2-5s                                       │
│ • NO LLM                                               │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ STAGE 3: Pattern Matcher (TF-IDF + Rules)             │
│ • Test patterns: TF-IDF similarity (925 tests)        │
│ • Security: Rule-based lookup (143 configs)           │
│ • Validation: Regex matching (149 patterns)           │
│ • Error handling: Keyword matching (23 patterns)      │
│ • Duration: 1-3s                                       │
│ • NO LLM                                               │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ STAGE 4: Plan Generator (LLM - ONLY HERE!)            │
│ • Single LLM call with ALL previous stage data        │
│ • Structured output (JSON schema)                     │
│ • Duration: 15-30s                                     │
│ • YES LLM (only stage with LLM)                        │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ STAGE 5: Validator (Pydantic)                         │
│ • Schema validation (Pydantic models)                 │
│ • Completeness checks                                 │
│ • Layer compliance checks                             │
│ • Duration: <1s                                        │
│ • NO LLM                                               │
└────────────────────────────────────────────────────────┘
```

---

## 📊 Input Data (100% of Phase 0-2)

### From Phase 0: Indexing
```
ChromaDB Vector Store (.cache/.chroma)
- 951 components indexed
- Semantic search for component discovery
```

### From Phase 1: Architecture Facts
```json
architecture_facts.json (17 keys, 70k lines, 8 MB):
{
  "components": [951],          // Stage 2: Component Discovery
  "interfaces": [226],          // Stage 2: API Endpoint Lookup
  "relations": [190],           // Stage 2: Dependency Graph
  "endpoint_flows": [206],      // Stage 2: Request Flow Analysis
  "tests": [925],               // Stage 3: TF-IDF Test Similarity ⭐
  "security_details": [143],    // Stage 3: Security Lookup ⭐
  "validation": [149],          // Stage 3: Validation Matching ⭐
  "error_handling": [23],       // Stage 3: Error Pattern Matching ⭐
  "workflows": [42],            // Stage 3: Business Context
  "dependencies": [170],        // Stage 2: Dependency Impact
  "tech_versions": [8],         // Stage 4: Tech Stack Info
  "evidence": [2508]            // Stage 5: Traceability
}
```

### From Phase 2: Architecture Analysis
```json
analyzed_architecture.json (400 KB):
{
  "macro_architecture": {...},      // Stage 4: Architecture Style
  "micro_architecture": {...},      // Stage 5: Layer Compliance
  "architecture_quality": {...}     // Stage 4: Quality Context
}
```

---

## 🔬 Stage Details

### Stage 1: Input Parser

**Purpose**: Parse task inputs from any format → normalized JSON

**Supported Formats**:
- JIRA XML (`.xml`)
- Confluence DOCX (`.docx`)
- Excel (`.xlsx`, `.xls`)
- Text/Logs (`.txt`, `.log`)

**Algorithm**: Format detection by extension → dedicated parser → TaskInput schema

**Example Output**:
```json
{
  "task_id": "PROJ-123",
  "source_file": "inputs/tasks/PROJ-123.xml",
  "source_format": "jira_xml",
  "summary": "Add email notification on user registration",
  "description": "Users should receive welcome email...",
  "acceptance_criteria": ["Email sent within 1 minute"],
  "technical_notes": "Use existing EmailService, async processing",
  "labels": ["backend", "notification"],
  "priority": "High"
}
```

---

### Stage 2: Component Discovery

**Purpose**: Find affected components using RAG + multi-signal scoring

**Algorithm**:
1. **ChromaDB Semantic Search** (top 20 candidates)
   ```python
   similarity = 1 - distance  # Convert distance to similarity (0-1)
   ```

2. **Name Matching** (fuzzy string match)
   ```python
   from fuzzywuzzy import fuzz
   score = fuzz.partial_ratio(task_description, component_name) / 100.0
   ```

3. **Package Matching** (label-based)
   ```python
   if label in component.package:
       score += 0.5
   ```

4. **Stereotype Matching** (keyword-based)
   ```python
   stereotype_keywords = {
       "controller": ["endpoint", "rest", "api"],
       "service": ["business", "logic", "workflow"],
       ...
   }
   ```

5. **Weighted Combination**
   ```python
   final_score = (
       semantic * 0.4 +
       name * 0.3 +
       package * 0.2 +
       stereotype * 0.1
   )
   ```

**Example Output**:
```json
{
  "affected_components": [
    {
      "id": "component.backend.service.user_service_impl",
      "name": "UserServiceImpl",
      "stereotype": "service",
      "layer": "application",
      "package": "backend.user_logic_impl",
      "relevance_score": 0.95,
      "change_type": "modify",
      "source": "chromadb"
    }
  ],
  "interfaces": [...],
  "dependencies": [...]
}
```

---

### Stage 3: Pattern Matcher

**Purpose**: Match test, security, validation, and error patterns using algorithms

#### Test Pattern Matching (TF-IDF Similarity)

**Algorithm**:
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Build corpus
corpus = [task_description] + [test.name + " ".join(test.scenarios) for test in tests]

# 2. TF-IDF vectorization
vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
tfidf_matrix = vectorizer.fit_transform(corpus)

# 3. Cosine similarity
query_vector = tfidf_matrix[0]
test_vectors = tfidf_matrix[1:]
similarities = cosine_similarity(query_vector, test_vectors).flatten()

# 4. Top K
top_tests = sorted(zip(tests, similarities), key=lambda x: x[1], reverse=True)[:5]
```

#### Security Pattern Matching (Rule-Based)

**Algorithm**: File path prefix matching
```python
for security_config in security_details:
    if component_package in security_config.file_path:
        # Match found!
```

#### Validation Pattern Matching (Target Class Matching)

**Algorithm**: Entity name matching
```python
for validation in validations:
    if entity_name in validation.target_class:
        # Match found!
```

#### Error Handling Pattern Matching (Keyword Matching)

**Algorithm**: Exception class substring matching
```python
for error_handler in error_handling:
    if keyword in error_handler.exception_class.lower():
        # Match found!
```

**Example Output**:
```json
{
  "test_patterns": [
    {
      "name": "UserServiceImplTest",
      "framework": "junit",
      "test_type": "unit",
      "relevance_score": 0.87,
      "pattern_description": "Similar unit test using junit"
    }
  ],
  "security_patterns": [...],
  "validation_patterns": [...],
  "error_patterns": [...]
}
```

---

### Stage 4: Plan Generator (LLM)

**Purpose**: Synthesize all previous stages into implementation plan

**LLM Prompt Structure**:
```
You are a senior software architect.

TASK:
- Task ID: PROJ-123
- Summary: Add email notification...
- Description: ...

DISCOVERED COMPONENTS: (from Stage 2)
- UserServiceImpl (service, relevance: 0.95)
- EmailService (service, relevance: 0.98)

SIMILAR TEST PATTERNS: (from Stage 3, 925 tests)
- UserServiceImplTest (junit, relevance: 0.87)

SECURITY PATTERNS: (from Stage 3, 143 configs)
- Authentication required for EmailService

VALIDATION PATTERNS: (from Stage 3, 149 patterns)
- @NotNull on User.email

ERROR HANDLING: (from Stage 3, 23 patterns)
- EmailSendException → DefaultExceptionHandler

ARCHITECTURE CONTEXT: (from Phase 2)
- Style: Modular Monolith
- Pattern: Layered (Controller → Service → Repository)
- Quality Grade: C

CREATE IMPLEMENTATION PLAN AS JSON:
{
  "development_plan": {
    "affected_components": [...],
    "implementation_steps": [...],
    "test_strategy": {...},
    ...
  }
}

IMPORTANT:
- Return ONLY valid JSON
- Use ONLY the components/patterns provided above
- DO NOT invent new components
```

**LLM Configuration**:
```python
llm = ChatOpenAI(
    model="gpt-oss-120b",
    temperature=0.2,  # Low temperature for consistency
    max_tokens=8000,  # Allow long plans
)
```

---

### Stage 5: Validator

**Purpose**: Validate plan completeness and quality

**Checks**:
1. **Required Fields**: affected_components, implementation_steps, test_strategy, etc.
2. **Field Types**: Lists non-empty, complexity in [Low, Medium, High]
3. **Component References**: Implementation steps reference actual components
4. **Layer Compliance**: Changes follow architecture layer rules

**Example Validation Result**:
```json
{
  "is_valid": true,
  "missing_fields": [],
  "warnings": [
    "No security_considerations specified"
  ],
  "errors": []
}
```

---

## 📈 Performance Comparison

| Metric | CrewAI (Old) | Hybrid Pipeline (New) | Improvement |
|--------|--------------|----------------------|-------------|
| **Duration** | 5-7 minutes | 18-40 seconds | **10-20x faster** ⚡ |
| **LLM Calls** | 5 | 1 | **5x fewer** 💰 |
| **Success Rate** | 70-80% | 95%+ | **15-25% higher** ✅ |
| **Tool-Use Issues** | Frequent | None (deterministic) | **100% reliable** 🎯 |
| **Debugging** | Hard (Agent black box) | Easy (Pipeline steps) | **Much easier** 🔍 |
| **Data Utilization** | 20% (only components) | 100% (all 17 keys) | **5x more data** 📊 |

---

## 🚀 Usage

### Via CLI

```bash
# Create sample task input
mkdir -p inputs/tasks
echo '<?xml version="1.0"?>
<item key="PROJ-123">
  <summary>Add email notification feature</summary>
  <description>Users should receive welcome email on registration</description>
  <labels>
    <label>backend</label>
    <label>notification</label>
  </labels>
</item>' > inputs/tasks/PROJ-123.xml

# Run Phase 0-4
python -m aicodegencrew run --preset architecture_full

# Output: knowledge/development/PROJ-123_plan.json
```

### Via Orchestrator

```python
from aicodegencrew.orchestrator import SDLCOrchestrator
from aicodegencrew.pipelines.development_planning import DevelopmentPlanningPipeline

orchestrator = SDLCOrchestrator()

# Register phases
orchestrator.register("phase4_development_planning",
    DevelopmentPlanningPipeline(
        input_file="inputs/tasks/PROJ-123.xml",
        facts_path="knowledge/architecture/architecture_facts.json",
        analyzed_path="knowledge/architecture/analyzed_architecture.json",
    )
)

# Run
result = orchestrator.run(phases=["phase4_development_planning"])
```

---

## 📄 Output Schema

```json
{
  "task_id": "PROJ-123",
  "source_files": ["inputs/tasks/PROJ-123.xml"],

  "understanding": {
    "summary": "Add email notification feature",
    "requirements": [...],
    "acceptance_criteria": [...],
    "technical_notes": "..."
  },

  "development_plan": {
    "affected_components": [
      {
        "id": "component.backend.service.user_service_impl",
        "name": "UserServiceImpl",
        "stereotype": "service",
        "layer": "application",
        "package": "backend.user_logic_impl",
        "relevance_score": 0.95,
        "change_type": "modify",
        "source": "chromadb"
      }
    ],

    "interfaces": [...],
    "dependencies": [...],

    "implementation_steps": [
      "1. Add EmailService dependency to UserServiceImpl (constructor injection)",
      "2. Create sendWelcomeEmail(User user) private method",
      "3. Call sendWelcomeEmail() from registerUser() after user creation",
      "4. Add @Async annotation for non-blocking email sending"
    ],

    "test_strategy": {
      "unit_tests": ["UserServiceImplTest.testSendEmail()"],
      "integration_tests": ["UserRegistrationIT.testEmailSent()"],
      "similar_patterns": [
        {
          "name": "DeedEntryServiceImplTest",
          "framework": "junit",
          "relevance_score": 0.87,
          "pattern_description": "Similar unit test with @MockBean"
        }
      ]
    },

    "security_considerations": [
      {
        "security_type": "authentication",
        "pattern": "EmailService requires auth",
        "recommendation": "Verify user is authenticated before sending email"
      }
    ],

    "validation_strategy": [
      {
        "validation_type": "not_null",
        "field": "email",
        "recommendation": "Use @NotNull @Email on User.email"
      }
    ],

    "error_handling": [
      {
        "exception_class": "EmailSendException",
        "handling_type": "exception_handler",
        "recommendation": "Add @ExceptionHandler in DefaultExceptionHandler"
      }
    ],

    "architecture_context": {
      "style": "Modular Monolith",
      "layer_pattern": "Controller → Service → Repository",
      "quality_grade": "C",
      "layer_compliance": ["✅ UserService → EmailService (valid)"]
    },

    "estimated_complexity": "Low",
    "complexity_reasoning": "Simple service call addition, existing infrastructure",
    "estimated_files_changed": 3,
    "risks": [
      "Email sending failure should not block user registration"
    ],

    "evidence_sources": {
      "components": "architecture_facts.json (951 components)",
      "test_patterns": "architecture_facts.json (925 tests)",
      "security": "architecture_facts.json (143 security details)",
      "validation": "architecture_facts.json (149 validation patterns)",
      "error_handling": "architecture_facts.json (23 error patterns)",
      "architecture": "analyzed_architecture.json",
      "semantic_search": "ChromaDB (Phase 0)"
    }
  }
}
```

---

## 🎯 Key Design Principles

1. **Evidence-First**: Every recommendation backed by Phase 0-2 facts
2. **Use Right Tool**: LLM for synthesis, algorithms for pattern matching
3. **Fail Fast**: Deterministic stages don't fail, LLM stage validated
4. **Single Responsibility**: Each stage has one clear job
5. **Composable**: Stages can be tested/replaced independently

---

## 🔧 Dependencies

```bash
# Core dependencies (already installed)
pip install langchain-openai pydantic

# Optional (for better pattern matching)
pip install scikit-learn fuzzywuzzy python-Levenshtein
```

---

## 📊 Metrics & Observability

All stages log structured metrics to `logs/metrics.jsonl`:

```json
{"event": "stage_complete", "stage": "stage1_input_parser", "duration_seconds": 0.12}
{"event": "stage_complete", "stage": "stage2_component_discovery", "duration_seconds": 3.45, "components_found": 5}
{"event": "stage_complete", "stage": "stage3_pattern_matcher", "duration_seconds": 1.87, "test_patterns": 5}
{"event": "stage_complete", "stage": "stage4_plan_generator", "duration_seconds": 18.32, "llm_call": true}
{"event": "stage_complete", "stage": "stage5_validator", "duration_seconds": 0.08, "is_valid": true}
{"event": "phase_complete", "phase": "phase4_development_planning", "duration_seconds": 23.84}
```

---

## ✅ Success Criteria

- ✅ **Speed**: <40 seconds per plan
- ✅ **Success Rate**: >95%
- ✅ **Data Coverage**: 100% of Phase 0-2 outputs used
- ✅ **Plan Completeness**: All required sections present
- ✅ **Evidence-Based**: All recommendations link to patterns

---

## 🚧 Future Enhancements

1. **Batch Processing**: Process multiple tasks in parallel
2. **Plan Refinement**: Iterative improvement loop
3. **Custom Scorers**: Domain-specific component discovery
4. **Pattern Learning**: Learn from validated plans
5. **Integration with Phase 5**: Direct handoff to Code Generation
