from tree_sitter import Language
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript

file_extensions = [
    '.py',
    '.js',
    '.ts',
    '.tsx',
    '.jsx'
]

file_ignorables = [
    'node_modules',
    '__pycache__',
    '.git',
    'dist',
    '.venv',
    '.env',
    '.env.local',
    'venv',
    'virtualenv',
    '.pytest_cache',
    '.ruff_cache',
    '.vscode',
    '.idea',
    '.DS_Store',
    '.gitignore'
]

language_map = {
    '.py': Language(tree_sitter_python.language()),
    '.js': Language(tree_sitter_javascript.language()),
    '.jsx': Language(tree_sitter_javascript.language()),
    '.ts': Language(tree_sitter_typescript.language_typescript()),
    '.tsx': Language(tree_sitter_typescript.language_tsx())
}