import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from datetime import datetime


def create_session_folder(base_dir='sessions') -> str:
    """Create a timestamped session folder for storing processed files."""
    os.makedirs(base_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join(base_dir, f'session_{timestamp}')
    os.makedirs(session_dir)
    return session_dir


@dataclass
class SemanticMetadata:
    """Metadata for semantic fixes per file."""
    filename: str
    original_filename: str
    semantic_fixes: List[str]
    lines_modified: List[int]
    division_fixes: int = 0
    iterator_wraps: int = 0
    encoding_fixes: int = 0
    import_cleanups: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    parse_success: bool = True


class DivisionAnalyzer(ast.NodeVisitor):
    """Analyze division operations to detect integer division."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.integer_divisions = []  # List of (lineno, col_offset, left_type, right_type)
        self.has_future_division = False
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check for __future__ division import."""
        if node.module == '__future__':
            for alias in node.names:
                if alias.name == 'division':
                    self.has_future_division = True
        self.generic_visit(node)
    
    def visit_BinOp(self, node: ast.BinOp):
        """Detect division operations between integers."""
        if isinstance(node.op, ast.Div):
            # Try to infer if operands are integers
            left_is_int = self._is_likely_integer(node.left)
            right_is_int = self._is_likely_integer(node.right)
            
            if left_is_int and right_is_int:
                self.integer_divisions.append((
                    node.lineno,
                    node.col_offset,
                    'int',
                    'int'
                ))
        
        self.generic_visit(node)
    
    def _is_likely_integer(self, node: ast.expr) -> bool:
        """Heuristic to determine if a node likely represents an integer."""
        if isinstance(node, ast.Constant):
            return isinstance(node.value, int)
        elif isinstance(node, ast.Num):  # Python 3.7 compatibility
            return isinstance(node.n, int)
        elif isinstance(node, ast.Name):
            # Check if variable name suggests integer (heuristic)
            name = node.id
            if re.match(r'^(i|j|k|n|m|count|idx|index|num|size|len|length)$', name):
                return True
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                # len(), int(), range() return integers
                if node.func.id in ('len', 'int', 'range'):
                    return True
        
        return False


class IteratorWrapper(ast.NodeTransformer):
    """Wrap iterators that need to be lists."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.wrapped_calls = []  # List of (lineno, col_offset, function_name)
    
    def visit_Subscript(self, node: ast.Subscript):
        """Detect indexing on map/filter/zip results."""
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                func_name = node.value.func.id
                if func_name in ('map', 'filter', 'zip'):
                    self.wrapped_calls.append((
                        node.lineno,
                        node.col_offset,
                        func_name
                    ))
        
        self.generic_visit(node)
        return node
    
    def visit_Call(self, node: ast.Call):
        """Detect len() on map/filter/zip results."""
        if isinstance(node.func, ast.Name) and node.func.id == 'len':
            if node.args and isinstance(node.args[0], ast.Call):
                inner_call = node.args[0]
                if isinstance(inner_call.func, ast.Name):
                    func_name = inner_call.func.id
                    if func_name in ('map', 'filter', 'zip'):
                        self.wrapped_calls.append((
                            inner_call.lineno,
                            inner_call.col_offset,
                            func_name
                        ))
        
        self.generic_visit(node)
        return node


class EncodingAnalyzer(ast.NodeVisitor):
    """Analyze string/bytes operations that may need encoding fixes."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.encoding_issues = []  # List of (lineno, issue_type, description)
    
    def visit_Call(self, node: ast.Call):
        """Detect file opens without explicit encoding."""
        if isinstance(node.func, ast.Name) and node.func.id == 'open':
            # Check if 'encoding' keyword is present
            has_encoding = any(kw.arg == 'encoding' for kw in node.keywords)
            has_binary_mode = False
            
            # Check if mode contains 'b'
            if len(node.args) >= 2:
                mode_arg = node.args[1]
                if isinstance(mode_arg, (ast.Constant, ast.Str)):
                    mode = mode_arg.value if isinstance(mode_arg, ast.Constant) else mode_arg.s
                    if 'b' in mode:
                        has_binary_mode = True
            
            if not has_encoding and not has_binary_mode:
                self.encoding_issues.append((
                    node.lineno,
                    'missing_encoding',
                    'open() without explicit encoding'
                ))
        
        self.generic_visit(node)


class SemanticAnalyzer:
    """Stage 2: Fix semantic differences between Python 2 and Python 3."""
    
    # Python 2 compatibility patterns to remove
    PY2_COMPAT_PATTERNS = [
        r'try:\s*import cPickle as pickle\s*except ImportError:\s*import pickle',
        r'try:\s*from StringIO import StringIO\s*except ImportError:\s*from io import StringIO',
        r'try:\s*import ConfigParser\s*except ImportError:\s*import configparser',
        r'try:\s*import Queue\s*except ImportError:\s*import queue',
    ]
    
    def __init__(self, stage1_metadata: Dict = None, dry_run: bool = False, verbose: bool = False):
        """Initialize semantic analyzer.
        
        Args:
            stage1_metadata: Metadata from Stage 1 (optional).
            dry_run: If True, show changes without writing files.
            verbose: If True, print detailed logs.
        """
        self.stage1_metadata = stage1_metadata or {}
        self.dry_run = dry_run
        self.verbose = verbose
        self.metadata: Dict[str, SemanticMetadata] = {}
        self.output_dir = None
    
    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[SEMANTIC] {message}")
    
    def _get_output_path(self, original_filepath: str, project_path: str) -> str:
        """Get output path preserving folder structure."""
        rel_path = os.path.relpath(original_filepath, project_path)
        return os.path.join(self.output_dir, rel_path)
    
    def _read_file(self, filepath: str) -> Tuple[str, List[str]]:
        """Read file and return content and lines."""
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        lines = content.splitlines(keepends=True)
        return content, lines
    
    def _write_file(self, filepath: str, content: str):
        """Write file creating parent directories as needed."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _fix_integer_division(self, lines: List[str], content: str) -> Tuple[List[str], List[int], int]:
        """Fix integer division operators.
        
        Returns:
            Tuple of (modified lines, changed line indices, fix count)
        """
        changed = []
        fix_count = 0
        
        try:
            tree = ast.parse(content)
            analyzer = DivisionAnalyzer(lines)
            analyzer.visit(tree)
            
            # If __future__ division is present, no fixes needed
            if analyzer.has_future_division:
                self.log("  __future__ division present, skipping division fixes")
                return lines, changed, 0
            
            # Group divisions by line
            divisions_by_line = defaultdict(list)
            for lineno, col_offset, left_type, right_type in analyzer.integer_divisions:
                divisions_by_line[lineno].append((col_offset, left_type, right_type))
            
            # Fix divisions (process in reverse order to maintain offsets)
            for lineno in sorted(divisions_by_line.keys(), reverse=True):
                if lineno <= len(lines):
                    idx = lineno - 1
                    line = lines[idx]
                    
                    # Sort by column offset in reverse order
                    for col_offset, left_type, right_type in sorted(divisions_by_line[lineno], reverse=True, key=lambda x: x[0]):
                        # Find the division operator
                        # Simple replacement: change first / after col_offset to //
                        pos = line.find('/', col_offset)
                        if pos != -1:
                            # Make sure it's not //= or // already
                            if pos + 1 < len(line) and line[pos + 1] not in ('/', '='):
                                line = line[:pos] + '//' + line[pos + 1:]
                                fix_count += 1
                    
                    if line != lines[idx]:
                        lines[idx] = line
                        changed.append(idx)
                        self.log(f"    Line {idx + 1}: Fixed integer division")
        
        except SyntaxError as e:
            self.log(f"  Could not parse for division analysis: {e}")
        
        return lines, changed, fix_count
    
    def _wrap_iterators(self, lines: List[str], content: str) -> Tuple[List[str], List[int], int]:
        """Wrap map/filter/zip calls that need to be lists.
        
        Returns:
            Tuple of (modified lines, changed line indices, wrap count)
        """
        changed = []
        wrap_count = 0
        
        try:
            tree = ast.parse(content)
            wrapper = IteratorWrapper(lines)
            wrapper.visit(tree)
            
            # Group wraps by line
            wraps_by_line = defaultdict(list)
            for lineno, col_offset, func_name in wrapper.wrapped_calls:
                wraps_by_line[lineno].append((col_offset, func_name))
            
            # Apply wraps (process in reverse order)
            for lineno in sorted(wraps_by_line.keys(), reverse=True):
                if lineno <= len(lines):
                    idx = lineno - 1
                    line = lines[idx]
                    
                    # Sort by column offset in reverse order
                    for col_offset, func_name in sorted(wraps_by_line[lineno], reverse=True, key=lambda x: x[0]):
                        # Find the function call
                        pos = line.find(f'{func_name}(', col_offset)
                        if pos != -1:
                            # Check if already wrapped in list()
                            before = line[:pos].rstrip()
                            if not before.endswith('list('):
                                # Find matching closing paren
                                paren_count = 0
                                end_pos = pos + len(func_name) + 1
                                for i in range(end_pos, len(line)):
                                    if line[i] == '(':
                                        paren_count += 1
                                    elif line[i] == ')':
                                        if paren_count == 0:
                                            end_pos = i + 1
                                            break
                                        paren_count -= 1
                                
                                # Wrap in list()
                                line = line[:pos] + 'list(' + line[pos:end_pos] + ')' + line[end_pos:]
                                wrap_count += 1
                    
                    if line != lines[idx]:
                        lines[idx] = line
                        changed.append(idx)
                        self.log(f"    Line {idx + 1}: Wrapped iterator in list()")
        
        except SyntaxError as e:
            self.log(f"  Could not parse for iterator analysis: {e}")
        
        return lines, changed, wrap_count
    
    def _fix_encoding_issues(self, lines: List[str], content: str) -> Tuple[List[str], List[int], int]:
        """Add explicit encoding to file opens.
        
        Returns:
            Tuple of (modified lines, changed line indices, fix count)
        """
        changed = []
        fix_count = 0
        
        try:
            tree = ast.parse(content)
            analyzer = EncodingAnalyzer(lines)
            analyzer.visit(tree)
            
            for lineno, issue_type, description in analyzer.encoding_issues:
                if lineno <= len(lines):
                    idx = lineno - 1
                    line = lines[idx]
                    
                    # Add encoding='utf-8' to open() calls
                    if 'open(' in line and 'encoding=' not in line:
                        # Find the closing paren
                        open_pos = line.find('open(')
                        if open_pos != -1:
                            # Find matching closing paren
                            paren_count = 0
                            start = open_pos + 5
                            end_pos = start
                            for i in range(start, len(line)):
                                if line[i] == '(':
                                    paren_count += 1
                                elif line[i] == ')':
                                    if paren_count == 0:
                                        end_pos = i
                                        break
                                    paren_count -= 1
                            
                            # Check if there are already arguments
                            args_content = line[start:end_pos].strip()
                            if args_content:
                                # Add encoding as keyword argument
                                line = line[:end_pos] + ", encoding='utf-8'" + line[end_pos:]
                            else:
                                # No arguments, just add encoding
                                line = line[:end_pos] + "encoding='utf-8'" + line[end_pos:]
                            
                            lines[idx] = line
                            changed.append(idx)
                            fix_count += 1
                            self.log(f"    Line {idx + 1}: Added explicit encoding to open()")
        
        except SyntaxError as e:
            self.log(f"  Could not parse for encoding analysis: {e}")
        
        return lines, changed, fix_count
    
    def _remove_py2_compat_blocks(self, lines: List[str]) -> Tuple[List[str], List[int], int]:
        """Remove Python 2/3 compatibility try-except blocks.
        
        Returns:
            Tuple of (modified lines, changed line indices, cleanup count)
        """
        changed = []
        cleanup_count = 0
        content = ''.join(lines)
        
        for pattern in self.PY2_COMPAT_PATTERNS:
            # Find multi-line compatibility blocks
            matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))
            
            for match in reversed(matches):  # Process in reverse to maintain positions
                start_pos = match.start()
                end_pos = match.end()
                
                # Find which lines this spans
                line_start = content[:start_pos].count('\n')
                line_end = content[:end_pos].count('\n')
                
                # Extract the Python 3 import (after except)
                try_except_text = match.group(0)
                py3_import = None
                
                # Parse to get the except clause
                if 'except ImportError:' in try_except_text:
                    parts = try_except_text.split('except ImportError:')
                    if len(parts) == 2:
                        py3_import = parts[1].strip()
                
                if py3_import:
                    # Replace the entire try-except with just the Python 3 import
                    indent = len(lines[line_start]) - len(lines[line_start].lstrip())
                    replacement = ' ' * indent + py3_import + '\n'
                    
                    # Remove the try-except block and insert the Python 3 import
                    for i in range(line_start, line_end + 1):
                        if i == line_start:
                            lines[i] = replacement
                            changed.append(i)
                        else:
                            lines[i] = ''
                            changed.append(i)
                    
                    cleanup_count += 1
                    self.log(f"    Lines {line_start + 1}-{line_end + 1}: Removed Python 2 compatibility block")
        
        # Remove empty lines left behind
        lines = [line for line in lines if line.strip() or line == '\n']
        
        return lines, changed, cleanup_count
    
    def _remove_redundant_future_imports(self, lines: List[str]) -> Tuple[List[str], List[int], int]:
        """Remove __future__ imports that are default in Python 3.
        
        Returns:
            Tuple of (modified lines, changed line indices, cleanup count)
        """
        changed = []
        cleanup_count = 0
        
        # These are default in Python 3
        redundant_imports = {
            'absolute_import',
            'division',
            'print_function',
            'unicode_literals',
        }
        
        for i, line in enumerate(lines):
            if 'from __future__ import' in line:
                # Parse what's being imported
                match = re.search(r'from __future__ import (.+)', line)
                if match:
                    imports_str = match.group(1)
                    imports = [imp.strip() for imp in imports_str.split(',')]
                    
                    # Filter out redundant imports
                    kept_imports = [imp for imp in imports if imp not in redundant_imports]
                    
                    if len(kept_imports) < len(imports):
                        if kept_imports:
                            # Keep only non-redundant imports
                            indent = len(line) - len(line.lstrip())
                            lines[i] = ' ' * indent + f"from __future__ import {', '.join(kept_imports)}\n"
                        else:
                            # Remove entire line
                            lines[i] = ''
                        
                        changed.append(i)
                        cleanup_count += 1
                        self.log(f"    Line {i + 1}: Removed redundant __future__ imports")
        
        # Remove empty lines
        lines = [line for line in lines if line.strip() or line == '\n']
        
        return lines, changed, cleanup_count
    
    def process_file(self, filepath: str, project_path: str) -> SemanticMetadata:
        """Process a single file for semantic fixes.
        
        Args:
            filepath: Path to the file.
            project_path: Root project path.
            
        Returns:
            SemanticMetadata object
        """
        self.log(f"Analyzing semantics: {filepath}")
        
        try:
            content, lines = self._read_file(filepath)
            
            all_changes = set()
            semantic_fixes = []
            warnings = []
            
            division_fixes = 0
            iterator_wraps = 0
            encoding_fixes = 0
            import_cleanups = 0
            
            # 1. Fix integer division
            lines, changed, count = self._fix_integer_division(lines, content)
            if changed:
                semantic_fixes.append('integer_division')
                all_changes.update(changed)
                division_fixes = count
            
            # 2. Wrap iterators
            content = ''.join(lines)
            lines, changed, count = self._wrap_iterators(lines, content)
            if changed:
                semantic_fixes.append('iterator_wrapping')
                all_changes.update(changed)
                iterator_wraps = count
            
            # 3. Fix encoding issues
            content = ''.join(lines)
            lines, changed, count = self._fix_encoding_issues(lines, content)
            if changed:
                semantic_fixes.append('encoding_fixes')
                all_changes.update(changed)
                encoding_fixes = count
            
            # 4. Remove Python 2 compatibility blocks
            lines, changed, count = self._remove_py2_compat_blocks(lines)
            if changed:
                semantic_fixes.append('py2_compat_cleanup')
                all_changes.update(changed)
                import_cleanups += count
            
            # 5. Remove redundant __future__ imports
            lines, changed, count = self._remove_redundant_future_imports(lines)
            if changed:
                semantic_fixes.append('future_import_cleanup')
                all_changes.update(changed)
                import_cleanups += count
            
            # Write output file
            modified_content = ''.join(lines)
            if not self.dry_run:
                output_path = self._get_output_path(filepath, project_path)
                self._write_file(output_path, modified_content)
            else:
                output_path = filepath
            
            # Verify output is still valid Python 3
            try:
                ast.parse(modified_content)
                parse_success = True
            except SyntaxError as e:
                parse_success = False
                warnings.append(f"Parse error after semantic fixes: {e}")
            
            metadata = SemanticMetadata(
                filename=output_path,
                original_filename=filepath,
                semantic_fixes=list(set(semantic_fixes)),
                lines_modified=sorted(list(all_changes)),
                division_fixes=division_fixes,
                iterator_wraps=iterator_wraps,
                encoding_fixes=encoding_fixes,
                import_cleanups=import_cleanups,
                warnings=warnings,
                parse_success=parse_success
            )
            
            self.metadata[filepath] = metadata
            status = "✓" if parse_success else "⚠"
            self.log(f"  {status} Fixes: {', '.join(metadata.semantic_fixes) or 'none'}")
            if warnings:
                self.log(f"  ⚠ {len(warnings)} warning(s)")
            
            return metadata
        
        except Exception as e:
            self.log(f"  ✗ Error processing file: {str(e)}")
            metadata = SemanticMetadata(
                filename=filepath,
                original_filename=filepath,
                semantic_fixes=[],
                lines_modified=[],
                warnings=[],
                errors=[str(e)],
                parse_success=False
            )
            self.metadata[filepath] = metadata
            return metadata
    
    def process_stage1_output(self, stage1_dir: str, project_path: str, session_dir: Optional[str] = None) -> Tuple[str, Dict]:
        """Process all files from Stage 1 output with better session handling."""
        self.log(f"Starting Stage 2 semantic analysis")
        
        # Improved session handling
        if session_dir:
            self.output_dir = session_dir
        elif self.dry_run:
            # For dry-run, create temp session to avoid modifying originals
            self.output_dir = tempfile.mkdtemp(prefix='py2to3_semantic_dryrun_')
            self.log(f"Dry-run: using temp directory: {self.output_dir}")
        else:
            # In-place updates to Stage 1 output
            self.output_dir = stage1_dir
        
        self.log(f"Output directory: {self.output_dir}")
        
        # Rest of the method remains the same...
        py_files = []
        for root, dirs, files in os.walk(stage1_dir):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'venv'}]
            for file in files:
                if file.endswith('.py') or file.endswith('.pyw'):  # Added .pyw support
                    # Skip generated files
                    if not any(pattern in file for pattern in ['_pb2.py', '_pb2_grpc.py']):
                        py_files.append(os.path.join(root, file))
        
        self.log(f"Found {len(py_files)} files to analyze")
        
        for filepath in sorted(py_files):
            self.process_file(filepath, stage1_dir)
        
        summary = self._generate_summary()
        return self.output_dir or '', summary
    
    def _generate_summary(self) -> Dict:
        """Generate a summary of semantic fixes."""
        total_files = len(self.metadata)
        successful_files = sum(1 for m in self.metadata.values() if m.parse_success)
        failed_files = total_files - successful_files
        total_lines_modified = sum(len(m.lines_modified) for m in self.metadata.values())
        total_warnings = sum(len(m.warnings) for m in self.metadata.values())
        total_division_fixes = sum(m.division_fixes for m in self.metadata.values())
        total_iterator_wraps = sum(m.iterator_wraps for m in self.metadata.values())
        total_encoding_fixes = sum(m.encoding_fixes for m in self.metadata.values())
        total_import_cleanups = sum(m.import_cleanups for m in self.metadata.values())
        
        summary = {
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'total_lines_modified': total_lines_modified,
            'total_warnings': total_warnings,
            'total_division_fixes': total_division_fixes,
            'total_iterator_wraps': total_iterator_wraps,
            'total_encoding_fixes': total_encoding_fixes,
            'total_import_cleanups': total_import_cleanups,
            'output_dir': self.output_dir
        }
        return summary
    
    def print_summary(self):
        """Print Stage 2 semantic analysis summary."""
        summary = self._generate_summary()
        print("\n" + "="*70)
        print("STAGE 2 SEMANTIC ANALYZER SUMMARY")
        print("="*70)
        print(f"Total files processed:     {summary['total_files']}")
        print(f"Successful files:          {summary['successful_files']}")
        print(f"Failed files:              {summary['failed_files']}")
        print(f"Total lines modified:      {summary['total_lines_modified']}")
        print(f"Total warnings:            {summary['total_warnings']}")
        print("\nSemantic Fixes Applied:")
        print(f"  Integer division fixes:  {summary['total_division_fixes']}")
        print(f"  Iterator wraps:          {summary['total_iterator_wraps']}")
        print(f"  Encoding fixes:          {summary['total_encoding_fixes']}")
        print(f"  Import cleanups:         {summary['total_import_cleanups']}")
        print(f"\nOutput directory:          {summary['output_dir']}")
        print("="*70 + "\n")
    
    def save_metadata(self, metadata_file: str):
        """Save semantic analysis metadata to JSON."""
        data = {k: asdict(v) for k, v in self.metadata.items()}
        os.makedirs(os.path.dirname(metadata_file), exist_ok=True)
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        self.log(f"Metadata saved to: {metadata_file}")


def main():
    """Run Stage 2 semantic analyzer."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python semantic_analyzer.py <stage1_dir> [--dry-run] [--verbose]")
        print("Example: python semantic_analyzer.py sessions/session_20251021_223023 --verbose")
        sys.exit(1)
    
    stage1_dir = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    verbose = '--verbose' in sys.argv
    
    if not os.path.isdir(stage1_dir):
        print(f"Error: {stage1_dir} is not a valid directory")
        sys.exit(1)
    
    # Stage 2 semantic analysis
    analyzer = SemanticAnalyzer(dry_run=dry_run, verbose=verbose)
    output_dir, summary = analyzer.process_stage1_output(stage1_dir, stage1_dir)
    
    # Print summary
    analyzer.print_summary()
    
    # Save metadata
    if not dry_run and output_dir:
        metadata_file = os.path.join(output_dir, 'semantic_metadata.json')
        analyzer.save_metadata(metadata_file)
        print(f"✓ Semantically fixed files available in: {output_dir}")
        print(f"✓ Metadata saved to: {metadata_file}")


if __name__ == '__main__':
    main()