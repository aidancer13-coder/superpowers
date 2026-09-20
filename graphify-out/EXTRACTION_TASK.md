# superpowers graphify — extraction task brief (self-contained)

Repo root: C:\Users\Comp\superpowers (obra/superpowers). Workdir: C:\Users\Comp\superpowers\graphify-out.

## State
- chunk_00 DONE: .graphify_chunk_00.json (RELEASE-NOTES.md + 2 images; 11 nodes / 11 edges / 1 hyperedge).
- AST extraction DONE (632 nodes / 1075 edges) — see graphify skill for where it lives.
- REMAINING: chunks 01..49 (this dir: _chunklist_01.txt .. _chunklist_49.txt, _manifest.json).
  Chunk = one file per line (absolute path, verbatim). Packaged <=4000 words; single docs >4000 words
  (largest 10538) are solo chunks — proven safe (RELEASE-NOTES 13.7k passed as one subagent).

## How to dispatch (KV-safe)
- delegation.max_concurrent_children=1 and delegation.reasoning_effort=low are already set in
  C:\Users\Comp\AppData\Local\hermes\config.yaml. Do NOT raise concurrency: the local llama.cpp
  (Qwen3.8-27B @127.0.0.1:18434, ~4.9 GB free VRAM for KV) exhausts its KV cache under parallel
  subagents (error: "Context size has been exceeded" even at n_batch=1, shown by Hermes as
  "model server rejected this request as too large").
- Dispatch ONE subagent at a time via delegate_task (single task per call); wait for its result,
  verify, then next. Do not run this from a huge/compacting session — the main session's own
  prompt holds KV too (this session is why extraction runs from a fresh chat).
- After each subagent: verify .graphify_chunk_NN.json exists and parses:
    python -c "import json;d=json.load(open(r'C:\Users\Comp\superpowers\graphify-out\.graphify_chunk_NN.json'));print(len(d['nodes']),len(d['edges']))"
  Rules check: node ids ^[a-z0-9_]+$; edge confidence_score in {1.0,0.95,0.85,0.75,0.65,0.55} or 0.1-0.3;
  source_file = exact absolute path from the chunklist verbatim.
- On subagent failure: check tail of C:\Users\Comp\AppData\Local\hermes\logs\llama-server.log.
  KV error -> wait ~60 s, retry same chunk once. Jinja "reasoning effort" error -> config problem, report it.
  A chunk retried twice and failing: skip, note it, continue; report gaps at the end.

## Subagent goal template (fill NN and the hint line)
graphify extraction subagent. Read C:\Users\Comp\superpowers\graphify-out\_chunklist_NN.txt (one absolute path per line), read every listed file FULLY with read_file, extract a knowledge graph fragment, write the JSON to C:\Users\Comp\superpowers\graphify-out\.graphify_chunk_NN.json (create parent dir), and also print the full JSON to stdout. Output ONLY valid JSON, no fences/preamble, exact shape: {"nodes":[{"id":"...","label":"Human Readable Name","file_type":"code|document|paper|image|rationale|concept","source_file":"ABSOLUTE_PATH","source_location":null,"source_url":null,"captured_at":null,"author":null,"contributor":null}],"edges":[{"source":"node_id","target":"node_id","relation":"calls|implements|references|cites|conceptually_related_to|shares_data_with|semantically_similar_to|rationale_for","confidence":"EXTRACTED|INFERRED|AMBIGUOUS","confidence_score":1.0,"source_file":"ABSOLUTE_PATH","source_location":null,"weight":1.0}],"hyperedges":[{"id":"snake_case_id","label":"Human Readable Label","nodes":["id1","id2","id3"],"relation":"participate_in|implement|form","confidence":"EXTRACTED|INFERRED","confidence_score":0.75,"source_file":"ABSOLUTE_PATH"}],"input_tokens":0,"output_tokens":0} RULES: node id lowercase [a-z0-9_] only, format {stem}_{entity}; stem = repo-relative path (root C:\Users\Comp\superpowers) minus extension, segments joined with _, top-level files = filename stem only; entity = normalized symbol name; NO chunk/sequence suffixes. confidence_score REQUIRED on every edge: EXTRACTED=1.0 (explicit in source); INFERRED exactly one of 0.95/0.85/0.75/0.65/0.55 (never 0.5); AMBIGUOUS=0.1-0.3. Store rationale (WHY) as a rationale attribute on the node, not a separate node (file_type rationale for concept-like nodes, concept for named concepts). semantically_similar_to (INFERRED 0.6-0.95) only for non-obvious cross-file links. Hyperedges: max 3 per chunk, 3+ nodes, sparingly. YAML frontmatter: copy source_url/captured_at/author/contributor onto every node from that file. source_file = EXACT absolute path from the list VERBATIM. Keep tool calls efficient: read the chunklist, read each file (page with offset/limit only if >2000 lines), then write the JSON. HINT: {per-chunk hint from _manifest.json / file names}.

## After all 49 chunks are done
Load skill graphify (skill_view name=graphify) and follow its merge/finalize steps to combine
.graphify_chunk_00.json + 01..49 + AST into the final graph. Report final node/edge/community counts.
