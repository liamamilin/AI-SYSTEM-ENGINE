# TOC.md

# Part 0 — AI Systems Engineering Foundations

## Chapter 1 — AI 技术栈与 L4-L6 定位
- L0-L6
- Research vs Engineering
- Model vs System
- 为什么聚焦 L4-L6

## Chapter 2 — AI System 的基本组成
- Model
- Context
- Tool
- State
- Runtime
- Backend
- Eval
- Data
- Infrastructure

## Chapter 3 — Problem Framing
- 业务问题建模
- LLM 是否必要
- Deterministic vs Probabilistic
- Failure Cost
- Requirements / Constraints

## Chapter 4 — Workflow vs Agent
- 普通程序
- Workflow
- LLM-enhanced Workflow
- Agent
- Autonomy Boundary
- 什么时候不应该使用 Agent

---

# Part 1 — LLM Interface Engineering

## Chapter 5 — LLM 请求的工程模型
- Token
- Context Window
- Messages
- Sampling
- Reasoning
- Model capabilities

## Chapter 6 — Instruction & Prompt Engineering
- Instruction hierarchy
- Examples
- Prompt templates
- Prompt as Context
- Prompt limitations

## Chapter 7 — Structured Output
- JSON Schema
- Pydantic
- Validation
- Constrained output
- Retry and repair

## Chapter 8 — Tool Calling
- Tool schema
- Tool selection
- Arguments
- Tool result
- Deterministic execution

## Chapter 9 — Streaming, Async and Concurrency
- Streaming
- Async / await
- Cancellation
- Backpressure
- TTFT

## Chapter 10 — Reliability of Model Calls
- Retry
- Backoff
- Timeout
- Rate limit
- Invalid output
- Fallback

## Chapter 11 — Model Gateway and Routing
- Provider abstraction
- Model selection
- Fallback
- Quality / latency / cost
- Local vs API models

---

# Part 2 — Evaluation & Experiment Engineering

## Chapter 12 — Why Eval Is Core Engineering
- Build-Measure-Diagnose
- Baseline
- Regression

## Chapter 13 — Eval Dataset Engineering
- Case design
- Ground truth
- Difficulty
- Metadata
- Versioning

## Chapter 14 — Component Evaluation
- Structured output
- Tool choice
- Tool arguments
- Retrieval
- Planning

## Chapter 15 — System Evaluation
- Task success
- Accuracy
- Latency
- Cost
- Failure rate

## Chapter 16 — LLM-as-a-Judge
- Rubrics
- Pairwise
- Reference-based
- Judge bias
- Human calibration

## Chapter 17 — Experiment Reproducibility
- Model version
- Prompt version
- Dataset version
- Config version
- Git commit
- Experiment tracking

---

# Part 3 — Agent Systems Engineering

## Chapter 18 — What Is an Agent?
- Agent = Model + Loop + Tools + State
- Agent myths
- Autonomy

## Chapter 19 — Build an Agent Loop From Scratch
- Minimal loop
- Stop conditions
- Tool result loop

## Chapter 20 — Tool Runtime
- Registry
- Schema
- Executor
- Timeout
- Error handling
- Idempotency

## Chapter 21 — State
- Conversation state
- Task state
- Application state
- Environment state

## Chapter 22 — Planning
- Implicit planning
- ReAct
- Plan-and-execute
- Task decomposition
- Planning failure

## Chapter 23 — Memory
- Working memory
- Conversation memory
- Semantic memory
- Episodic memory
- User state

## Chapter 24 — Context Management
- Selection
- Ordering
- Pruning
- Summarization
- Compression
- Caching

## Chapter 25 — Human-in-the-loop
- Approval
- Escalation
- Confidence
- High-risk actions
- Autonomy boundary

## Chapter 26 — Multi-Agent and Sub-Agent
- Handoff
- Delegation
- Supervisor
- Isolation
- When multi-agent is unnecessary

---

# Part 4 — Context, Retrieval, Knowledge and Data

## Chapter 27 — Context Engineering
- Instructions
- Conversation
- Tool results
- Retrieval
- Memory
- Environment

## Chapter 28 — Retrieval Fundamentals
- Sparse retrieval
- BM25
- Dense retrieval
- Embeddings
- Hybrid search

## Chapter 29 — RAG Pipeline
- Parsing
- Cleaning
- Chunking
- Metadata
- Indexing
- Retrieval
- Generation

## Chapter 30 — Advanced Retrieval
- Query rewrite
- Multi-query
- Filtering
- Reranking
- Hierarchical retrieval
- Context compression

## Chapter 31 — Retrieval Evaluation
- Recall@K
- Precision@K
- MRR
- NDCG
- Citation correctness
- Faithfulness

## Chapter 32 — Data Engineering for AI Systems
- Data lifecycle
- Provenance
- Cleaning
- Deduplication
- Versioning
- Privacy
- Data contracts

---

# Part 5 — Production AI Engineering

## Chapter 33 — AI Backend Architecture
- API
- Session
- Job
- Agent runtime
- Model
- Database
- Streaming events

## Chapter 34 — Long-running Tasks
- Queue
- Worker
- Async
- Checkpoint
- Resume
- Cancellation

## Chapter 35 — Reliability Engineering
- Retry
- Fallback
- Circuit breaker
- Timeout
- Idempotency
- Graceful degradation

## Chapter 36 — Observability
- Logs
- Metrics
- Traces
- Tokens
- Cost
- Latency
- Tool traces

## Chapter 37 — AI Security
- Prompt injection
- Indirect injection
- Tool abuse
- Privilege escalation
- Secret leakage
- Data exfiltration
- Unsafe execution

## Chapter 38 — Sandbox and Permission Systems
- Trust boundaries
- Capability design
- Read / write separation
- Approval
- Secret isolation

## Chapter 39 — MCP and Tool Protocols
- Why protocols exist
- Client
- Server
- Tools
- Resources
- Authentication
- Build a minimal MCP server

## Chapter 40 — AI Economics
- Cost/request
- Cost/task
- Token usage
- Cache
- Model routing
- Value vs cost

---

# Part 6 — Model Serving & Inference Engineering

## Chapter 41 — LLM Inference Fundamentals
- Weights
- Prefill
- Decode
- KV cache

## Chapter 42 — GPU Memory
- Model weights
- KV cache
- Activations
- Context length
- Concurrency

## Chapter 43 — Batching and Scheduling
- Static batching
- Continuous batching
- Scheduling
- Throughput

## Chapter 44 — Inference Metrics
- TTFT
- TPOT
- Tokens/s
- P50
- P95
- P99

## Chapter 45 — Quantization
- FP16 / BF16
- INT8
- INT4
- AWQ
- GPTQ
- Trade-offs

## Chapter 46 — Advanced Inference
- Prefix caching
- Speculative decoding
- Tensor parallel
- Pipeline parallel
- Expert parallel
- KV offloading
- Prefill/decode disaggregation

## Chapter 47 — vLLM as a Serving Case Study
- Installation
- OpenAI-compatible API
- Configuration
- Benchmark
- Metrics

## Chapter 48 — Production Serving
- Load balancing
- Routing
- Autoscaling
- Caching
- Failover
- Monitoring

---

# Part 7 — Post-training Engineering

## Chapter 49 — When Should You Train?
- Prompt vs RAG vs Tool vs Training
- Behavior adaptation
- Cost-benefit analysis

## Chapter 50 — Dataset Engineering for Post-training
- Collection
- Cleaning
- Deduplication
- Formatting
- Quality
- Difficulty
- Contamination

## Chapter 51 — Supervised Fine-Tuning
- Input / target
- Loss
- Training loop
- Eval

## Chapter 52 — LoRA and QLoRA
- Low-rank adaptation
- Memory savings
- Training setup
- Failure cases

## Chapter 53 — Preference Optimization
- Preference data
- DPO
- RLHF
- PPO
- GRPO
- Verifiable rewards

## Chapter 54 — Synthetic Data and Distillation
- Teacher/student
- Data generation
- Filtering
- Risks

## Chapter 55 — Post-training Evaluation
- Baseline
- Same eval set
- Regression
- Capability trade-offs

---

# Part 8 — End-to-End AI System Design

## Chapter 56 — AI System Design Method
- Requirements
- Constraints
- Architecture
- Model
- Context
- Tools
- Runtime
- Eval
- Security
- Economics

## Chapter 57 — Coding Agent Case Study
- Code search
- Filesystem
- Shell
- Patch
- Test
- Sandbox
- Git
- Eval

## Chapter 58 — Research Agent Case Study
- Search
- Browse
- Read
- Extract
- Cite
- Synthesize

## Chapter 59 — Enterprise Knowledge Agent
- RAG
- SQL
- Tools
- Auth
- Audit
- Permissions

## Chapter 60 — Capstone: Production AI Agent Platform
- Full architecture
- Runnable repository
- Eval suite
- Deployment
- Observability
- Security
- Cost analysis

---

# Appendix

- A. Python / Async refresher
- B. Docker / Linux refresher
- C. PostgreSQL / pgvector
- D. GPU basics
- E. Multimodal AI
- F. Framework comparison
- G. Glossary
- H. Current ecosystem notes
