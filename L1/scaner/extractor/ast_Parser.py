"""
AST Parser
This script will parse the AST of a file and return a list of nodes.

Input: A file object
Output: A list of nodes

Imported by: ast_Extractor.py
"""
from pathlib import Path
from tree_sitter import Parser
import os

from scaner.config.lang_config import language_map

class ASTParser:
    """
    A service class to handle AST parsing for multiple programming languages.
    It produces the AST of a given file
    """
    def __init__(self):
        # Encapsulate the parser mapping within the class instance
        self._parsers = {
            ext: Parser(language)
            for ext, language in language_map.items()
        }

    def parse_file(self, file_path):
        """Parses a file and returns the tree-sitter Tree object."""
        file_extension = os.path.splitext(file_path)[1]
        
        if file_extension not in self._parsers:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        parser = self._parsers[file_extension]
        source_code = Path(file_path).read_bytes()
        return parser.parse(source_code)

    @staticmethod
    def format_tree(node, indent=0):
        """Recursively prints the structure of the AST."""
        print("  " * indent + node.type)
        for child in node.children:
            ASTParser.format_tree(child, indent + 1)

if __name__ == "__main__":
    file_path = input("Enter a file path: ").strip().strip('"')
    
    ast_manager = ASTParser()
    tree = ast_manager.parse_file(file_path)
    ast_manager.format_tree(tree.root_node)