#!/usr/bin/env python3
"""graphify post-pass: deterministic gids + upsert + AST edges (imports/references/validates)
+ same_as/contains/mentions + provenance + golden set + 50x deg=1 labeling.
Idempotent: re-running on its own output yields zero diff.

Determinism: all iterations sorted, stable sha256 gids, RNG seed 42.
gid = sha256(repo \t sha \t path \t kind \t symbol)[:16]
edge key = (src_gid, dst_gid, relation, provenance_tag)
provenance per edge: {extractor, version, source, lines, sha}
"""
import json, re, os, hashlib, random, sys
from collections import defaultdict, Counter

REPO = "C:/Users/Comp/superpowers"
OUT = os.path.join(REPO, "graphify-out", "postpass")
GRAPH = os.path.join(OUT, "graph.json")
SHA = sys.argv[1] if len(sys.argv) > 1 else "5bf4e78011075bcfc0dc295f0724994cd123ee71"
EXTRACTOR = "postpass-ast"
VERSION = 1
TAG = f"{EXTRACTOR}:{VERSION}"
CODE_EXTS = (".py", ".js", ".mjs", ".cjs", ".sh")
DOC_EXTS = (".md",)

def norm_id(s):
    return re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_")

def rel(path):
    p = path.replace("\\", "/")
    pre = REPO.replace("\\", "/") + "/"
    return p[len(pre):] if p.startswith(pre) else p

def stem_full(path):
    r = rel(path)
    return norm_id(r.rsplit(".", 1)[0])

def file_gid(path, ftype="code"):
    return hashlib.sha256(f"{REPO}\t{SHA}\t{rel(path)}\tfile\t{ftype}".encode()).hexdigest()[:16]

def symbol_gid(path, kind, symbol):
    return hashlib.sha256(f"{REPO}\t{SHA}\t{rel(path)}\t{kind}\t{symbol}".encode()).hexdigest()[:16]

def concept_gid(symbol):
    return hashlib.sha256(f"{REPO}\t{SHA}\t\tconcept\t{symbol}".encode()).hexdigest()[:16]

def prov(source, lines, tag=TAG):
    return {"extractor": EXTRACTOR, "version": VERSION, "source": source, "lines": lines, "sha": SHA}

g = json.load(open(GRAPH, encoding="utf-8"))
nodes, links = g["nodes"], g["links"]

# ---------- 1. assign gids ----------
gid_of = {}          # legacy id -> gid
legacy_by_gid = {}
# index helpers (source_file in graph is RELATIVE; normalize to absolute)
def abs_of(sf):
    sf = (sf or "").replace("\\", "/")
    if not sf:
        return ""
    if sf.startswith(REPO + "/") or sf.lower().startswith("c:"):
        return sf
    return REPO + "/" + sf.lstrip("/")

node_by_gid = {}
for n in nodes:
    nid = n["id"]
    sf = abs_of(n.get("source_file"))
    loc = n.get("source_location")
    if sf and n["id"] == stem_full(sf) + "_file":
        gid = file_gid(sf, n.get("file_type") or "code")
    elif sf:
        if nid == stem_full(sf):
            gid = file_gid(sf, n.get("file_type") or "code")
        elif loc:
            kind = "symbol" if n.get("file_type") == "code" else "section"
            gid = symbol_gid(sf, kind, nid)
        else:
            gid = symbol_gid(sf, "doc", nid)
    else:
        gid = concept_gid(nid)
    gid_of[nid] = gid
    legacy_by_gid[gid] = nid
    n["gid"] = gid
    n["legacy_id"] = nid
    node_by_gid[gid] = n

by_file = defaultdict(list)
for n in nodes:
    sf = abs_of(n.get("source_file"))
    if sf:
        by_file[sf].append(n)

legacy_used = {n["id"] for n in nodes}

# ---------- 2. collect repo files ----------
files = {}
for root, dirs, fnames in os.walk(REPO):
    dirs[:] = [d for d in sorted(dirs) if d not in (".git", "node_modules", "graphify-out", ".opencode") or d == ".opencode"]
    for f in sorted(fnames):
        if f.endswith(CODE_EXTS) or f.endswith(DOC_EXTS):
            full = os.path.join(root, f).replace("\\", "/")
            files[full] = f
# ensure .opencode included
op = os.path.join(REPO, ".opencode")
for root, dirs, fnames in os.walk(op):
    for f in sorted(fnames):
        if f.endswith(CODE_EXTS):
            full = os.path.join(root, f).replace("\\", "/")
            files[full] = f

def file_node(sf, ftype="code", label=None):
    """existing file-level node or None"""
    for n in by_file.get(sf, []):
        if n["id"] == stem_full(sf):
            return n
    return None

created_nodes = []
def ensure_file_node(sf, ftype="code"):
    sf = abs_of(sf)
    n = file_node(sf, ftype)
    if n:
        return n["gid"]
    gid = file_gid(sf, ftype)
    if gid in node_by_gid:
        return gid
    base = sf.rsplit("/", 1)[-1]
    stem = stem_full(sf)
    nid = stem if stem not in legacy_used else stem + "_file"  # deterministic tiebreak
    node = {
        "id": nid, "gid": gid, "legacy_id": nid, "label": base,
        "file_type": ftype, "source_file": sf, "source_location": None,
        "source_url": None, "captured_at": None, "author": None, "contributor": None,
        "community": None, "community_name": None, "_origin": "postpass", "_filenode": True,
    }
    nodes.append(node)
    by_file[sf].append(node)
    node_by_gid[gid] = node
    legacy_by_gid[gid] = nid
    legacy_used.add(nid)
    gid_of[nid] = gid
    created_nodes.append(node)
    return gid

# ---------- 3. edge store with upsert ----------
edge_map = {}   # (legacy_src, legacy_dst, relation, tag) -> edge
merged_existing = 0
skipped_dangling = 0
for e in links:
    if e["source"] not in gid_of or e["target"] not in gid_of:
        skipped_dangling += 1
        continue
    s, t = gid_of[e["source"]], gid_of[e["target"]]
    pr = e.get("provenance") or {}
    if pr.get("extractor") == EXTRACTOR:
        tag = f"{EXTRACTOR}:{pr.get('version', VERSION)}"
    else:
        tag = "graphify-ast:1" if e.get("_origin") == "ast" else "graphify-llm:1"
    key = (e["source"], e["target"], e["relation"], tag)
    if key in edge_map:
        merged_existing += 1
        continue
    e2 = dict(e)
    e2["gid_source"], e2["gid_target"] = s, t
    e2["provenance"] = e.get("provenance") or {"extractor": "graphify", "version": 1,
                        "source": e.get("source_file"), "lines": e.get("source_location"),
                        "sha": SHA}
    edge_map[key] = e2

additions = defaultdict(list)
upsert_skips = 0
def add_edge(src_gid, dst_gid, relation, source, lines, tag=TAG, weight=1.0, conf="EXTRACTED", score=1.0, context=""):
    global upsert_skips
    if src_gid == dst_gid:
        return False  # no self-edges
    key = (legacy_by_gid[src_gid], legacy_by_gid[dst_gid], relation, tag)  # key on legacy ids -> idempotent
    if key in edge_map:
        upsert_skips += 1
        return False
    e = {"source": legacy_by_gid[src_gid], "target": legacy_by_gid[dst_gid],
         "gid_source": src_gid, "gid_target": dst_gid,
         "relation": relation, "confidence": conf, "confidence_score": score,
         "weight": weight, "source_file": source, "source_location": lines,
         "provenance": prov(source, lines, tag), "context": context}
    edge_map[key] = e
    additions[relation].append(e)
    return True

# ---------- 4. symbol index from code files ----------
file_text = {}
def text_of(sf):
    if sf not in file_text:
        try:
            file_text[sf] = open(sf, encoding="utf-8", errors="replace").read()
        except Exception:
            file_text[sf] = None
    return file_text[sf]

exports = defaultdict(set)     # file -> exported symbol names
funcdefs = defaultdict(set)    # file -> defined function names
sym_file = {}                  # symbol name -> file (first, for cross-file detection)
sym_files = defaultdict(set)   # symbol name -> ALL files defining it
NAME = r"[A-Za-z_$][A-Za-z0-9_$]*"

for sf in sorted(files):
    if not sf.endswith(CODE_EXTS):
        continue
    t = text_of(sf)
    if not t:
        continue
    ext = sf.rsplit(".", 1)[-1]
    if ext in ("js", "mjs", "cjs"):
        for m in re.finditer(r"export\s+const\s+(" + NAME + r")\b", t):
            exports[sf].add(m.group(1))
        for m in re.finditer(r"export\s+function\s+(" + NAME + r")\b", t):
            exports[sf].add(m.group(1))
            funcdefs[sf].add(m.group(1))
        for m in re.finditer(r"export\s*\{([^}]+)\}", t):
            for part in m.group(1).split(","):
                p = part.strip()
                if p:
                    exports[sf].add(p.split(" as ")[-1].strip())
        for m in re.finditer(r"module\.exports\.(" + NAME + r")\b", t):
            exports[sf].add(m.group(1))
        for m in re.finditer(r"module\.exports\s*=\s*\{([^}]+)\}", t):
            for part in m.group(1).split(","):
                p = part.strip()
                if p:
                    exports[sf].add(p.split(":")[0].strip().split(" as ")[-1].strip())
        for m in re.finditer(r"^(?:const|let|var)\s+(" + NAME + r")\s*=\s*(?:function|\()", t, re.M):
            funcdefs[sf].add(m.group(1))
        for m in re.finditer(r"^function\s+(" + NAME + r")\b", t, re.M):
            funcdefs[sf].add(m.group(1))
    elif ext == "sh":
        for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{", t, re.M):
            funcdefs[sf].add(m.group(1))
    elif ext == "py":
        for m in re.finditer(r"^(def|class)\s+(" + NAME + r")\b", t, re.M):
            funcdefs[sf].add(m.group(2))
            if not m.group(2).startswith("_"):
                exports[sf].add(m.group(2))
        for m in re.finditer(r"^([A-Z][A-Z0-9_]*)\s*=", t, re.M):
            exports[sf].add(m.group(1))
        # private defs are still module-internal API (e.g. _strip_frontmatter) — index them
        for s in list(funcdefs[sf]):
            exports[sf].add(s)
    for s in list(exports[sf]):
        if len(s) > 2:
            sym_files[s].add(sf)
            if s not in sym_file:
                sym_file[s] = sf

# ---------- 5. extract edges per file ----------
imp_edges = ref_edges = val_edges = 0
test_file = lambda sf: rel(sf).startswith("tests/")

def js_imports(sf, t):
    """yield (line, target_path, [symbols])"""
    d = os.path.dirname(sf)
    out = []
    for m in re.finditer(r"import\s+(?:([A-Za-z_$][A-Za-z0-9_$]*)\s+from\s+)?\{?([^'\";]+)?\}?\s*from\s*['\"]([^'\"]+)['\"]", t):
        pass
    # simpler, line-oriented
    for i, line in enumerate(t.splitlines(), 1):
        lm = re.search(r"import\s+(?:([A-Za-z_$][A-Za-z0-9_$]*)\s+from\s+|\{([^}]*)\}\s*from\s+|)\s*['\"](\.[^'\"]+)['\"]", line)
        if lm:
            syms = [s.strip().split(" as ")[0] for s in (lm.group(2) or "").split(",") if s.strip()] if lm.group(2) else ([lm.group(1)] if lm.group(1) else [])
            out.append((i, lm.group(3), syms))
            continue
        rm = re.search(r"require\(\s*['\"](\.[^'\"]+)['\"]\s*\)", line)
        if rm:
            out.append((i, rm.group(1), []))
            continue
        dm = re.search(r"import\(\s*['\"](\.[^'\"]+)['\"]\s*\)", line)
        if dm:
            out.append((i, dm.group(1), []))
    # multi-line require destructure: const { a, b } = require('...')
    for m in re.finditer(r"const\s*\{([^}]+)\}\s*=\s*require\(\s*['\"](\.[^'\"]+)['\"]\s*\)", t):
        ln = t[:m.start()].count("\n") + 1
        out.append((ln, m.group(2), [s.strip() for s in m.group(1).split(",") if s.strip()]))
    return out

def resolve(d, p):
    full = os.path.normpath(os.path.join(d, p)).replace("\\", "/")
    if full in files:
        return full
    for cand in (full, full + ".js", full + ".cjs", full + ".mjs", os.path.join(full, "index.js")):
        if cand in files:
            return cand
    return None

for sf in sorted(files):
    if not sf.endswith(CODE_EXTS):
        continue
    t = text_of(sf)
    if not t:
        continue
    ext = sf.rsplit(".", 1)[-1]
    d = os.path.dirname(sf)
    is_test = test_file(sf)
    src_gid = None  # file-level source for import edges

    if ext in ("js", "mjs", "cjs"):
        # imports
        for ln, p, syms in js_imports(sf, t):
            tgt = resolve(d, p)
            if not tgt:
                continue
            src_gid = ensure_file_node(sf)
            tgt_gid = ensure_file_node(tgt)
            imp_edges += add_edge(src_gid, tgt_gid, "imports", sf, f"L{ln}") or 0
            for s in syms:
                if s in sym_file and sym_file[s] == tgt:
                    s_gid = symbol_gid(tgt, "symbol", norm_id(stem_full(tgt) + "_" + s))
                    # target symbol node may exist in graph under different legacy id; find by file+label
                    sn = None
                    for n in by_file.get(tgt, []):
                        if n.get("file_type") == "code" and n["id"].endswith("_" + norm_id(s)):
                            sn = n
                            break
                    if sn is None and s_gid in node_by_gid:
                        sn = node_by_gid[s_gid]
                    if sn:
                        add_edge(src_gid, sn["gid"], "imports", sf, f"L{ln}")
        # validate / reference from test functions
        if is_test:
            # find function bodies
            for fm in re.finditer(r"function\s+(" + NAME + r")\s*\(([^)]*)\)\s*\{", t):
                fname = fm.group(1)
                start = t.index("{", fm.start())
                depth, i = 0, start
                while i < len(t):
                    if t[i] == "{":
                        depth += 1
                    elif t[i] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    i += 1
                body = t[start:i + 1]
                lname = fname.lower()
                looks_assert = bool(re.search(r"assert\.|failures\.push|expect\(|strictEqual|deepEqual|process\.exit|throw new Error|!==|===", body))
                is_test_fn = (re.search(r"assert|expect|check|verify|test", lname) is not None) or looks_assert
                if not is_test_fn:
                    continue
                body_lines = t[:start].count("\n") + 1
                for s, tfile in sorted(sym_file.items()):
                    if tfile == sf or test_file(tfile):
                        continue
                    pat = r"(?<![A-Za-z0-9_$])" + re.escape(s) + r"(?![A-Za-z0-9_$])"
                    for bm in re.finditer(pat, body):
                        line_start = body.rfind("\n", 0, bm.start()) + 1
                        line_end = body.find("\n", bm.end())
                        line = body[line_start:line_end if line_end > 0 else len(body)]
                        ln = body_lines + body[:bm.start()].count("\n")
                        in_assert = bool(re.search(r"assert|expect|failures\.push|typeof|===|!==|\.includes\(", line))
                        # find target node for symbol
                        sn = None
                        for n in by_file.get(tfile, []):
                            if n.get("file_type") == "code" and n["id"].endswith("_" + norm_id(s)):
                                sn = n
                                break
                        if sn is None:
                            sn = node_by_gid.get(symbol_gid(tfile, "symbol", norm_id(stem_full(tfile) + "_" + s)))
                        if sn is None:
                            continue
                        src_gid = ensure_file_node(sf)
                        rel2 = "validates" if in_assert else "references"
                        if in_assert:
                            val_edges += add_edge(src_gid, sn["gid"], rel2, sf, f"L{ln}", context=f"{fname}: {line.strip()[:80]}") or 0
                        else:
                            ref_edges += add_edge(src_gid, sn["gid"], rel2, sf, f"L{ln}", context=f"{fname}: {line.strip()[:80]}") or 0
                        break  # one edge per symbol per function
            # top-level test() calls (cjs): test('name', () => { ... })
            for tm in re.finditer(r"\btest\(\s*['\"][^'\"]*['\"]\s*,\s*(?:async\s*)?(?:function|\()", t):
                start = t.find("{", tm.end() - 1)
                if start < 0:
                    continue
                depth, i = 0, start
                while i < len(t):
                    if t[i] == "{":
                        depth += 1
                    elif t[i] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    i += 1
                body = t[start:i + 1]
                body_lines = t[:start].count("\n") + 1
                for s, tfile in sorted(sym_file.items()):
                    if tfile == sf or test_file(tfile):
                        continue
                    pat = r"(?<![A-Za-z0-9_$])" + re.escape(s) + r"(?![A-Za-z0-9_$])"
                    bm = re.search(pat, body)
                    if not bm:
                        continue
                    line_start = body.rfind("\n", 0, bm.start()) + 1
                    line_end = body.find("\n", bm.end())
                    line = body[line_start:line_end if line_end > 0 else len(body)]
                    ln = body_lines + body[:bm.start()].count("\n")
                    in_assert = bool(re.search(r"assert|expect|===|!==|\.includes\(|strictEqual", line))
                    sn = None
                    for n in by_file.get(tfile, []):
                        if n.get("file_type") == "code" and n["id"].endswith("_" + norm_id(s)):
                            sn = n
                            break
                    if sn is None:
                        sn = node_by_gid.get(symbol_gid(tfile, "symbol", norm_id(stem_full(tfile) + "_" + s)))
                    if sn is None:
                        continue
                    src_gid = ensure_file_node(sf)
                    rel2 = "validates" if in_assert else "references"
                    if in_assert:
                        val_edges += add_edge(src_gid, sn["gid"], rel2, sf, f"L{ln}") or 0
                    else:
                        ref_edges += add_edge(src_gid, sn["gid"], rel2, sf, f"L{ln}") or 0

    elif ext == "sh":
        # references: repo path literals
        for i, line in enumerate(t.splitlines(), 1):
            for pm in re.finditer(r"((?:\$\(?\w*(?:ROOT|DIR)\w*\)?/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.(?:sh|js|mjs|cjs|py))", line):
                cand = pm.group(1)
                if "$" in cand.split("/")[0] or cand.startswith("."):
                    base = cand.rsplit("/", 1)[-1]
                    # try resolve as repo-root relative or test-dir relative
                    tgt = None
                    for pref in (REPO + "/", d + "/", REPO + "/tests/"):
                        if (pref + cand) in files:
                            tgt = pref + cand
                            break
                    if tgt is None:
                        for f in files:
                            if f.rsplit("/", 1)[-1] == base and (cand in f or base in os.path.basename(f)):
                                if "scripts/" in cand and "scripts/" in f:
                                    tgt = f
                                    break
                    if tgt is None:
                        continue
                    if tgt == sf:
                        continue  # self-reference (usage string) — not an edge
                    src_gid = ensure_file_node(sf)
                    tgt_gid = ensure_file_node(tgt)
                    ref_edges += add_edge(src_gid, tgt_gid, "references", sf, f"L{i}") or 0

    elif ext == "py":
        # imports
        for i, line in enumerate(t.splitlines(), 1):
            im = re.match(r"\s*(?:from\s+([A-Za-z_][\w.]*)\s+import\s+.+|import\s+([A-Za-z_][\w.]*))", line)
            if not im:
                continue
            modname = (im.group(1) or im.group(2)).split(".")[-1]
            tgt = None
            for f in files:
                base = f.rsplit("/", 1)[-1]
                if base == modname + ".py" or base == "__init__.py" and ".hermes-plugin" in f and modname in ("__init__", "plugin"):
                    if ".hermes-plugin" in f or d in f:
                        tgt = f
                        break
            if tgt and tgt != sf:
                src_gid = ensure_file_node(sf)
                tgt_gid = ensure_file_node(tgt)
                imp_edges += add_edge(src_gid, tgt_gid, "imports", sf, f"L{i}") or 0
        # test functions: def test_* / def assert_*
        for fm in re.finditer(r"^\s*(?:async\s+)?def\s+(" + NAME + r")\s*\(", t, re.M):
            fname = fm.group(1)
            if not re.search(r"test|assert|check|expect", fname.lower()):
                continue
            start = t.find(":", fm.end())
            # find block by indent
            ind = len(t[fm.start():fm.end()]) - len(t[fm.start():fm.end()].lstrip())
            body_start = t.find("\n", start) + 1
            depth_end = len(t)
            for j in range(body_start, len(t), 1):
                if t[j] == "\n":
                    line = t[j + 1:]
                    if line.strip() and (len(line) - len(line.lstrip())) <= ind:
                        depth_end = j
                        break
            body = t[body_start:depth_end]
            body_lines = t[:body_start].count("\n") + 1
            for s, tfile in sorted(sym_file.items()):
                if tfile == sf or test_file(tfile):
                    continue
                pat = r"(?<![A-Za-z0-9_])" + re.escape(s) + r"(?![A-Za-z0-9_])"
                bm = re.search(pat, body)
                if not bm:
                    continue
                line_start = body.rfind("\n", 0, bm.start()) + 1
                line_end = body.find("\n", bm.end())
                line = body[line_start:line_end if line_end > 0 else len(body)]
                ln = body_lines + body[:bm.start()].count("\n")
                in_assert = line.strip().startswith("assert") or re.search(r"assert\s|expect", line)
                sn = None
                for n in by_file.get(tfile, []):
                    if n.get("file_type") == "code" and n["id"].endswith("_" + norm_id(s)):
                        sn = n
                        break
                if sn is None:
                    continue
                src_gid = ensure_file_node(sf)
                rel2 = "validates" if in_assert else "references"
                if in_assert:
                    val_edges += add_edge(src_gid, sn["gid"], rel2, sf, f"L{ln}") or 0
                else:
                    ref_edges += add_edge(src_gid, sn["gid"], rel2, sf, f"L{ln}") or 0

# ---------- 6. contains: file -> section/symbol ----------
contains_added = 0
for sf in sorted(set(list(by_file.keys()))):
    stem = stem_full(sf)
    fn = file_node(sf)
    if fn is None:
        # only create file node if the file is a code file with section nodes
        if sf.endswith(CODE_EXTS):
            ensure_file_node(sf)
        else:
            continue
    fn_gid = file_node(sf)["gid"] if file_node(sf) else file_gid(sf)
    for n in sorted(by_file[sf], key=lambda x: x["id"]):
        if n["id"] == stem:
            continue
        if not n.get("source_location"):
            continue
        contains_added += add_edge(fn_gid, n["gid"], "contains", sf, n.get("source_location")) or 0

# ---------- 7. same_as: same (repo, sha, path, kind=file) ----------
same_as_added = same_as_rejected = 0
file_groups = defaultdict(list)
for n in nodes:
    sf = abs_of(n.get("source_file"))
    if sf and n.get("file_type") in ("code", "document") and (n["id"] == stem_full(sf) or n["id"] == stem_full(sf) + "_file"):
        file_groups[(sf, n.get("file_type"))].append(n)
for key, grp in sorted(file_groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    if len(grp) < 2:
        continue
    for a, b in zip(grp, grp[1:]):
        same_as_added += add_edge(a["gid"], b["gid"], "same_as", key[0], "L1") or 0
# rejection audit: doc nodes whose LABEL names a code file but path differs -> NOT same_as (mentions instead)
same_as_rejected_list = []
for n in nodes:
    if n.get("file_type") != "document" or n.get("source_location"):
        continue
    lbl = n.get("label", "")
    for sf in sorted(files):
        if sf.endswith(CODE_EXTS) and sf != (n.get("source_file") or ""):
            base = sf.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if len(base) >= 8 and base.replace("_", "-").lower() in lbl.lower():
                same_as_rejected_list.append((n["id"], sf))
                break

# ---------- 8. mentions: doc node -> file it names (no merge, only a link) ----------
mentions_added = 0
doc_nodes = [n for n in nodes if n.get("file_type") in ("document", "paper", "rationale")
             and (not n.get("source_location") or not str(n.get("source_location")).startswith("L"))]
stem_lookup = {}   # dash-flat key -> sf (all file kinds; SKILL -> skill)
for sf in sorted(files):
    r = rel(sf).rsplit(".", 1)[0]
    segs = r.split("/")
    if segs[-1].upper() == "SKILL":
        segs = segs[:-1] + ["skill"]
    flat = "-".join(s.replace("_", "-") for s in segs)
    stem_lookup[flat] = sf
    if len(segs) > 1:                       # also key without first path segment
        stem_lookup["-".join(s.replace("_", "-") for s in segs[1:])] = sf
for n in sorted(doc_nodes, key=lambda x: x["id"]):
    lbl = re.sub(r"[^a-z0-9 .-]+", " ", (n.get("label") or "").lower()).strip().replace(" ", "-")
    if not lbl:
        continue
    my_sf = abs_of(n.get("source_file"))
    hits = []
    for key, sf in sorted(stem_lookup.items()):
        if sf == my_sf or len(key) < 12:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", lbl):
            hits.append(sf)
    for sf in hits[:5]:                     # cap: 5 per doc node
        src_gid = n["gid"]
        tgt_gid = ensure_file_node(sf)
        if tgt_gid == src_gid:
            continue
        mentions_added += add_edge(src_gid, tgt_gid, "mentions", n.get("source_file") or n["id"], "L1",
                                   context=f"label: {(n.get('label') or '')[:60]}") or 0

# ---------- 9. golden set ----------
def gid_of_legacy(nid):
    return gid_of.get(nid)

def find_node(pred):
    for n in nodes:
        if pred(n):
            return n
    return None

def edge_exists(src_leg, dst_leg, relation):
    if not src_leg or not dst_leg:
        return False
    for (a, b, r, tag), e in edge_map.items():
        if {a, b} == {src_leg, dst_leg} and r == relation:
            return True
    return False

test_bcache = "C:/Users/Comp/superpowers/tests/opencode/test-bootstrap-caching.mjs"
plugin_js = "C:/Users/Comp/superpowers/.opencode/plugins/superpowers.js"
v1 = find_node(lambda n: n.get("source_file") and "plugins/superpowers.js" in n["source_file"].replace("\\", "/") and n["id"].endswith("v1_mapping"))
v2 = find_node(lambda n: n.get("source_file") and "plugins/superpowers.js" in n["source_file"].replace("\\", "/") and n["id"].endswith("v2_mapping"))
tbc_leg = stem_full(test_bcache)
plugin_leg = stem_full(plugin_js)
sdd_skill_file = "C:/Users/Comp/superpowers/skills/subagent-driven-development/SKILL.md"
doc_skill = find_node(lambda n: n["id"] == "skills_subagent_driven_development_skill")
sdd_file_leg = stem_full(sdd_skill_file)
server_cjs = "C:/Users/Comp/superpowers/skills/brainstorming/scripts/server.cjs"
bl_test = "C:/Users/Comp/superpowers/tests/brainstorm-server/browser-launcher.test.js"
bump_sh = "C:/Users/Comp/superpowers/scripts/bump-version.sh"
tb_test = "C:/Users/Comp/superpowers/tests/version-bump/test-bump-version.sh"

golden = []
def G(name, kind, ok, detail):
    golden.append({"name": name, "kind": kind, "ok": bool(ok), "detail": detail})

G("P1", "positive", v1 and edge_exists(tbc_leg, v1["id"], "validates"), f"test-bootstrap-caching.mjs --validates--> V1_MAPPING (assertMappingConstants)")
G("P2", "positive", v2 and edge_exists(tbc_leg, v2["id"], "validates"), f"test-bootstrap-caching.mjs --validates--> V2_MAPPING")
G("P3", "positive", edge_exists(stem_full(bl_test), stem_full(server_cjs), "imports"), "browser-launcher.test.js --imports--> server.cjs (require ../../skills/brainstorming/scripts/server.cjs)")
G("P4", "positive", edge_exists(stem_full(tb_test), stem_full(bump_sh), "references"), "test-bump-version.sh --references--> scripts/bump-version.sh")
G("P5", "positive", v1 and edge_exists(plugin_leg, v1["id"], "contains"), "superpowers.js --contains--> V1_MAPPING")
sdd_file_node = node_by_gid.get(file_gid(sdd_skill_file))
G("P6", "positive", doc_skill and sdd_file_node and edge_exists(doc_skill["id"], sdd_file_node["legacy_id"], "mentions"), "doc 'subagent-driven-development SKILL.md' (worktree-rototill plan) --mentions--> skills/.../SKILL.md")
G("N1", "negative", doc_skill and not any(e["relation"] == "same_as" and doc_skill["gid"] in (e["gid_source"], e["gid_target"]) for e in edge_map.values()), "doc node (path=rototill.md) NOT same_as anything (mentions instead)")
G("N2", "negative", v1 and not edge_exists(plugin_leg, v1["id"], "same_as"), "file node NOT same_as section node (only contains)")
G("N3", "negative", all(v <= 5 for v in Counter(e["gid_source"] for e in edge_map.values() if e["relation"] == "mentions").values()), f"mentions out-degree per doc node <= 5 (max={max((v for v in Counter(e['gid_source'] for e in edge_map.values() if e['relation'] == 'mentions').values()), default=0)})")
G("N4", "negative", not any(e["relation"] == "validates" and e["gid_source"] == e["gid_target"] for e in edge_map.values()), "no self-validates edge (local symbol not cross-validated)")
golden_neg5 = None  # idempotency checked after re-run

# ---------- 10. write output ----------
new_links = []
for e in edge_map.values():
    new_links.append(e)
g["links"] = sorted(new_links, key=lambda e: (e["gid_source"], e["gid_target"], e["relation"]))
g["provenance_meta"] = {"postpass": TAG, "repo": REPO, "sha": SHA, "edge_key": "(src_gid, dst_gid, relation, provenance_tag)"}
json.dump(g, open(GRAPH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------- 11. diff report ----------
lines = []
lines.append("# post-pass diff report\n")
lines.append(f"- repo: {REPO}")
lines.append(f"- sha: {SHA}")
lines.append(f"- extractor: {TAG}")
lines.append(f"- input nodes: {len([n for n in nodes if n.get('_origin') != 'postpass'])} + created: {len(created_nodes)}")
lines.append(f"- input edges: {len(links)} (+{merged_existing} duplicate-key merges)")
lines.append(f"- total edges after: {len(edge_map)}")
lines.append(f"- upsert skips (duplicate keys within this run): {upsert_skips}")
lines.append("")
lines.append("## Added edges by relation")
for r in sorted(additions):
    lines.append(f"\n### {r} (+{len(additions[r])})")
    for e in additions[r][:6]:
        lines.append(f"- {e['source']} -> {e['target']}  [{e['source_file'].split('superpowers/')[-1]} {e['source_location']}] {e.get('context','')[:70]}")
    if len(additions[r]) > 6:
        lines.append(f"- ... +{len(additions[r])-6} more")
lines.append("\n## Created file-level nodes")
for n in created_nodes:
    lines.append(f"- {n['id']}  ({rel(n['source_file'])})")
lines.append("\n## same_as")
lines.append(f"- added: {same_as_added}")
lines.append(f"- rejected (doc-label names code file, different path -> mentions instead): {len(same_as_rejected_list)}")
for nid, sf in same_as_rejected_list[:10]:
    lines.append(f"  - {nid} ~ {rel(sf)}")
lines.append("\n## retargeted edges")
lines.append("- 0 (no node merges this pass; same_as only links, never rewrites)")
open(os.path.join(OUT, "diff_report.md"), "w", encoding="utf-8").write("\n".join(lines))

# ---------- 12. golden results ----------
gl = ["# golden set results\n"]
for x in golden:
    gl.append(f"{'PASS' if x['ok'] else 'FAIL'}  {x['name']} ({x['kind']}): {x['detail']}")
gl.append("\nIdempotency (N5): re-run required -> see diff2_report.md")
open(os.path.join(OUT, "golden_results.md"), "w", encoding="utf-8").write("\n".join(gl))

# ---------- 13. 50 deg=1 labeling (stable across runs: original degree, non-postpass edges only) ----------
from collections import Counter as C
deg = defaultdict(int)
for e in edge_map.values():
    if (e.get("provenance") or {}).get("extractor") == EXTRACTOR:
        continue
    deg[e["gid_source"]] += 1
    deg[e["gid_target"]] += 1
d1 = [n for n in nodes if deg[n["gid"]] == 1 and n.get("_origin") != "postpass"]
random.seed(42)
sample = random.sample(sorted(d1, key=lambda x: x["gid"]), 50)
lab = []
pp_edges_all = [e for e in edge_map.values() if (e.get("provenance") or {}).get("extractor") == EXTRACTOR]
for n in sample:
    gid = n["gid"]
    inc = [e for e in edge_map.values() if gid in (e["gid_source"], e["gid_target"])]
    e = inc[0]
    other_gid = e["gid_target"] if e["gid_source"] == gid else e["gid_source"]
    other = node_by_gid[other_gid]
    new_edges = [x for x in pp_edges_all if gid in (x["gid_source"], x["gid_target"])]
    if new_edges:
        cls = "missing_edge"
        x0 = new_edges[0]
        other_leg = legacy_by_gid[x0["gid_target"] if x0["gid_source"] == gid else x0["gid_source"]]
        note = f"post-pass added: {x0['relation']} -> {other_leg}"
    elif n.get("file_type") in ("concept", "rationale"):
        cls = "correct_leaf"
        note = "concept/rationale leaf; no cross-file symbol to link"
    elif n.get("file_type") == "code" and e["relation"] == "contains" and (n.get("source_location") or "").startswith("L"):
        cls = "correct_leaf"
        note = "AST symbol under file node; no cross-file use detected"
    else:
        cls = "correct_leaf"
        note = "single edge; no detectable missing link (auto-pre-label)"
    lab.append({"gid": gid, "legacy_id": n["id"], "label": n.get("label"), "file": rel(n.get("source_file") or ""), "loc": n.get("source_location"),
                "only_edge": f"{e['relation']} <-> {other.get('label')}", "auto_class": cls, "note": note, "human": ""})
json.dump(lab, open(os.path.join(OUT, "label50.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
lm = ["# 50 random deg=1 nodes (seed 42) — auto-pre-label, human column empty\n",
      "| # | node | file | only edge | auto class | note |", "|---|------|------|-----------|------------|------|"]
for i, x in enumerate(lab, 1):
    lm.append(f"| {i} | {x['legacy_id']} | {x['file']}:{x['loc']} | {x['only_edge']} | {x['auto_class']} | {x['note'][:90]} |")
from collections import Counter as C
cnt = C(x["auto_class"] for x in lab)
lm.append(f"\nCounts: {dict(cnt)}. Precision/recall: after human fill of `human` column, run `python postpass.py score` (not implemented — counts above are the denominator).")
open(os.path.join(OUT, "label50.md"), "w", encoding="utf-8").write("\n".join(lm))

print(f"nodes: {len(nodes)} (created {len(created_nodes)})  edges: {len(edge_map)} (added imports={len(additions.get('imports',[]))} references={len(additions.get('references',[]))} validates={len(additions.get('validates',[]))} contains={len(additions.get('contains',[]))} mentions={len(additions.get('mentions',[]))} same_as={len(additions.get('same_as',[]))}) upsert_skips={upsert_skips}")
print("golden:", sum(1 for x in golden if x['ok']), "/", len(golden), "pass")
for x in golden:
    if not x['ok']:
        print("  FAIL:", x['name'], x['detail'])
print("label50:", dict(C(x['auto_class'] for x in lab)))
