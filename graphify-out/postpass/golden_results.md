# golden set results

PASS  P1 (positive): test-bootstrap-caching.mjs --validates--> V1_MAPPING (assertMappingConstants)
PASS  P2 (positive): test-bootstrap-caching.mjs --validates--> V2_MAPPING
PASS  P3 (positive): browser-launcher.test.js --imports--> server.cjs (require ../../skills/brainstorming/scripts/server.cjs)
PASS  P4 (positive): test-bump-version.sh --references--> scripts/bump-version.sh
PASS  P5 (positive): superpowers.js --contains--> V1_MAPPING
PASS  P6 (positive): doc 'subagent-driven-development SKILL.md' (worktree-rototill plan) --mentions--> skills/.../SKILL.md
PASS  N1 (negative): doc node (path=rototill.md) NOT same_as anything (mentions instead)
PASS  N2 (negative): file node NOT same_as section node (only contains)
PASS  N3 (negative): mentions out-degree per doc node <= 5 (max=1)
PASS  N4 (negative): no self-validates edge (local symbol not cross-validated)
PASS  P7 (positive): STOP (lifecycle.test.js L20) --references--> stop-server.sh file-node (path-string const)
PASS  P8 (positive): src (helper.test.js L15) --references--> helper.js file-node (fs.readFileSync)
PASS  P9 (positive): test-bootstrap-caching.sh --references--> cleanup_test_env (setup.sh L77) via source setup.sh
PASS  N5 (negative): concept 'executing plans' --NOT--> references (mentions only, never references)
PASS  N6 (negative): no references edge from a const pointing at a directory (repoRoot -> REPO dir, skipped)

Idempotency: re-run required -> see diff2_report.md (zero-diff check)