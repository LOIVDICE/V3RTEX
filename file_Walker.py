"""
File Walker
This script will walk through a directory and return a list of files and directories in the directory.

Input: A directory path
Output: A list of files and directories in the directory (the size, when it was last modified, hash of the file, and the file name)

Imported by: ast_Parser.py
"""

import os
import hashlib

from compBlocs12 import File, Directory
from lang_config import file_ignorables, file_extensions

LARGE_FILE_SIZE_BYTES = 1_000_000

def directory_input_regulator(directory):
    if not os.path.isdir(directory):
        raise ValueError(f"Directory {directory} is not a valid directory")
    if directory in file_ignorables:
        raise ValueError(f"Directory {directory} is in the ignore list")
    return directory


def file_walker(directory):
    directories = []
    matching_files = []
    warnings = []

    try:
        for root, dirs, files in os.walk(directory):

            #1 ignore directories and files that are in the ignore list
            dirs[:] = [d for d in dirs if d not in file_ignorables]
            files[:] = [f for f in files if f not in file_ignorables and f.endswith(tuple(file_extensions))]
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                directory_obj = Directory(
                    path=dir_path,
                    name=dir_name,
                    relative_path=os.path.relpath(dir_path, os.getcwd())
                )
                directories.append(directory_obj)

            for file_name in files:
                file_path = os.path.join(root, file_name)
                with open(file_path, 'rb') as file:
                    file_bytes = file.read()

                if b'\0' in file_bytes:
                    warnings.append(f"Skipped binary file with source extension: {file_path}")
                    continue

                file_size = os.path.getsize(file_path)
                file_warnings = []
                is_empty = file_size == 0
                is_large = file_size > LARGE_FILE_SIZE_BYTES

                if is_empty:
                    file_warnings.append("EMPTY")

                if is_large:
                    file_warnings.append("LARGE")

                file_hash = hashlib.sha256(file_bytes).hexdigest()
                line_count = len(file_bytes.splitlines()) if file_bytes else 0

                file_obj = File(
                    path=file_path,
                    name=file_name,
                    relative_path=os.path.relpath(file_path, directory),
                    language=os.path.splitext(file_name)[1].lower(),
                    size=file_size,
                    last_modified=os.path.getmtime(file_path),
                    hash=file_hash,
                    line_count=line_count,
                    is_empty=is_empty,
                    is_large=is_large,
                    warnings=file_warnings,
                )

                matching_files.append(file_obj)
    except Exception as e:
        print(f"Error: {e}")

    return {
        "directories": directories,
        "files": matching_files,
        "warnings": warnings,
    }

# def file_walker(directory):
#     for root, dirs, files in os.walk(directory):
#         dirs[:] = [d for d in dirs if d not in ignorables]
#         for dir in dirs:
#             dir_path = os.path.join(root, dir)
#             dir = Directory(dir_path, dir)
#             print(f"Directory: {dir.__str__()}")

#             files[:] = [f for f in files if f not in ignorables and f.endswith(tuple(needed_file_extensions))]
#             for file in files:
#                 file_path = os.path.join(root, file)
#                 file = File(file_path, file, os.path.getsize(file_path), os.path.getmtime(file_path), hashlib.sha256(open(file_path, 'rb').read()).hexdigest())
#                 print(f"File: {file.__str__()}")


if __name__ == "__main__":
    directory = directory_input_regulator(input("Enter a directory path: "))
    results = file_walker(directory)
    print(f"DIRECTORY : {directory}")
    print(f"DIRECTORIES : {results['directories']}")
    print(f"FILES : {results['files']}")
    print(f"WARNINGS : {results['warnings']}")