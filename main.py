from file_Walker import file_walker
from core_extractor_02 import ObjectASTExtractor
from symbol_Resolver import SymbolResolver
from call_Resolver import CallResolver
from sql_Bd import DatabaseManager

def strip_quotes(input_string):
    return input_string.strip('"')

def main():
    directory_path = strip_quotes(input("Enter the directory path: "))

    # Stage 1 — discover every source file in the project
    results      = file_walker(directory_path)
    files        = results['files']
    directories  = results['directories']

    #print(f"FILES: {files}")

    for warning in results['warnings']:
        print(f"WARNING: {warning}")

    # Stage 2 — extract nodes from each file and populate file.nodes
    for file in files:
        if file.is_empty or file.has_syntax_errors:
            continue
        extractor  = ObjectASTExtractor(file.path, file.relative_path)
        file.nodes = extractor.run()

    # Stage 3 — resolve all imports across the full project
    resolver   = SymbolResolver(files, project_root=directory_path)
    symbol_map = resolver.produce_symbol_map()
    
    # Print every import with its resolution status
    print("IMPORT NODES:")
    count = total_internal = total_external = total_unresolved = 0

    for file in files:
        for node in file.nodes:
            if node.category != "imports":
                continue
            count += 1
            status = node.metadata.get("resolution", "UNRESOLVED")

            if status == "INTERNAL":
                total_internal += 1
                target   = node.metadata.get("target_file_path", "?")
                resolved = symbol_map.get_symbols(node.id)
                symbols  = ", ".join(resolved.keys()) if resolved else "—"
                # print(f"  [{status}]    IMPORT {count}: {node.text}")
                # print(f"               -> {target}  [{symbols}]")

            elif status == "EXTERNAL":
                total_external += 1
                # print(f"  [{status}]    IMPORT {count}: {node.text}")

            else:
                total_unresolved += 1
                # print(f"  [UNRESOLVED]  IMPORT {count}: {node.text}")

    print(f"\n  TOTAL : {count}  |  INTERNAL : {total_internal}  |  EXTERNAL : {total_external}  |  UNRESOLVED : {total_unresolved}")
    print(f"\nSYMBOL MAP: {len(symbol_map)} entries")

    # Stage 4 — build function-level call graph
    call_resolver = CallResolver(files, symbol_map)
    call_graph    = call_resolver.produce_call_graph()

    print("\nCALL GRAPH:")
    #call_resolver.print_call_graph(call_graph)
    # call_resolver.print_sorted_graph(call_graph)
    print(f"\nCALL GRAPH: {len(call_graph)} edges")

    # Stage 5 — persist everything to SQLite
    db = DatabaseManager("v3rtex.db")
    db.populate(files, symbol_map, call_graph, directories=directories)

    stats = db.stats()
    print(f"\nDATABASE: {stats}")


def clear_database():
    db = DatabaseManager("v3rtex.db")
    db.clear_database()
    print("Database cleared")

def launch():

    print("Welcome to the V3RTEX code analysis tool \nThis tool will analyze your PY or Js/Ts project")

    loop = True
    while loop:
        print("Chose between the options below: \n 1. Analyze a Python project \n 2. Clear the database")
        choice = input("Enter your choice (1 or 2): ")
        if choice == "1":
            main()
        elif choice == "2":
            clear_database()
        else:
            print("Invalid choice")
            break
    

if __name__ == "__main__":
    launch()
