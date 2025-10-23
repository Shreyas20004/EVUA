import os
import re
import ast
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from datetime import datetime

def create_session_folder(base_dir='sessions') -> str:
    os.makedirs(base_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join(base_dir, f'session_{timestamp}')
    os.makedirs(session_dir)
    return session_dir

@dataclass
class FileMetadata:
    """Metadata for each processed file."""
    filename: str
    original_filename: str
    rules_applied: List[str]
    lines_changed: List[int]
    stubbed_lines: List[int] = field(default_factory=list)
    marked_lines: List[Tuple[int, str]] = field(default_factory=list)  # (line_num, marker_type)
    parseable: bool = True
    errors: List[str] = field(default_factory=list)


class LongUnicodeReplacer(ast.NodeTransformer):
    """AST-based replacer for long() and unicode() calls."""
    
    def __init__(self):
        self.replacements = []  # Track (line, col_offset) for debugging
    
    def visit_Call(self, node: ast.Call) -> ast.expr:
        """Replace long() and unicode() function calls."""
        if isinstance(node.func, ast.Name):
            if node.func.id == 'long':
                self.replacements.append((node.lineno, node.col_offset, 'long', 'int'))
                node.func.id = 'int'
            elif node.func.id == 'unicode':
                self.replacements.append((node.lineno, node.col_offset, 'unicode', 'str'))
                node.func.id = 'str'
        
        return self.generic_visit(node)


class Python2ConstructDetector(ast.NodeVisitor):
    """Detect Python 2-only constructs that need Stage 1 attention."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.python2_constructs = defaultdict(list)  # {construct_type: [line_numbers]}
    
    def visit_Print(self, node):
        """Python 2 print statement (not print function)."""
        self.python2_constructs['print_statement'].append(node.lineno)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Detect Python 2-specific functions."""
        if isinstance(node.func, ast.Name):
            if node.func.id in ['xrange', 'raw_input', 'apply', 'coerce']:
                self.python2_constructs[node.func.id].append(node.lineno)
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        """Detect __metaclass__ in class definitions."""
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == '__metaclass__':
                        self.python2_constructs['metaclass_assignment'].append(item.lineno)
        self.generic_visit(node)


class Preprocessor:
    """Stage 0: Transform Python 2 code to be Python 3 parseable."""
    
    RULES = {
        'print_fix': r'print\s+(?![\(\[])',
        'comparison_fix': r'<>',
    }
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        """Initialize preprocessor.
        
        Args:
            dry_run: If True, show changes without writing files.
            verbose: If True, print detailed logs.
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.metadata: Dict[str, FileMetadata] = {}
        self.temp_dir = None
        self.stubbed_lines_log = defaultdict(list)  # Track all stubbed lines
        self.marked_lines_log = defaultdict(list)   # Track all marked lines
    
    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[PREPROCESSOR] {message}")
    
    def discover_python_files(self, project_path: str) -> List[str]:
        """Discover all .py files in project directory.
        
        Args:
            project_path: Root directory to search.
            
        Returns:
            List of absolute paths to .py files.
        """
        py_files = []
        for root, dirs, files in os.walk(project_path):
            # Skip common non-essential directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'venv', '.pytest_cache', 'node_modules'}]
            for file in files:
                if file.endswith('.py'):
                    py_files.append(os.path.join(root, file))
        
        self.log(f"Discovered {len(py_files)} Python files")
        return sorted(py_files)
    
    def _get_relative_temp_path(self, original_filepath: str, project_path: str) -> str:
        """Get the relative path to preserve folder structure in temp_dir.
        
        Args:
            original_filepath: Full path to original file.
            project_path: Root project path.
            
        Returns:
            Relative path to be used in temp_dir.
        """
        return os.path.relpath(original_filepath, project_path)
    
    def _has_print_function_import(self, content: str) -> bool:
        """Check if file has 'from __future__ import print_function'."""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module == '__future__':
                        for alias in node.names:
                            if alias.name == 'print_function':
                                return True
        except:
            pass
        return False
    
    def _remove_conflicting_future_imports(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Remove or stub problematic __future__ imports.
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        conflicting = {'division', 'absolute_import', 'generators'}
        changed = []
        
        for i, line in enumerate(lines):
            if 'from __future__ import' in line:
                # Check if line imports conflicting features
                if any(feat in line for feat in conflicting):
                    # Comment out the line instead of removing
                    lines[i] = '# ' + line.rstrip() + '  # (removed conflicting __future__ import)\n'
                    changed.append(i)
        
        return lines, changed
    
    def _apply_print_fix(self, lines: List[str]) -> List[int]:
        """Convert Python 2 print statements to Python 3 print() function safely."""
        changed = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()

            # Skip if already print function or not a print statement
            if not stripped.startswith('print') or re.match(r'print\s*\(', stripped):
                i += 1
                continue

            # Handle print >> redirection
            if stripped.startswith('print >>'):
                match = re.match(r'print\s*>>\s*(\S+)\s*,\s*(.*)', stripped)
                if match:
                    file_obj = match.group(1)
                    content = match.group(2)
                    indent = len(line) - len(stripped)
                    lines[i] = ' ' * indent + f'print({content}, file={file_obj})\n'
                    changed.append(i)
                i += 1
                continue

            # Standard print statements (single or multiple expressions)
            match = re.match(r'print\s+(.*)', stripped)
            if match:
                content = match.group(1).rstrip(';').rstrip()
                indent = len(line) - len(stripped)
                
                # Handle multiple arguments with commas
                if ',' in content and '<<' not in content:  # Avoid bit shift operators
                    # Convert comma-separated to multiple arguments
                    parts = [part.strip() for part in content.split(',')]
                    new_content = ', '.join(parts)
                    lines[i] = ' ' * indent + f'print({new_content})\n'
                else:
                    lines[i] = ' ' * indent + f'print({content})\n'
                    
                changed.append(i)

            i += 1

        return changed

    def _mark_python2_constructs(self, content: str, lines: List[str]) -> List[Tuple[int, str]]:
        """Mark Python 2-only constructs with comments for Stage 1 review."""
        marked = []
        
        try:
            tree = ast.parse(content)
            detector = Python2ConstructDetector(lines)
            detector.visit(tree)
            
            # Add markers for detected constructs
            for construct_type, line_numbers in detector.python2_constructs.items():
                for line_no in line_numbers:
                    idx = line_no - 1
                    if idx < len(lines):
                        original_line = lines[idx].rstrip()
                        if not original_line.endswith('# PY2_MARKER'):
                            lines[idx] = original_line + f'  # PY2_MARKER: {construct_type}\n'
                            marked.append((idx, construct_type))
                            self.log(f"    Marked {construct_type} at line {line_no}")
        
        except Exception as e:
            self.log(f"    AST analysis failed for marking: {e}")
            # Fallback: simple regex marking for common patterns
            for i, line in enumerate(lines):
                if re.search(r'\b(xrange|raw_input|apply|coerce)\s*\(', line):
                    if not line.rstrip().endswith('# PY2_MARKER'):
                        lines[i] = line.rstrip() + '  # PY2_MARKER: python2_function\n'
                        marked.append((i, 'python2_function'))
        
        return marked

    def _apply_long_unicode_fix_ast(self, content: str, lines: List[str]) -> Tuple[List[str], List[int], List[int]]:
        """Use AST to safely replace long() and unicode() calls with int() and str()."""
        long_changes, unicode_changes = [], []

        try:
            tree = ast.parse(content)
            replacer = LongUnicodeReplacer()
            replacer.visit(tree)

            # Apply replacements grouped by line
            by_line = defaultdict(list)
            for line_no, col, old, new in replacer.replacements:
                by_line[line_no].append((col, old, new))

            for line_no in sorted(by_line.keys(), reverse=True):
                idx = line_no - 1
                if idx < len(lines):
                    line = lines[idx]
                    for col, old, new in sorted(by_line[line_no], reverse=True):
                        line = line[:col] + new + line[col + len(old):]
                        if old == 'long': long_changes.append(idx)
                        if old == 'unicode': unicode_changes.append(idx)
                    lines[idx] = line

        except Exception:
            # Fallback: regex only outside strings
            for i, line in enumerate(lines):
                if re.search(r'\blong\(', line):
                    lines[i] = re.sub(r'\blong\(', 'int(', line)
                    long_changes.append(i)
                if re.search(r'\bunicode\(', line):
                    lines[i] = re.sub(r'\bunicode\(', 'str(', line)
                    unicode_changes.append(i)

        return lines, long_changes, unicode_changes

    def _apply_comparison_fix(self, lines: List[str]) -> List[int]:
        """Replace <> with !=, ignoring strings and comments."""
        changed = []

        for i, line in enumerate(lines):
            if '<>' not in line:
                continue

            # Heuristic: only replace outside strings
            parts = re.split(r'([\'"].*?[\'"])', line)  # Split by quoted strings
            for j, part in enumerate(parts):
                if '<>' in part and not (part.startswith('"') or part.startswith("'")):
                    parts[j] = part.replace('<>', '!=')

            new_line = ''.join(parts)
            if new_line != line:
                lines[i] = new_line
                changed.append(i)

        return changed
    
    def _validate_parseable(self, content: str, filename: str) -> Tuple[bool, List[str]]:
        """Try to parse content with AST. Return (success, errors)."""
        try:
            ast.parse(content)
            return True, []
        except SyntaxError as e:
            return False, [f"Syntax error at line {e.lineno}: {e.msg}"]
        except Exception as e:
            return False, [f"Parse error: {str(e)}"]
    
    def _stub_only_broken_syntax(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Stub only truly broken syntax that prevents parsing."""
        stubbed = []
        max_attempts = min(len(lines), 20)  # Reduced from 50
        attempt = 0

        while attempt < max_attempts:
            try:
                ast.parse(''.join(lines))
                break
            except SyntaxError as e:
                if e.lineno and e.lineno <= len(lines):
                    idx = e.lineno - 1
                    original_line = lines[idx].rstrip()
                    
                    # Only stub if it's clearly malformed syntax
                    if self._is_truly_broken_syntax(original_line):
                        lines[idx] = f'# STUBBED: {original_line}\n'
                        stubbed.append(idx)
                        self.log(f"    Line {idx+1}: Stubbed broken syntax -> {original_line}")
                    else:
                        # Try to fix common issues instead of stubbing
                        fixed = self._try_fix_syntax(lines[idx])
                        if fixed:
                            lines[idx] = fixed
                            self.log(f"    Line {idx+1}: Fixed syntax instead of stubbing")
                        else:
                            # Last resort: minimal stub with single comment
                            lines[idx] = f'# FIXME: Syntax needs review: {original_line}\n'
                            stubbed.append(idx)
                            self.log(f"    Line {idx+1}: Marked for review -> {original_line}")
                    
                    attempt += 1
                else:
                    break
            except Exception as e:
                self.log(f"    Stubbing failed: {e}")
                break

        return lines, stubbed

    def _is_truly_broken_syntax(self, line: str) -> bool:
        """Check if line has truly broken syntax that can't be easily fixed."""
        stripped = line.strip()
        
        # Definitely broken patterns
        broken_patterns = [
            r'^\s*<<<\s*',  # Here document syntax
            r'^\s*`.*`\s*$',  # Backticks (deprecated)
            r'^\s*exec\s+[^\s]+\s*$',  # exec without parentheses but with spaces
        ]
        
        for pattern in broken_patterns:
            if re.search(pattern, stripped):
                return True
        
        # Incomplete structures
        if stripped.count('(') != stripped.count(')') and not any(keyword in stripped for keyword in ['def', 'class', 'if', 'for', 'while']):
            return True
            
        return False

    def _try_fix_syntax(self, line: str) -> Optional[str]:
        """Try to fix common syntax issues without stubbing."""
        original = line.rstrip()
        
        # Fix exec statements
        if original.startswith('exec '):
            match = re.match(r'exec\s+(.+?)(\s+in\s+.+)?$', original)
            if match:
                expr = match.group(1)
                globals_part = match.group(2) or ''
                return f'exec({expr}{globals_part})\n'
        
        # Fix backticks (repr)
        if '`' in original:
            line = re.sub(r'`([^`]+)`', r'repr(\1)', original)
            return line + '\n'
        
        return None
    
    def _create_temp_file(self, original_filepath: str, project_path: str, content: str) -> str:
        """Create temp file preserving folder structure.
        
        Returns:
            Path to the temp file created.
        """
        rel_path = self._get_relative_temp_path(original_filepath, project_path)
        temp_filepath = os.path.join(self.temp_dir, rel_path)
        
        # Create parent directories
        temp_file_dir = os.path.dirname(temp_filepath)
        os.makedirs(temp_file_dir, exist_ok=True)
        
        # Write file
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return temp_filepath
    
    def process_file(self, filepath: str, project_path: str) -> FileMetadata:
        """Process a single Python file.
        
        Args:
            filepath: Path to the .py file.
            project_path: Root project path (for relative paths).
            
        Returns:
            FileMetadata object with processing results.
        """
        self.log(f"Processing: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
            
            lines = original_content.splitlines(keepends=True)
            if not lines:
                return FileMetadata(filepath, filepath, [], [], [], [], True, [])
            
            all_changes = set()
            all_stubbed = set()
            all_marked = []
            rules_applied = []
            
            # Rule 1: Print fix (only if no print_function import)
            if not self._has_print_function_import(original_content):
                changed = self._apply_print_fix(lines)
                if changed:
                    rules_applied.append('print_fix')
                    all_changes.update(changed)
                    self.log(f"    Applied print_fix to {len(changed)} line(s)")
            
            # Rule 2: long() and unicode() fixes via AST
            modified_content = ''.join(lines)
            lines, long_changes, unicode_changes = self._apply_long_unicode_fix_ast(modified_content, lines)
            
            if long_changes:
                rules_applied.append('long_fix')
                all_changes.update(long_changes)
                self.log(f"    Applied long_fix to {len(long_changes)} line(s)")
            
            if unicode_changes:
                rules_applied.append('unicode_fix')
                all_changes.update(unicode_changes)
                self.log(f"    Applied unicode_fix to {len(unicode_changes)} line(s)")
            
            # Rule 3: Comparison operator fix
            changed = self._apply_comparison_fix(lines)
            if changed:
                rules_applied.append('comparison_fix')
                all_changes.update(changed)
                self.log(f"    Applied comparison_fix to {len(changed)} line(s)")
            
            # Rule 4: Remove conflicting future imports
            changed, stubbed_future = self._remove_conflicting_future_imports(lines)
            if stubbed_future:
                rules_applied.append('future_imports')
                all_changes.update(stubbed_future)
                self.log(f"    Applied future_imports to {len(stubbed_future)} line(s)")
            
            # Rule 5: Mark Python 2 constructs for Stage 1
            modified_content = ''.join(lines)
            marked = self._mark_python2_constructs(modified_content, lines)
            if marked:
                rules_applied.append('python2_markers')
                all_marked.extend(marked)
                self.log(f"    Marked {len(marked)} Python 2 construct(s)")
            
            modified_content = ''.join(lines)
            
            # Validation: Check if parseable
            parseable, errors = self._validate_parseable(modified_content, filepath)
            
            # If not parseable, try minimal stubbing
            if not parseable:
                self.log(f"  Initial parse failed: {errors[0]}")
                lines, stubbed = self._stub_only_broken_syntax(lines)
                all_stubbed.update(stubbed)
                modified_content = ''.join(lines)
                
                if stubbed:
                    rules_applied.append('minimal_stubbing')
                    self.log(f"  Stubbed {len(stubbed)} truly broken line(s)")
                    for line_idx in sorted(stubbed):
                        self.log(f"    Stubbed line {line_idx + 1}")
                        self.stubbed_lines_log[filepath].append(line_idx + 1)
                
                # Revalidate
                parseable, errors = self._validate_parseable(modified_content, filepath)
            
            # Create metadata
            metadata = FileMetadata(
                filename=filepath if self.dry_run else self._create_temp_file(filepath, project_path, modified_content),
                original_filename=filepath,
                rules_applied=list(set(rules_applied)),
                lines_changed=sorted(list(all_changes)),
                stubbed_lines=sorted(list(all_stubbed)),
                marked_lines=all_marked,
                parseable=parseable,
                errors=errors
            )
            
            self.metadata[filepath] = metadata
            status = "✓" if parseable else "⚠"
            self.log(f"  {status} Rules: {', '.join(metadata.rules_applied) or 'none'} | Stubbed: {len(metadata.stubbed_lines)} | Marked: {len(metadata.marked_lines)}")
            
            return metadata
        
        except Exception as e:
            self.log(f"  ✗ Error processing file: {str(e)}")
            metadata = FileMetadata(
                filename=filepath,
                original_filename=filepath,
                rules_applied=[],
                lines_changed=[],
                stubbed_lines=[],
                marked_lines=[],
                parseable=False,
                errors=[str(e)]
            )
            self.metadata[filepath] = metadata
            return metadata
    
    def process_project(self, project_path: str) -> Tuple[str, Dict]:
        """Process all Python files in a project.
        
        Args:
            project_path: Root directory of the project.
            
        Returns:
            Tuple of (temp_dir_path, summary_dict)
        """
        self.log(f"Starting Stage 0 preprocessor on: {project_path}")
        
        py_files = self.discover_python_files(project_path)
        
        # Create temp directory if not dry run
        if not self.dry_run:
            self.temp_dir = create_session_folder('sessions')
            self.log(f"Using session folder for processed files: {self.temp_dir}")

                
        for filepath in py_files:
            self.process_file(filepath, project_path)
        
        # Generate summary
        summary = self._generate_summary()
        
        return self.temp_dir or '', summary
    
    def _generate_summary(self) -> Dict:
        """Generate a summary report of processing."""
        total_files = len(self.metadata)
        parseable_files = sum(1 for m in self.metadata.values() if m.parseable)
        rules_count = defaultdict(int)
        total_changes = 0
        total_stubbed = 0
        total_marked = 0
        
        for metadata in self.metadata.values():
            total_changes += len(metadata.lines_changed)
            total_stubbed += len(metadata.stubbed_lines)
            total_marked += len(metadata.marked_lines)
            for rule in metadata.rules_applied:
                rules_count[rule] += 1
        
        summary = {
            'total_files': total_files,
            'parseable_files': parseable_files,
            'unparseable_files': total_files - parseable_files,
            'total_lines_changed': total_changes,
            'total_lines_stubbed': total_stubbed,
            'total_lines_marked': total_marked,
            'rules_applied': dict(rules_count),
            'temp_directory': self.temp_dir,
            'metadata': {k: asdict(v) for k, v in self.metadata.items()},
            'stubbed_lines_detail': dict(self.stubbed_lines_log)
        }
        
        return summary
    
    def save_metadata(self, output_path: str):
        """Save metadata to JSON file."""
        summary = self._generate_summary()
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        self.log(f"Metadata saved to: {output_path}")
    
    def print_summary(self):
        """Print a formatted summary."""
        summary = self._generate_summary()
        
        print("\n" + "="*70)
        print("STAGE 0 PREPROCESSOR SUMMARY")
        print("="*70)
        print(f"Total files processed:     {summary['total_files']}")
        print(f"Parseable files:           {summary['parseable_files']}")
        print(f"Unparseable files:         {summary['unparseable_files']}")
        print(f"Total lines changed:       {summary['total_lines_changes']}")
        print(f"Total lines stubbed:       {summary['total_lines_stubbed']}")
        print(f"Total lines marked:        {summary['total_lines_marked']}")
        print(f"Temp directory:            {summary['temp_directory']}")
        print("\nRules Applied (frequency):")
        for rule, count in sorted(summary['rules_applied'].items(), key=lambda x: -x[1]):
            print(f"  {rule:.<35} {count:>4} files")
        
        if self.stubbed_lines_log:
            print("\nStubbed Lines (by file):")
            for filepath, lines in sorted(self.stubbed_lines_log.items()):
                rel_path = os.path.relpath(filepath)
                print(f"  {rel_path}")
                for line_no in lines:
                    print(f"    Line {line_no}")
        
        print("="*70 + "\n")


def main():
    """Example usage of the preprocessor."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python stage0_preprocessor.py <project_path> [--dry-run] [--verbose]")
        print("Example: python stage0_preprocessor.py ./my_project --verbose")
        sys.exit(1)
    
    project_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    verbose = '--verbose' in sys.argv
    
    if not os.path.isdir(project_path):
        print(f"Error: {project_path} is not a valid directory")
        sys.exit(1)
    
    # Run preprocessor
    preprocessor = Preprocessor(dry_run=dry_run, verbose=verbose)
    temp_dir, summary = preprocessor.process_project(project_path)
    
    # Print summary
    preprocessor.print_summary()
    
    # Save metadata
    if not dry_run and temp_dir:
        metadata_file = os.path.join(temp_dir, 'metadata.json')
        preprocessor.save_metadata(metadata_file)
        print(f"✓ Processed files available in: {temp_dir}")
        print(f"✓ Metadata saved to: {metadata_file}")


if __name__ == '__main__':
    main()