# post-pass diff report

- repo: C:/Users/Comp/superpowers
- sha: 5bf4e78011075bcfc0dc295f0724994cd123ee71
- extractor: postpass-ast:1
- input nodes: 1348 + created: 0
- input edges: 2663 (+0 duplicate-key merges)
- total edges after: 2663
- upsert skips (duplicate keys within this run): 539
- suppressed parallel duplicates (src,dst,relation already in graph): 271

## Added edges by relation

## v2 passes (path-refs / sh-source / strict concept-mentions)
- path-refs (const X = path.join/fs.readFileSync -> file node): 0
- sh-source (source X.sh + used symbol -> symbol node): 0
- concept-mentions (concept node -> EXISTING file node only, no phantoms): 0

## Created file-level nodes

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