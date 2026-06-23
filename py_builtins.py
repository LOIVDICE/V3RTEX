"""
py_builtins.py

Python language / stdlib names that can appear at a call site but never
resolve to a project definition. Kept separate from the resolver so the
lists can grow without touching resolution logic.

Category A (built-in exceptions): names like ValueError / Exception are
called exactly like functions (``raise ValueError(...)``) but belong to
the language, so they should be classified EXTERNAL, not UNRESOLVED.
"""

# Built-in exception classes (callable: raise ValueError("..."))
EXCEPTIONS = {
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError",
    "IndexError", "AttributeError", "RuntimeError", "StopIteration",
    "StopAsyncIteration", "NotImplementedError", "FileNotFoundError",
    "FileExistsError", "IOError", "OSError", "ImportError",
    "ModuleNotFoundError", "NameError", "UnboundLocalError",
    "ZeroDivisionError", "ArithmeticError", "OverflowError",
    "FloatingPointError", "AssertionError", "LookupError", "MemoryError",
    "RecursionError", "ReferenceError", "SystemError", "PermissionError",
    "TimeoutError", "ConnectionError", "BrokenPipeError",
    "ConnectionResetError", "ConnectionAbortedError",
    "ConnectionRefusedError", "InterruptedError", "ProcessLookupError",
    "ChildProcessError", "BlockingIOError", "IsADirectoryError",
    "NotADirectoryError", "UnicodeError", "UnicodeDecodeError",
    "UnicodeEncodeError", "UnicodeTranslateError", "EOFError",
    "GeneratorExit", "KeyboardInterrupt", "SystemExit", "Warning",
    "DeprecationWarning", "PendingDeprecationWarning", "UserWarning",
    "FutureWarning", "RuntimeWarning", "SyntaxWarning", "ResourceWarning",
}
