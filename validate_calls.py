"""
validate_calls.py  —  non-interactive call-resolution report.

Runs the full Stage 1–4 pipeline on a target project and prints the
resolution breakdown (LOCAL / IMPORTED / EXTERNAL / UNRESOLVED), plus
optionally dumps every unresolved call site to a file for before/after
diffing. Used to validate call-resolver changes without touching L1.

Usage:
    python validate_calls.py [project_path] [--dump out.txt]
"""
import sys
from collections import Counter

from file_Walker import file_walker
from core_extractor_02 import ObjectASTExtractor
from symbol_Resolver import SymbolResolver
from call_Resolver import CallResolver

DEFAULT_PROJECT = r"C:\Users\lenov\projects\Tcheck-Games"


def build(project_path):
    results = file_walker(project_path)
    files = results["files"]
    for file in files:
        if file.is_empty or file.has_syntax_errors:
            continue
        file.nodes = ObjectASTExtractor(file.path, file.relative_path).run()

    symbol_map = SymbolResolver(files, project_root=project_path).produce_symbol_map()
    resolver = CallResolver(files, symbol_map)
    graph = resolver.produce_call_graph()
    return files, resolver, graph


def report(project_path, dump_path=None):
    files, resolver, graph = build(project_path)

    counts = Counter()
    unresolved = []
    for caller_id, edges in graph._by_caller.items():
        for edge in edges:
            counts[edge.resolution] += 1
            if edge.resolution == "UNRESOLVED":
                caller = resolver._node_index.get(caller_id)
                site = resolver._node_index.get(edge.call_site_node_id)
                unresolved.append((
                    caller.file_rel_path if caller else "?",
                    (caller.qualified_name or caller.name) if caller else "?",
                    (site.text.replace("\n", " ") if site else "?"),
                    site.start_line if site else 0,
                ))

    total = sum(counts.values())
    print(f"PROJECT: {project_path}")
    print(f"  TOTAL      : {total}")
    print(f"  LOCAL      : {counts['LOCAL']}")
    print(f"  IMPORTED   : {counts['IMPORTED']}")
    print(f"  EXTERNAL   : {counts['EXTERNAL']}")
    print(f"  UNRESOLVED : {counts['UNRESOLVED']}")
    resolved = counts['LOCAL'] + counts['IMPORTED'] + counts['EXTERNAL']
    if total:
        print(f"  resolved+external rate : {resolved / total * 100:.1f}%")

    if dump_path:
        unresolved.sort()
        with open(dump_path, "w", encoding="utf-8") as fh:
            for rel, caller, text, line in unresolved:
                fh.write(f"{rel}\t{caller}\t{text}\t{line}\n")
        print(f"  dumped {len(unresolved)} unresolved -> {dump_path}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    dump = None
    if "--dump" in args:
        i = args.index("--dump")
        dump = args[i + 1]
        del args[i:i + 2]
    project = args[0] if args else DEFAULT_PROJECT
    report(project, dump)
