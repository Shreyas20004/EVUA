
import os
import re
import ast
import json
import tempfile
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
class ModernizationMetadata:
    """Metadata for modernization changes per file."""
    filename: str
    original_filename: str
    modernizations_applied: List[str]
    lines_modified: List[int]
    import_changes: Dict[str, str]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    parse_success: bool = True


class ExceptionHandler(ast.NodeTransformer):
    """AST transformer for exception syntax updates."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.changes = []
    
    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        """Modernize exception handler syntax (except ... as ...)."""
        # This is already Python 3 syntax in the AST,
        # but we track it for documentation
        self.generic_visit(node)
        return node
    
    def visit_Raise(self, node: ast.Raise) -> ast.Raise:
        """Modernize raise statements."""
        # Raise with cause: raise Exception from e
        # Already handled by Python 3 AST
        self.generic_visit(node)
        return node


class OldStyleClassDetector(ast.NodeVisitor):
    """Detect old-style classes (no explicit object inheritance)."""
    
    def __init__(self):
        self.old_style_classes = []  # List of (class_name, lineno)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Detect classes that don't inherit from object."""
        # In Python 3, all classes implicitly inherit from object
        # But we detect explicit old-style patterns
        if not node.bases:
            # Class with no bases at all (old-style in Py2)
            self.old_style_classes.append((node.name, node.lineno))
        
        self.generic_visit(node)


class MetaclassReplacer(ast.NodeTransformer):
    """Find and flag metaclass assignments for manual conversion."""
    
    def __init__(self):
        self.metaclass_assignments = []  # (class_name, lineno)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Find __metaclass__ assignments in class body."""
        for i, item in enumerate(node.body):
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == '__metaclass__':
                        self.metaclass_assignments.append((node.name, node.lineno))
        
        self.generic_visit(node)
        return node


class Modernizer:
    """Stage 1: Modernize Python 2 idioms to Python 3."""
    
    # Import mapping: old_import -> (new_import, replacement_lines)
    IMPORT_MIGRATIONS = {
        'StringIO': ('io', 'from io import StringIO'),
        'cPickle': ('pickle', 'import pickle'),
        'ConfigParser': ('configparser', 'import configparser'),
        'Queue': ('queue', 'import queue'),
        'SocketServer': ('socketserver', 'import socketserver'),
        'xmlrpclib': ('xmlrpc.client', 'import xmlrpc.client'),
        'SimpleXMLRPCServer': ('xmlrpc.server', 'from xmlrpc.server import SimpleXMLRPCServer'),
        'Cookie': ('http.cookies', 'import http.cookies'),
        'BaseHTTPServer': ('http.server', 'import http.server'),
        'SimpleHTTPServer': ('http.server', 'import http.server'),
        'htmllib': ('html.parser', 'import html.parser'),
        'HTMLParser': ('html.parser', 'from html.parser import HTMLParser'),
        'urllib': ('urllib', 'import urllib.parse'),
        'urllib2': ('urllib', 'import urllib.request'),
        'urlparse': ('urllib.parse', 'from urllib.parse import urlparse'),
        'urllib_parse': ('urllib.parse', 'from urllib import parse'),
    }
    
    BUILTIN_RENAMES = {
        'basestring': 'str',
        'unicode': 'str',
        'long': 'int',
        'xrange': 'range',
        'raw_input': 'input',
    }
    
    BUILTIN_FUNCTIONS = {
        'apply': 'Use function(*args, **kwargs) instead',
        'buffer': 'Use memoryview() instead',
        'cmp': 'Use key= parameter or operator.attrgetter()',
        'execfile': 'Use exec(open(filename).read())',
        'file': 'Use open()',
        'reload': 'Use importlib.reload()',
        'reduce': 'Use functools.reduce()',
        'intern': 'Use sys.intern()',
        'coerce': 'Remove (not needed in Python 3)',
    }
    
    def __init__(self, stage0_metadata: Dict = None, dry_run: bool = False, verbose: bool = False):
        """Initialize modernizer.
        
        Args:
            stage0_metadata: Metadata from Stage 0 preprocessing (optional).
            dry_run: If True, show changes without writing files.
            verbose: If True, print detailed logs.
        """
        self.stage0_metadata = stage0_metadata or {}
        self.dry_run = dry_run
        self.verbose = verbose
        self.metadata: Dict[str, ModernizationMetadata] = {}
        self.output_dir = None
    
    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[MODERNIZER] {message}")
    
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
    
    def _detect_division_intent(self, content: str) -> bool:
        """Heuristically detect if code uses integer division."""
        # Look for patterns that suggest integer division
        patterns = [
            r'for\s+\w+\s+in\s+range\(\s*\w+\s*/\s*\d+',  # range(n/2)
            r'\w+\s*/\s*\d+\s*\)\s*as\s+\w+',
            r'\[\s*\d+\s*/\s*\d+\s*\]',
        ]
        return any(re.search(p, content) for p in patterns)
    
    def _update_exception_syntax(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Convert except Exception, e: to except Exception as e:.
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        
        for i, line in enumerate(lines):
            # Match: except ExceptionType, var:
            match = re.search(r'except\s+([^:,]+?)\s*,\s*(\w+)\s*:', line)
            if match:
                exception_type = match.group(1)
                var_name = match.group(2)
                indent = len(line) - len(line.lstrip())
                lines[i] = ' ' * indent + f'except {exception_type} as {var_name}:\n'
                changed.append(i)
                self.log(f"    Line {i+1}: Updated exception syntax")
        
        return lines, changed
    
    def _update_raise_syntax(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Convert raise Exception, value to raise Exception(value).
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        
        for i, line in enumerate(lines):
            # Match: raise ExceptionType, value [, traceback]
            match = re.search(r'raise\s+([A-Za-z_]\w*)\s*,\s*(.+?)(?:\s*,\s*(.+?))?$', line)
            if match:
                exception_type = match.group(1)
                value = match.group(2)
                traceback = match.group(3)
                
                indent = len(line) - len(line.lstrip())
                if traceback:
                    # raise Type, value, tb -> raise Type(value).with_traceback(tb)
                    lines[i] = ' ' * indent + f'raise {exception_type}({value}).with_traceback({traceback})\n'
                else:
                    lines[i] = ' ' * indent + f'raise {exception_type}({value})\n'
                
                changed.append(i)
                self.log(f"    Line {i+1}: Updated raise syntax")
        
        return lines, changed
    
    def _update_imports(self, lines: List[str]) -> Tuple[List[str], List[int], Dict[str, str]]:
        """Update imports from Python 2 to Python 3 equivalents.
        
        Returns:
            Tuple of (modified lines, changed line indices, import mappings)
        """
        changed = []
        import_changes = {}
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            for old_import, (new_module, replacement) in self.IMPORT_MIGRATIONS.items():
                # Match: import StringIO or from StringIO import X
                if re.search(rf'import\s+{re.escape(old_import)}', stripped):
                    lines[i] = line.replace(old_import, replacement.split()[-1])
                    import_changes[old_import] = replacement
                    changed.append(i)
                    self.log(f"    Line {i+1}: Migrated import '{old_import}' to '{new_module}'")
                
                # from StringIO import something
                elif re.search(rf'from\s+{re.escape(old_import)}\s+import', stripped):
                    if old_import in self.IMPORT_MIGRATIONS:
                        new_import = self.IMPORT_MIGRATIONS[old_import][1]
                        parts = stripped.split(' import ')
                        if len(parts) == 2:
                            what = parts[1]
                            lines[i] = ' ' * (len(line) - len(stripped)) + f'from {new_import.split()[-1]} import {what}\n'
                            import_changes[old_import] = new_import
                            changed.append(i)
                            self.log(f"    Line {i+1}: Migrated 'from {old_import}' import")
        
        return lines, changed, import_changes
    
    def _remove_unicode_prefix(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Remove u"string" prefixes (convert to "string").
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        
        for i, line in enumerate(lines):
            # Match u"..." or u'...'
            if re.search(r"\bu'", line) or re.search(r'\bu"', line):
                lines[i] = re.sub(r"\bu'", "'", line)
                lines[i] = re.sub(r'\bu"', '"', lines[i])
                changed.append(i)
                self.log(f"    Line {i+1}: Removed unicode prefix")
        
        return lines, changed
    
    def _update_raw_input(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Replace raw_input() with input().
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        
        for i, line in enumerate(lines):
            if re.search(r'\braw_input\b', line):
                lines[i] = re.sub(r'\braw_input\b', 'input', line)
                changed.append(i)
                self.log(f"    Line {i+1}: Converted raw_input() to input()")
        
        return lines, changed
    
    def _update_builtin_names(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Replace deprecated builtin names.
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        
        for i, line in enumerate(lines):
            for old_name, new_name in self.BUILTIN_RENAMES.items():
                # Use word boundaries to avoid partial matches
                if re.search(rf'\b{re.escape(old_name)}\b', line):
                    lines[i] = re.sub(rf'\b{re.escape(old_name)}\b', new_name, line)
                    changed.append(i)
                    self.log(f"    Line {i+1}: Renamed '{old_name}' to '{new_name}'")
                    break
        
        return lines, changed
    
    def _detect_old_style_classes(self, content: str) -> List[Tuple[str, int]]:
        """Detect old-style classes that should inherit from object.
        
        Returns:
            List of (class_name, lineno)
        """
        old_style = []
        
        try:
            tree = ast.parse(content)
            detector = OldStyleClassDetector()
            detector.visit(tree)
            old_style = detector.old_style_classes
        except SyntaxError:
            pass
        
        return old_style
    
    def _update_old_style_classes(self, lines: List[str], old_style_classes: List[Tuple[str, int]]) -> Tuple[List[str], List[int]]:
        """Convert old-style classes to inherit from object.
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        
        for class_name, lineno in old_style_classes:
            if lineno <= len(lines):
                i = lineno - 1
                line = lines[i]
                
                # Match: class ClassName:
                match = re.search(rf'class\s+{re.escape(class_name)}\s*:', line)
                if match:
                    lines[i] = line.replace(':', '(object):', 1)
                    changed.append(i)
                    self.log(f"    Line {i+1}: Updated old-style class to inherit from object")
        
        return lines, changed
    
    def _detect_metaclasses(self, content: str) -> List[Tuple[str, int]]:
        """Detect Python 2 metaclass assignments.
        
        Returns:
            List of (class_name, lineno)
        """
        metaclasses = []
        
        try:
            tree = ast.parse(content)
            replacer = MetaclassReplacer()
            replacer.visit(tree)
            metaclasses = replacer.metaclass_assignments
        except SyntaxError:
            pass
        
        return metaclasses
    
    def _flag_metaclass_for_review(self, lines: List[str], metaclasses: List[Tuple[str, int]]) -> List[str]:
        """Flag metaclass assignments for manual review.
        
        Returns:
            List of warnings
        """
        warnings = []
        
        for class_name, lineno in metaclasses:
            if lineno <= len(lines):
                i = lineno - 1
                # Comment with instruction
                lines[i] = f'# TODO: Convert metaclass syntax for {class_name}\n' + lines[i]
                msg = f"Line {i+1}: Manual metaclass conversion needed for '{class_name}'"
                warnings.append(msg)
                self.log(f"    {msg}")
        
        return warnings
    
    def _detect_deprecated_builtins(self, content: str) -> List[Tuple[str, int]]:
        """Detect usage of deprecated builtins that don't have direct replacements.
        
        Returns:
            List of (builtin_name, lineno)
        """
        deprecated = []
        
        lines = content.splitlines()
        for i, line in enumerate(lines):
            for builtin_name in self.BUILTIN_FUNCTIONS.keys():
                if re.search(rf'\b{re.escape(builtin_name)}\s*\(', line):
                    deprecated.append((builtin_name, i + 1))
        
        return deprecated
    
    def _flag_deprecated_builtins(self, deprecated: List[Tuple[str, int]]) -> List[str]:
        """Generate warnings for deprecated builtins.
        
        Returns:
            List of warnings
        """
        warnings = []
        
        for builtin_name, lineno in deprecated:
            msg = f"Line {lineno}: Deprecated builtin '{builtin_name}' - {self.BUILTIN_FUNCTIONS[builtin_name]}"
            warnings.append(msg)
            self.log(f"    ⚠ {msg}")
        
        return warnings
    
    def _add_division_import(self, lines: List[str]) -> bool:
        """Add 'from __future__ import division' if needed.
        
        Returns:
            True if added
        """
        # Check if already present
        for line in lines:
            if 'from __future__ import division' in line:
                return False
        
        # Add after other __future__ imports or at top
        added = False
        for i, line in enumerate(lines):
            if line.startswith('from __future__ import'):
                lines.insert(i + 1, 'from __future__ import division\n')
                added = True
                break
        
        if not added and lines:
            # Add at the top before other imports
            lines.insert(0, 'from __future__ import division\n')
            added = True
        
        return added
    
    def _detect_division_operators(self, content: str) -> List[int]:
        """Detect lines with division operators that might need //.
        
        Returns:
            List of line numbers with division operators
        """
        lines_with_div = []
        
        source_lines = content.splitlines()
        for i, line in enumerate(source_lines):
            # Simple heuristic: division in numeric context
            if re.search(r'(\d+|\w+)\s*/\s*(\d+|\w+)', line):
                lines_with_div.append(i + 1)
        
        return lines_with_div
    
    def _update_nonzero_to_bool(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Replace __nonzero__() with __bool__().
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        
        for i, line in enumerate(lines):
            if '__nonzero__' in line:
                lines[i] = line.replace('__nonzero__', '__bool__')
                changed.append(i)
                self.log(f"    Line {i+1}: Converted __nonzero__() to __bool__()")
        
        return lines, changed
    
    def _update_dict_methods(self, lines: List[str]) -> Tuple[List[str], List[int]]:
        """Handle dict methods that now return iterators in Python 3.
        
        Note: In most cases, this just needs documentation since the behavior
        is often compatible. We flag cases where list() wrapping might be needed.
        
        Returns:
            Tuple of (modified lines, changed line indices)
        """
        changed = []
        warnings = []
        
        for i, line in enumerate(lines):
            # Detect patterns like: for k in dict.keys():
            # In Python 3, this still works (views are iterable)
            # But list(dict.keys()) is explicitly for Python 2/3 compatibility
            
            if re.search(r'\.keys\(\)', line) or re.search(r'\.values\(\)', line) or re.search(r'\.items\(\)', line):
                # Check if it's being used in a context that requires a list
                if re.search(r'\[\s*.*?\s*for.*?in\s+(.*?)\.(?:keys|values|items)\(\)', line):
                    # This is likely fine in Python 3
                    pass
                elif re.search(r'len\s*\(\s*.*?\.(?:keys|values|items)\(\)', line):
                    # len() works with views in Python 3
                    pass
        
        return lines, changed
    
    def _update_map_filter_zip(self, lines: List[str]) -> List[str]:
        """Flag map/filter/zip usage that may need list() wrapping.
        
        Note: These now return iterators in Python 3. We flag for manual review.
        
        Returns:
            List of warnings
        """
        warnings = []
        
        for i, line in enumerate(lines):
            for builtin in ['map', 'filter', 'zip']:
                if re.search(rf'\b{builtin}\s*\(', line):
                    # Check if result is being indexed or used as list
                    if re.search(rf'{builtin}\([^)]*\)\[', line):
                        warnings.append(f"Line {i+1}: {builtin}() returns iterator; consider wrapping with list()")
                        self.log(f"    ⚠ Line {i+1}: {builtin}() may need list() wrapping")
        
        return warnings
    
    def process_file(self, filepath: str, project_path: str) -> ModernizationMetadata:
        """Process a single file for modernization.
        
        Args:
            filepath: Path to the processed Python file.
            project_path: Root project path.
            
        Returns:
            ModernizationMetadata object
        """
        self.log(f"Modernizing: {filepath}")
        
        try:
            content, lines = self._read_file(filepath)
            
            all_changes = set()
            modernizations = []
            warnings = []
            import_changes = {}
            
            # 1. Update exception syntax
            changed = self._update_exception_syntax(lines)[1]
            if changed:
                modernizations.append('exception_syntax')
                all_changes.update(changed)
            
            # 2. Update raise syntax
            changed = self._update_raise_syntax(lines)[1]
            if changed:
                modernizations.append('raise_syntax')
                all_changes.update(changed)
            
            # 3. Update imports
            lines, changed, import_changes = self._update_imports(lines)
            if changed:
                modernizations.append('imports')
                all_changes.update(changed)
            
            # 4. Remove unicode prefixes
            changed = self._remove_unicode_prefix(lines)[1]
            if changed:
                modernizations.append('unicode_literals')
                all_changes.update(changed)
            
            # 5. Replace raw_input
            changed = self._update_raw_input(lines)[1]
            if changed:
                modernizations.append('raw_input')
                all_changes.update(changed)
            
            # 6. Update builtin names
            changed = self._update_builtin_names(lines)[1]
            if changed:
                modernizations.append('builtin_names')
                all_changes.update(changed)
            
            # 7. Detect and update old-style classes
            modified_content = ''.join(lines)
            old_style = self._detect_old_style_classes(modified_content)
            if old_style:
                lines, changed = self._update_old_style_classes(lines, old_style)
                if changed:
                    modernizations.append('old_style_classes')
                    all_changes.update(changed)
            
            # 8. Detect metaclasses (flag for manual review)
            metaclasses = self._detect_metaclasses(modified_content)
            if metaclasses:
                metaclass_warnings = self._flag_metaclass_for_review(lines, metaclasses)
                warnings.extend(metaclass_warnings)
                modernizations.append('metaclass_review')
            
            # 9. Detect deprecated builtins
            deprecated = self._detect_deprecated_builtins(modified_content)
            if deprecated:
                deprecated_warnings = self._flag_deprecated_builtins(deprecated)
                warnings.extend(deprecated_warnings)
                modernizations.append('deprecated_builtins')
            
            # 10. Update __nonzero__ to __bool__
            changed = self._update_nonzero_to_bool(lines)[1]
            if changed:
                modernizations.append('nonzero_to_bool')
                all_changes.update(changed)
            
            # 11. Check for division operators
            div_lines = self._detect_division_operators(modified_content)
            if div_lines:
                warnings.append(f"Potential integer division on lines: {div_lines[:5]} (manual review recommended)")
                modernizations.append('division_review')
            
            # 12. Flag map/filter/zip
            map_warnings = self._update_map_filter_zip(lines)
            if map_warnings:
                warnings.extend(map_warnings)
                modernizations.append('map_filter_zip_review')
            
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
                warnings.append(f"Parse error after modernization: {e}")
            
            metadata = ModernizationMetadata(
                filename=output_path,
                original_filename=filepath,
                modernizations_applied=list(set(modernizations)),
                lines_modified=sorted(list(all_changes)),
                import_changes=import_changes,
                warnings=warnings,
                parse_success=parse_success
            )
            
            self.metadata[filepath] = metadata
            status = "✓" if parse_success else "⚠"
            self.log(f"  {status} Modernizations: {', '.join(metadata.modernizations_applied) or 'none'}")
            if warnings:
                self.log(f"  ⚠ {len(warnings)} warning(s)")
            
            return metadata
        
        except Exception as e:
            self.log(f"  ✗ Error processing file: {str(e)}")
            metadata = ModernizationMetadata(
                filename=filepath,
                original_filename=filepath,
                modernizations_applied=[],
                lines_modified=[],
                import_changes={},
                warnings=[],
                errors=[str(e)],
                parse_success=False
            )
            self.metadata[filepath] = metadata
            return metadata
    
    def process_stage0_output(self, stage0_temp_dir: str, project_path: str, session_dir: Optional[str] = None) -> Tuple[str, Dict]:
        """Process all files from Stage 0 output into the session folder.
        
        Args:
            stage0_temp_dir: Path to Stage 0 temp directory (session folder).
            project_path: Root project path.
            session_dir: If provided, use this folder for output (same as stage0 for in-place updates).
            
        Returns:
            Tuple of (output_dir, summary_dict)
        """
        self.log(f"Starting Stage 1 modernization")

        # Use the same session folder as Stage 0 for in-place modernization
        if session_dir:
            self.output_dir = session_dir
            self.log(f"Using provided session folder for output: {self.output_dir}")
        elif stage0_temp_dir:
            # Default: Use the same directory as Stage 0 output (in-place update)
            self.output_dir = stage0_temp_dir
            self.log(f"Using Stage 0 output directory for in-place modernization: {self.output_dir}")
        elif not self.dry_run:
            # Fallback: Create new temp directory
            self.output_dir = tempfile.mkdtemp(prefix='py2to3_stage1_')
            self.log(f"Created new output directory: {self.output_dir}")

        # Discover all .py files in stage0 output
        py_files = []
        for root, dirs, files in os.walk(stage0_temp_dir):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'venv'}]
            for file in files:
                if file.endswith('.py'):
                    py_files.append(os.path.join(root, file))

        self.log(f"Found {len(py_files)} files to modernize")

        for filepath in sorted(py_files):
            self.process_file(filepath, stage0_temp_dir)

        summary = self._generate_summary()

        return self.output_dir or '', summary

    
    def _generate_summary(self) -> Dict:
        """Generate a summary of modernization results."""
        total_files = len(self.metadata)
        successful_files = sum(1 for m in self.metadata.values() if m.parse_success)
        failed_files = total_files - successful_files
        total_lines_modified = sum(len(m.lines_modified) for m in self.metadata.values())
        total_warnings = sum(len(m.warnings) for m in self.metadata.values())
        summary = {
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'total_lines_modified': total_lines_modified,
            'total_warnings': total_warnings,
            'output_dir': self.output_dir
        }
        return summary

    def print_summary(self):
        """Print Stage 1 modernization summary."""
        summary = self._generate_summary()
        print("\n" + "="*70)
        print("STAGE 1 MODERNIZER SUMMARY")
        print("="*70)
        print(f"Total files processed:     {summary['total_files']}")
        print(f"Successful files:          {summary['successful_files']}")
        print(f"Failed files:              {summary['failed_files']}")
        print(f"Total lines modified:      {summary['total_lines_modified']}")
        print(f"Total warnings:            {summary['total_warnings']}")
        print(f"Output directory:          {summary['output_dir']}")
        print("="*70 + "\n")

    def save_metadata(self, metadata_file: str):
        """Save modernization metadata to JSON."""
        data = {k: asdict(v) for k, v in self.metadata.items()}
        os.makedirs(os.path.dirname(metadata_file), exist_ok=True)
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        self.log(f"Metadata saved to: {metadata_file}")


def main():
    """Run Stage 1 modernizer on Stage 0 session folder."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python modernizer.py <stage0_temp_dir> [--dry-run] [--verbose]")
        print("Example: python modernizer.py sessions/session_20251021_223023 --verbose")
        sys.exit(1)

    stage0_dir = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    verbose = '--verbose' in sys.argv

    if not os.path.isdir(stage0_dir):
        print(f"Error: {stage0_dir} is not a valid directory")
        sys.exit(1)

    # Stage 1 modernization
    modernizer = Modernizer(dry_run=dry_run, verbose=verbose)
    output_dir, summary = modernizer.process_stage0_output(stage0_dir, stage0_dir)

    # Print summary
    modernizer.print_summary()

    # Save metadata
    if not dry_run and output_dir:
        metadata_file = os.path.join(output_dir, 'modernization_metadata.json')
        modernizer.save_metadata(metadata_file)
        print(f"✓ Modernized files available in: {output_dir}")
        print(f"✓ Metadata saved to: {metadata_file}")


if __name__ == '__main__':
    main()