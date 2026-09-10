# ch29-rag

> **Status: DONE**（14 mock 测试通过 + live 冒烟通过；见 LAST_TESTED.md）

## 1. 目标

不依赖任何框架，实现 Ch29 的**七环 RAG 管道**：解析 → 清洗 → 分块 → 元数据 → 索引 → 检索 → 生成。核心卖点是**分层归因**：trace 记录每一环的输入输出，管道任一环失败都能定位到环；同时实现父子块折中、注入纪律（编号+出处+框架声明）与拒答路径。

## 2. 架构（七环 ↔ 函数）

```text
Ring 1 Parsing   parse(raw)                        页拼接（阅读顺序）
Ring 2 Cleaning  clean(doc)                        去页眉页脚/乱码/重复
Ring 3 Chunking  chunk_structure(doc)              结构对齐分块（按 ## 节）+ 父子块
Ring 4 Metadata  enrich + metadata_gate            溯源元数据 + 入索引完整率门禁
Ring 5 Indexing  build_index / BM25 / reconcile    BM25 倒排 + 向量索引 + 对账
Ring 6 Retrieval retrieve(query, index, vec)       BM25 饱和归一 ⊕ cosine，α 加权
Ring 7 Generation generate / render_context / refuse  编号+出处+框架声明，引用 [n]，拒答

编排：RagPipeline.answer(query) → RagResult(answer, trace[七环])
骨架入口：rag_answer(query, embed_fn, llm, config)
```

- BM25/混合检索实现与 `scripts/ch28_retrieval_experiment.py` 同源（字符 bigram 分词、α 加权）；
- BM25 分数用 `s/(s+K)` 饱和归一、dense 用 cosine 截断 [0,1]，两者加权后可做**绝对阈值**拒答判定（rank 归一做不到）；
- 检索 child 块（小块准），生成注入 parent 块（上下文完整）——父子块折中；
- 生成走 Ollama 原生 `/api/chat` + `think=False`（OpenAI-compat 端点忽略 think，2026-09-10 实测，同 Ch7）；云端供应商换 `make_client('openai')` 走 OpenAI-compat，代码零改动。

## 3. 目录

```text
src/rag_pipeline/
  models.py       # Chunk / ChunkMeta / RingTrace（分层归因的最小结构）
  corpus.py       # 内置 12 篇中文知识库文档（客服/IT 域，含页眉页脚噪声）
  parsing.py      # Ring 1  cleaning.py   # Ring 2  chunking.py  # Ring 3
  metadata.py     # Ring 4  indexing.py   # Ring 5  retrieval.py # Ring 6
  generation.py   # Ring 7  client.py     # OllamaClient / OpenAICompatClient / OllamaEmbedder
  pipeline.py     # RagPipeline（build rings 1-5 + answer rings 6-7）
tests/test_rings.py     # 9 个 mock 测试（rings 1-6）
tests/test_pipeline.py  # 5 个 mock 测试（七环 trace / 拒答 / 引用 / 冻结检索）
examples/live_smoke.py  # live 冒烟（本机 Ollama）
```

## 4. 运行

```bash
cd code/ch29-rag
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python pytest pydantic httpx
PYTHONPATH=src .venv/bin/python -m pytest -q        # 14 passed（全部 mock，不依赖 Ollama）

# live 冒烟（需本机 Ollama：bge-m3 + qwen3.5:9b-mlx）：
PYTHONPATH=src .venv/bin/python examples/live_smoke.py
```

## 5. 预期结果（Last verified: 2026-09-10）

```text
测试：14 passed（BM25 打分/混合加权/门禁/对账/trace 七环结构/拒答路径/引用/冻结检索）

live 冒烟（bge-m3 + qwen3.5:9b-mlx, think off, temp 0）：
  Query "会员自动续费扣款了，但我上个月就取消了订阅，怎么退款？"
    ring 6 max_score=0.798 → ring 7 带引用回答：
    "…可在扣款后 72 小时内申请全额退款，原路退回 [1]"
    citations: [1] kb_subscription_refund.md·自动续费与退款
               [3][4] kb_refund_policy.md·退款流程/退款审核
  Query "竞品 X 的价格是多少？"（语料中无答案）
    ring 6 max_score=0.150 < threshold 0.45 → ring 7 拒答：
    "未找到可靠来源：知识库中没有与该问题足够相关的资料…"
  索引：12 篇 / 13 页 → 20 节 → 21 child 块，门禁 21/0，对账通过
```

## 6. 设计要点（正文对应）

- **每环一个接口，可独立替换与评测**：管道原则"任何一环都可以被 mock"——`answer_with_frozen_hits` 冻结检索评测生成环；测试里的 `toy_embed_fn`/`FakeLLM` 同理
- **trace = 分层归因的地基**：`RingTrace(ring, stage, summary, data)`，七环各一条；"答错了"的判定表（依据缺/召回败/排序败/生成败/元数据错）直接读 trace
- **拒答是功能不是缺陷**：max hybrid score < 阈值（默认 0.45）→ `refuse()`，不调 LLM；"语料中无答案"的查询必须进评测集（Ch13 对抗层）
- **元数据完整率是自动化门禁**：缺 source/date 的块拒绝入索引（`metadata_gate`）；对账（`reconcile`）拦"索引静默腐烂"（案例三）
- **阈值的取值依据**：live 实测域内 query max_score≈0.80、域外≈0.15，0.45 居中有余量；正式定阈值用第 31 章 PR 曲线

## 7. 已知边界（第 30/31 章）

查询改写（"便宜点买"vs"折扣"）、多路/迭代检索、重排——Advanced Retrieval；召回率/引用正确性的正式量化——第 31 章。本实现把测试集与阈值参数全部留在 `RagConfig`，管道变更 = 实验变更（第 17 章纪律）。
