"""
This script is use dto create every component in the project
This script contains the class definitions and building blocs which will be used all through 
Following OOP principles.

Objects : Directory, File, Node
"""

class Directory:
    def __init__(
        self, 
        path: str, 
        name: str, 
        relative_path: str, 
        files: list = []
    ):
        self.path = path
        self.name = name
        self.relative_path = relative_path
        self.files = files
        self.id = self.create_directory_id()

    def create_directory_id(self):
        return f"{self.path}.{self.relative_path}.{self.name}"

    def __str__(self):
        return f"{self.path} - {self.name} - {self.relative_path}"

    def __repr__(self):
        rel_path = self.relative_path.replace("\\", ".").replace("//", ".")
        path = self.path.replace("\\", ".").replace("//", ".")
        return f"Directory(path={path!r}, name={self.name!r}, relative_path={rel_path!r})"


class File:
    def __init__(
        self,
        path: str,
        name: str,
        relative_path: str,
        language: str,
        size: int,
        last_modified: float,
        hash: str,
        line_count: int = 0,
        encoding: str = "utf-8",
        is_empty: bool = False,
        is_large: bool = False,
        has_syntax_errors: bool = False,
        warnings: list = None,
        nodes: list = None,
    ):
        self.path = path
        self.relative_path = relative_path
        self.language = language
        self.name = name
        self.size = size
        self.last_modified = last_modified
        self.hash = hash
        self.line_count = line_count
        self.encoding = encoding
        self.is_empty = True if size == 0 else False
        self.is_large = True if size > 1_000_000 else False
        self.has_syntax_errors = has_syntax_errors
        self.warnings = warnings or []
        self.nodes = nodes or []
        self.id = self.create_file_id()

    def create_file_id(self):
        rel_path = self.relative_path.replace("\\", ".").replace("//", ".")
        path = self.path.replace("\\", ".").replace("//", ".")
        return f"{path}.{rel_path}.{self.name}.{self.language}.{self.size}.{self.line_count}"

    def __repr__(self):
        return (
            f"File(id={self.id!r}, name={self.name!r}, "
            f"language={self.language!r}, path={self.relative_path!r}, "
            f"lines={self.line_count}, empty={self.is_empty}, "
            f"large={self.is_large}, errors={self.has_syntax_errors})"
        )

    def __str__(self):
        return f"File({self.relative_path})"


class Node:
    def __init__(
        self,
        file_rel_path: str,
        category: str,
        node_type: str,
        start_line: int,
        end_line: int,
        start_column: int,
        end_column: int,
        text: str,
        name: str = None,
        qualified_name: str = None,
        parent: 'Node' = None,
        metadata: dict = None,
    ):
        self.file_rel_path = file_rel_path
        self.category = category
        self.node_type = node_type
        self.start_line = start_line
        self.end_line = end_line
        self.start_column = start_column
        self.end_column = end_column
        self.text = text
        self.name = name
        self.qualified_name = qualified_name
        self.parent = parent
        self.children = []
        self.metadata = metadata or {}
        self.id = self.create_node_id()

    def create_node_id(self):
        #1 sanitize the file_rel_path
        file_rel_path = self.file_rel_path.replace("\\", ".").replace("//", ".")
        
        #2 sort node_type
        node_type = self.node_type.lower()

        return f"{file_rel_path}.{node_type}.{self.name}.{self.parent.name if self.parent else None}.{self.start_line}"

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "node_type": self.node_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_column": self.start_column,
            "end_column": self.end_column,
            "text": self.text,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "parent_id": self.parent.id if self.parent else None,
            "children_ids": [child.id for child in self.children],
            "metadata": self.metadata,
        }

    def __repr__(self):
        return f"Node(category={self.category}, node_type={self.node_type}, name={self.name}, start_line={self.start_line}, end_line={self.end_line})"


#class symbol: