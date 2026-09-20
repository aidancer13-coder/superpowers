# post-pass diff report

- repo: C:/Users/Comp/superpowers
- sha: 5bf4e78011075bcfc0dc295f0724994cd123ee71
- extractor: postpass-ast:1
- input nodes: 1348 + created: 13
- input edges: 2188 (+0 duplicate-key merges)
- total edges after: 2872
- upsert skips (duplicate keys within this run): 64

## Added edges by relation

### contains (+642)
- hermes_plugin___init -> hermes_plugin_init  [.hermes-plugin/__init__.py L1] 
- hermes_plugin___init -> hermes_plugin_init_build_bootstrap  [.hermes-plugin/__init__.py L40] 
- hermes_plugin___init -> hermes_plugin_init_rationale_9  [.hermes-plugin/__init__.py L9] 
- hermes_plugin___init -> hermes_plugin_init_register  [.hermes-plugin/__init__.py L74] 
- hermes_plugin___init -> hermes_plugin_init_register_pre_llm_call  [.hermes-plugin/__init__.py L91] 
- hermes_plugin___init -> hermes_plugin_init_skills_dir  [.hermes-plugin/__init__.py L8] 
- ... +636 more

### imports (+2)
- tests_brainstorm_server_browser_launcher_test -> skills_brainstorming_scripts_server  [tests/brainstorm-server/browser-launcher.test.js L4] 
- tests_brainstorm_server_browser_launcher_test -> skills_brainstorming_scripts_server_browserlauncherforplatform  [tests/brainstorm-server/browser-launcher.test.js L2] 

### mentions (+11)
- docs_superpowers_plans_2026_04_06_worktree_rototill_rewritten_finishing_skill -> skills_finishing_a_development_branch_skill_file  [plans/2026-04-06-worktree-rototill.md L1] label: Rewritten finishing-a-development-branch SKILL.md (Task 3)
- docs_superpowers_plans_2026_04_06_worktree_rototill_rewritten_using_git_worktrees_skill -> skills_using_git_worktrees_skill_file  [plans/2026-04-06-worktree-rototill.md L1] label: Rewritten using-git-worktrees SKILL.md (Task 2)
- docs_superpowers_plans_2026_07_06_sdd_plan_scoped_workspace_sdd_skill -> skills_subagent_driven_development_skill_file  [plans/2026-07-06-sdd-plan-scoped-workspace.md L1] label: subagent-driven-development SKILL.md
- gemini -> skills_using_superpowers_skill  [GEMINI.md L1] label: GEMINI.md (Gemini entry importing using-superpowers skill)
- skills_executing_plans_skill -> skills_executing_plans_skill_file  [plans/2026-04-06-worktree-rototill.md L1] label: executing-plans SKILL.md
- skills_finishing_a_development_branch_skill -> skills_finishing_a_development_branch_skill_file  [plans/2026-04-06-worktree-rototill.md L1] label: finishing-a-development-branch SKILL.md
- ... +5 more

### references (+22)
- tests_brainstorm_server_browser_launcher_test -> skills_brainstorming_scripts_server_browserlauncherforplatform  [tests/brainstorm-server/browser-launcher.test.js L26] 
- tests_brainstorm_server_helper_test -> skills_brainstorming_scripts_helper_nextreconnectdelay  [tests/brainstorm-server/helper.test.js L46] 
- tests_brainstorm_server_start_server_test -> skills_brainstorming_scripts_start_server  [tests/brainstorm-server/start-server.test.sh L7] 
- tests_brainstorm_server_stop_server_test -> skills_brainstorming_scripts_stop_server  [tests/brainstorm-server/stop-server.test.sh L10] 
- tests_brainstorm_server_stop_server_test -> skills_brainstorming_scripts_server  [tests/brainstorm-server/stop-server.test.sh L11] 
- tests_brainstorm_server_windows_lifecycle_test -> skills_brainstorming_scripts_start_server  [tests/brainstorm-server/windows-lifecycle.test.sh L23] 
- ... +16 more

### validates (+7)
- tests_brainstorm_server_helper_test -> skills_brainstorming_scripts_helper_nextreconnectdelay  [tests/brainstorm-server/helper.test.js L33] 
- tests_brainstorm_server_ws_protocol_test -> skills_brainstorming_scripts_server_computeacceptkey  [tests/brainstorm-server/ws-protocol.test.js L55] 
- tests_brainstorm_server_ws_protocol_test -> skills_brainstorming_scripts_server_opcodes  [tests/brainstorm-server/ws-protocol.test.js L185] 
- tests_brainstorm_server_ws_protocol_test -> skills_brainstorming_scripts_server_decodeframe  [tests/brainstorm-server/ws-protocol.test.js L259] 
- tests_hermes_test_bootstrap -> hermes_plugin_init_strip_frontmatter  [tests/hermes/test_bootstrap.py L33] 
- tests_opencode_test_bootstrap_caching -> opencode_plugins_superpowers_v1_mapping  [tests/opencode/test-bootstrap-caching.mjs L171] assertMappingConstants: if (typeof mod.V1_MAPPING !== 'string' || type
- ... +1 more

## Created file-level nodes
- tests_opencode_test_bootstrap_caching  (tests/opencode/test-bootstrap-caching.mjs)
- tests_opencode_test_session_bootstrap  (tests/opencode/test-session-bootstrap.mjs)
- hermes_plugin___init  (.hermes-plugin/__init__.py)
- tests_hermes___init  (tests/hermes/__init__.py)
- tests_opencode_test_bootstrap_caching_file  (tests/opencode/test-bootstrap-caching.sh)
- tests_opencode_test_session_bootstrap_file  (tests/opencode/test-session-bootstrap.sh)
- tests_opencode_test_skill_registration  (tests/opencode/test-skill-registration.mjs)
- tests_opencode_test_skill_registration_file  (tests/opencode/test-skill-registration.sh)
- skills_finishing_a_development_branch_skill_file  (skills/finishing-a-development-branch/SKILL.md)
- skills_using_git_worktrees_skill_file  (skills/using-git-worktrees/SKILL.md)
- skills_subagent_driven_development_skill_file  (skills/subagent-driven-development/SKILL.md)
- skills_executing_plans_skill_file  (skills/executing-plans/SKILL.md)
- skills_writing_plans_skill_file  (skills/writing-plans/SKILL.md)

## same_as
- added: 0
- rejected (doc-label names code file, different path -> mentions instead): 17
  - docs_superpowers_specs_2026_08_27_diagnosing_superpowers_design_spec ~ .opencode/plugins/superpowers.js
  - docs_porting_to_a_new_harness ~ .opencode/plugins/superpowers.js
  - docs_superpowers_plans_2026_05_06_lift_drill_into_evals_document ~ .opencode/plugins/superpowers.js
  - agents ~ .opencode/plugins/superpowers.js
  - gemini ~ .opencode/plugins/superpowers.js
  - release_notes ~ .opencode/plugins/superpowers.js
  - skills_diagnosing_superpowers_skill ~ .opencode/plugins/superpowers.js
  - skills_diagnosing_superpowers_templates_case ~ .opencode/plugins/superpowers.js
  - skills_diagnosing_superpowers_templates_issue ~ .opencode/plugins/superpowers.js
  - skills_diagnosing_superpowers_templates_report ~ .opencode/plugins/superpowers.js

## retargeted edges
- 0 (no node merges this pass; same_as only links, never rewrites)