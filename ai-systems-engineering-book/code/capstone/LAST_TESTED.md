# LAST_TESTED

- status: DONE — clean install / 29 mock tests pass / 32 条分层评测（mock 模式 100%）/ live 冒烟通过（问答 + ACL 拒绝 + 审批红线 + 审计回放 + 成本）
- last verified: 2026-09-10
- environment: macOS M4 Pro 48GB, Ollama local, bge-m3 (embeddings), qwen3.5:9b-mlx (think=false), temperature=0
- deps tested: pydantic 2.13.5, httpx 0.28.1, pytest 9.1.1, uv 0.11.26, Python 3.12.14 (Homebrew)
- 复用项目（PYTHONPATH 跨项目引用，全部零改动）：ch08-tool-calling / ch11-model-gateway / ch19-agent-loop / ch29-rag / ch33-ai-backend / evals-shared-eval-runner
- eval 结果（mock 模式）：32 cases（simple_fact 8 / multi_hop 4 / refuse 5 / permission 6 / sql 9）全过；run_id 落盘 results/mock-latest/，metadata 标注 mode=mock（生成质量层需 live）
- live smoke 摘要：
  - ① "非白名单软件怎么申请安装？" → kb_software_install.md 引用回答；cost 0.002332（457+42 tok，standard）
  - ② 员工问 "P4 薪级带宽" → salary/server_ops/expense 检索层被拒，模型回答"知识库中未找到"（密级零泄漏）
  - ③ 写路径：search_docs → submit_request 挂起（副作用 0）→ raise_if_not_approved 显式拒绝 → it-manager approve → ticket T-0001 落地
  - ④ 审计回放完整（u001 / sha 问题哈希 / 允许+拒绝块 / 工具 / 审批 pending→approved / cost 0.017192；平台累计 0.020616）
- note: 红线断言（未审批→拒绝/批准后→执行）由测试 test_write_tool_without_approval_never_executes 与 test_write_tool_executes_only_after_approval 锁定
