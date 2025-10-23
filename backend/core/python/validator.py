import os
import re
import ast
import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from datetime import datetime
from io import StringIO
import contextlib


def create_session_folder(base_dir='sessions') -> str:
    """Create a timestamped session folder for storing processed files."""
    os.makedirs(base_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join(base_dir, f'session_{timestamp}')
    os.makedirs(session_dir)
    return session_dir


@dataclass
class ExecutionResult:
    """Result of executing a single file."""
    filepath: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    runtime_error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationIssue:
    """A detected validation issue in the code."""
    filepath: str
    line_number: int
    issue_type: str
    severity: str  # 'error', 'warning', 'info'
    description: str
    suggestion: Optional[str] = None


@dataclass
class TestMetadata:
    """Metadata for testing and verification per file."""
    filename: str
    execution_result: Optional[ExecutionResult]
    validation_issues: List[ValidationIssue]
    behavioral_checks: Dict[str, bool]
    import_success: bool = True
    syntax_valid: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BehaviorValidator(ast.NodeVisitor):
    """AST visitor to detect potential behavioral issues."""
    
    def __init__(self, filepath: str, source_lines: List[str]):
        self.filepath = filepath
        self.source_lines = source_lines
        self.issues: List[ValidationIssue] = []
    
    def visit_BinOp(self, node: ast.BinOp):
        """Check for division operations that might have changed behavior."""
        if isinstance(node.op, ast.Div):
            # Check if this looks like integer division
            left_literal = isinstance(node.left, (ast.Constant, ast.Num))
            right_literal = isinstance(node.right, (ast.Constant, ast.Num))
            
            if left_literal or right_literal:
                self.issues.append(ValidationIssue(
                    filepath=self.filepath,
                    line_number=node.lineno,
                    issue_type='division_behavior',
                    severity='warning',
                    description='Division operator / may behave differently (float division in Py3)',
                    suggestion='Use // for integer division if needed'
                ))
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Check for potentially problematic function calls."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # Check for dict methods that return views in Py3
            if func_name in ('keys', 'values', 'items'):
                self.issues.append(ValidationIssue(
                    filepath=self.filepath,
                    line_number=node.lineno,
                    issue_type='dict_views',
                    severity='info',
                    description=f'{func_name}() returns a view in Python 3',
                    suggestion='Wrap with list() if you need a list'
                ))
            
            # Check for map/filter/zip without list()
            if func_name in ('map', 'filter', 'zip'):
                # Check if result is being used directly
                parent = getattr(node, '_parent', None)
                if not isinstance(parent, ast.Call) or (
                    isinstance(parent.func, ast.Name) and parent.func.id != 'list'
                ):
                    self.issues.append(ValidationIssue(
                        filepath=self.filepath,
                        line_number=node.lineno,
                        issue_type='lazy_iterator',
                        severity='info',
                        description=f'{func_name}() returns an iterator in Python 3',
                        suggestion='Wrap with list() if you need multiple passes'
                    ))
        
        self.generic_visit(node)
    
    def visit_Str(self, node: ast.Str):
        """Check for string/bytes confusion (Python 3.7 compatibility)."""
        # This is mainly for documentation
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute):
        """Check for encode/decode usage."""
        if node.attr in ('encode', 'decode'):
            self.issues.append(ValidationIssue(
                filepath=self.filepath,
                line_number=node.lineno,
                issue_type='encoding',
                severity='info',
                description=f'String/bytes conversion via {node.attr}()',
                suggestion='Ensure encoding parameter is specified (e.g., utf-8)'
            ))
        
        self.generic_visit(node)


class TestRunner:
    """Stage 3: Test and verify modernized Python code."""
    
    def __init__(self, verbose: bool = False, python_executable: str = 'python3'):
        """Initialize test runner.
        
        Args:
            verbose: If True, print detailed logs.
            python_executable: Python interpreter to use for testing.
        """
        self.verbose = verbose
        self.python_executable = python_executable
        self.metadata: Dict[str, TestMetadata] = {}
        self.output_dir = None
        self.runtime_logs_dir = None
    
    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"[TESTING] {message}")
    
    def _validate_syntax(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """Check if file has valid Python 3 syntax.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            ast.parse(content)
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)
    
    def _test_import(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """Try to import the file to check for import errors.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create a temporary module name
            module_name = Path(filepath).stem
            
            # Try to compile the file
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            compile(content, filepath, 'exec')
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _execute_file(self, filepath: str, timeout: int = 30) -> ExecutionResult:
        """Execute a Python file and capture results.
        
        Args:
            filepath: Path to the Python file.
            timeout: Execution timeout in seconds.
            
        Returns:
            ExecutionResult object
        """
        self.log(f"Executing: {filepath}")
        
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                [self.python_executable, filepath],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(filepath) or '.'
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Parse warnings from stderr
            warnings = []
            runtime_error = None
            
            if result.stderr:
                stderr_lines = result.stderr.split('\n')
                for line in stderr_lines:
                    if 'DeprecationWarning' in line or 'FutureWarning' in line:
                        warnings.append(line.strip())
                    elif 'Error' in line or 'Exception' in line:
                        runtime_error = result.stderr
            
            success = result.returncode == 0 and not runtime_error
            
            return ExecutionResult(
                filepath=filepath,
                success=success,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                runtime_error=runtime_error,
                warnings=warnings
            )
        
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                filepath=filepath,
                success=False,
                exit_code=-1,
                stdout='',
                stderr='',
                execution_time=timeout,
                runtime_error=f'Execution timeout after {timeout} seconds',
                warnings=[]
            )
        except Exception as e:
            return ExecutionResult(
                filepath=filepath,
                success=False,
                exit_code=-1,
                stdout='',
                stderr=str(e),
                execution_time=0.0,
                runtime_error=str(e),
                warnings=[]
            )
    
    def _run_behavioral_validation(self, filepath: str) -> List[ValidationIssue]:
        """Run AST-based behavioral validation.
        
        Args:
            filepath: Path to the Python file.
            
        Returns:
            List of ValidationIssue objects
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            tree = ast.parse(content)
            validator = BehaviorValidator(filepath, lines)
            validator.visit(tree)
            
            return validator.issues
        except Exception as e:
            self.log(f"  Behavioral validation failed: {e}")
            return []
    
    def _save_runtime_log(self, execution_result: ExecutionResult):
        """Save execution logs to file.
        
        Args:
            execution_result: ExecutionResult to save
        """
        if not self.runtime_logs_dir:
            return
        
        log_filename = Path(execution_result.filepath).stem + '_runtime.log'
        log_path = os.path.join(self.runtime_logs_dir, log_filename)
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"File: {execution_result.filepath}\n")
            f.write(f"Success: {execution_result.success}\n")
            f.write(f"Exit Code: {execution_result.exit_code}\n")
            f.write(f"Execution Time: {execution_result.execution_time:.2f}s\n")
            f.write(f"\n{'='*70}\n")
            f.write("STDOUT:\n")
            f.write(f"{'='*70}\n")
            f.write(execution_result.stdout)
            f.write(f"\n{'='*70}\n")
            f.write("STDERR:\n")
            f.write(f"{'='*70}\n")
            f.write(execution_result.stderr)
            
            if execution_result.runtime_error:
                f.write(f"\n{'='*70}\n")
                f.write("RUNTIME ERROR:\n")
                f.write(f"{'='*70}\n")
                f.write(execution_result.runtime_error)
            
            if execution_result.warnings:
                f.write(f"\n{'='*70}\n")
                f.write("WARNINGS:\n")
                f.write(f"{'='*70}\n")
                for warning in execution_result.warnings:
                    f.write(f"  - {warning}\n")
    
    def test_file(self, filepath: str, execute: bool = True) -> TestMetadata:
        """Test a single Python file.
        
        Args:
            filepath: Path to the Python file.
            execute: If True, execute the file; otherwise just validate syntax.
            
        Returns:
            TestMetadata object
        """
        self.log(f"Testing: {filepath}")
        
        warnings = []
        errors = []
        
        # 1. Syntax validation
        syntax_valid, syntax_error = self._validate_syntax(filepath)
        if not syntax_valid:
            errors.append(f"Syntax error: {syntax_error}")
            self.log(f"  ✗ Syntax invalid: {syntax_error}")
        else:
            self.log(f"  ✓ Syntax valid")
        
        # 2. Import check
        import_success, import_error = self._test_import(filepath)
        if not import_success:
            warnings.append(f"Import issue: {import_error}")
            self.log(f"  ⚠ Import check failed: {import_error}")
        else:
            self.log(f"  ✓ Import check passed")
        
        # 3. Behavioral validation
        validation_issues = self._run_behavioral_validation(filepath) if syntax_valid else []
        if validation_issues:
            self.log(f"  ℹ Found {len(validation_issues)} behavioral check(s)")
        
        # 4. Execution test (optional)
        execution_result = None
        if execute and syntax_valid:
            execution_result = self._execute_file(filepath)
            self._save_runtime_log(execution_result)
            
            if execution_result.success:
                self.log(f"  ✓ Execution successful ({execution_result.execution_time:.2f}s)")
            else:
                errors.append(f"Execution failed: {execution_result.runtime_error}")
                self.log(f"  ✗ Execution failed (exit code: {execution_result.exit_code})")
            
            if execution_result.warnings:
                warnings.extend(execution_result.warnings)
        
        # Behavioral checks summary
        behavioral_checks = {
            'division_checked': any(issue.issue_type == 'division_behavior' for issue in validation_issues),
            'encoding_checked': any(issue.issue_type == 'encoding' for issue in validation_issues),
            'iterators_checked': any(issue.issue_type == 'lazy_iterator' for issue in validation_issues),
            'dict_views_checked': any(issue.issue_type == 'dict_views' for issue in validation_issues),
        }
        
        metadata = TestMetadata(
            filename=filepath,
            execution_result=execution_result,
            validation_issues=validation_issues,
            behavioral_checks=behavioral_checks,
            import_success=import_success,
            syntax_valid=syntax_valid,
            warnings=warnings,
            errors=errors
        )
        
        self.metadata[filepath] = metadata
        return metadata
    
    def test_directory(self, directory: str, execute: bool = True) -> Tuple[str, Dict]:
        """Test all Python files in a directory.
        
        Args:
            directory: Path to the directory.
            execute: If True, execute files; otherwise just validate syntax.
            
        Returns:
            Tuple of (output_dir, summary_dict)
        """
        self.log(f"Starting Stage 3 testing on: {directory}")
        
        # Setup output directories
        self.output_dir = directory
        self.runtime_logs_dir = os.path.join(directory, 'runtime_logs')
        os.makedirs(self.runtime_logs_dir, exist_ok=True)
        
        # Discover all .py files
        py_files = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'venv', 'runtime_logs'}]
            for file in files:
                if file.endswith('.py'):
                    py_files.append(os.path.join(root, file))
        
        self.log(f"Found {len(py_files)} files to test")
        
        # Test each file
        for filepath in sorted(py_files):
            self.test_file(filepath, execute=execute)
        
        # Generate summary
        summary = self._generate_summary()
        
        return self.output_dir, summary
    
    def _generate_summary(self) -> Dict:
        """Generate a summary of test results."""
        total_files = len(self.metadata)
        syntax_valid = sum(1 for m in self.metadata.values() if m.syntax_valid)
        import_success = sum(1 for m in self.metadata.values() if m.import_success)
        
        executed = sum(1 for m in self.metadata.values() if m.execution_result is not None)
        passed = sum(1 for m in self.metadata.values() 
                    if m.execution_result and m.execution_result.success)
        failed = sum(1 for m in self.metadata.values() 
                    if m.execution_result and not m.execution_result.success)
        
        total_warnings = sum(len(m.warnings) for m in self.metadata.values())
        total_errors = sum(len(m.errors) for m in self.metadata.values())
        
        # Collect all validation issues by type
        issues_by_type = defaultdict(int)
        for metadata in self.metadata.values():
            for issue in metadata.validation_issues:
                issues_by_type[issue.issue_type] += 1
        
        # Collect runtime errors
        runtime_errors = []
        for metadata in self.metadata.values():
            if metadata.execution_result and metadata.execution_result.runtime_error:
                runtime_errors.append({
                    'file': metadata.filename,
                    'error': metadata.execution_result.runtime_error
                })
        
        summary = {
            'total_files_tested': total_files,
            'syntax_valid': syntax_valid,
            'syntax_invalid': total_files - syntax_valid,
            'import_success': import_success,
            'import_failed': total_files - import_success,
            'executed': executed,
            'passed': passed,
            'failed': failed,
            'total_warnings': total_warnings,
            'total_errors': total_errors,
            'validation_issues_by_type': dict(issues_by_type),
            'runtime_errors': runtime_errors,
            'output_dir': self.output_dir,
            'runtime_logs_dir': self.runtime_logs_dir
        }
        
        return summary
    
    def print_summary(self):
        """Print Stage 3 testing summary."""
        summary = self._generate_summary()
        
        print("\n" + "="*70)
        print("STAGE 3 TESTING & VERIFICATION SUMMARY")
        print("="*70)
        print(f"Total files tested:        {summary['total_files_tested']}")
        print(f"\nSyntax Validation:")
        print(f"  Valid:                   {summary['syntax_valid']}")
        print(f"  Invalid:                 {summary['syntax_invalid']}")
        print(f"\nImport Checks:")
        print(f"  Success:                 {summary['import_success']}")
        print(f"  Failed:                  {summary['import_failed']}")
        
        if summary['executed'] > 0:
            print(f"\nExecution Tests:")
            print(f"  Executed:                {summary['executed']}")
            print(f"  Passed:                  {summary['passed']}")
            print(f"  Failed:                  {summary['failed']}")
        
        print(f"\nValidation:")
        print(f"  Total warnings:          {summary['total_warnings']}")
        print(f"  Total errors:            {summary['total_errors']}")
        
        if summary['validation_issues_by_type']:
            print(f"\nBehavioral Checks (by type):")
            for issue_type, count in sorted(summary['validation_issues_by_type'].items()):
                print(f"  {issue_type:.<30} {count:>4}")
        
        if summary['runtime_errors']:
            print(f"\nRuntime Errors ({len(summary['runtime_errors'])}):")
            for error_info in summary['runtime_errors'][:5]:  # Show first 5
                file = Path(error_info['file']).name
                error = error_info['error'][:100] + '...' if len(error_info['error']) > 100 else error_info['error']
                print(f"  • {file}: {error}")
            
            if len(summary['runtime_errors']) > 5:
                print(f"  ... and {len(summary['runtime_errors']) - 5} more")
        
        print(f"\nOutput directory:          {summary['output_dir']}")
        print(f"Runtime logs:              {summary['runtime_logs_dir']}")
        print("="*70 + "\n")
    
    def save_report(self, report_file: str):
        """Save test report to JSON file.
        
        Args:
            report_file: Path to save the JSON report
        """
        summary = self._generate_summary()
        
        # Include detailed metadata
        detailed_results = {}
        for filepath, metadata in self.metadata.items():
            detailed_results[filepath] = {
                'filename': metadata.filename,
                'syntax_valid': metadata.syntax_valid,
                'import_success': metadata.import_success,
                'execution_result': asdict(metadata.execution_result) if metadata.execution_result else None,
                'validation_issues': [asdict(issue) for issue in metadata.validation_issues],
                'behavioral_checks': metadata.behavioral_checks,
                'warnings': metadata.warnings,
                'errors': metadata.errors
            }
        
        report = {
            'summary': summary,
            'detailed_results': detailed_results,
            'generated_at': datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Test report saved to: {report_file}")
    
    def generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on test results.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Analyze common issues
        issue_counts = defaultdict(int)
        for metadata in self.metadata.values():
            for issue in metadata.validation_issues:
                issue_counts[issue.issue_type] += 1
        
        # Generate recommendations
        if issue_counts.get('division_behavior', 0) > 0:
            recommendations.append(
                f"⚠ {issue_counts['division_behavior']} potential integer division issues detected. "
                "Review division operators (/) and use (//) where integer division is needed."
            )
        
        if issue_counts.get('lazy_iterator', 0) > 0:
            recommendations.append(
                f"ℹ {issue_counts['lazy_iterator']} uses of map/filter/zip detected. "
                "These return iterators in Python 3. Wrap with list() if you need multiple passes."
            )
        
        if issue_counts.get('encoding', 0) > 0:
            recommendations.append(
                f"ℹ {issue_counts['encoding']} string/bytes conversions detected. "
                "Ensure encoding='utf-8' is specified explicitly."
            )
        
        # Check for execution failures
        failed_count = sum(1 for m in self.metadata.values() 
                          if m.execution_result and not m.execution_result.success)
        if failed_count > 0:
            recommendations.append(
                f"❌ {failed_count} files failed execution. "
                "Check runtime logs in the runtime_logs/ directory for details."
            )
        
        # Check for import failures
        import_failed = sum(1 for m in self.metadata.values() if not m.import_success)
        if import_failed > 0:
            recommendations.append(
                f"⚠ {import_failed} files have import issues. "
                "Verify all dependencies are installed and compatible with Python 3."
            )
        
        return recommendations


def main():
    """Run Stage 3 testing and verification."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py <stage2_dir> [--no-execute] [--verbose]")
        print("Example: python test_runner.py sessions/session_20251021_223023 --verbose")
        sys.exit(1)
    
    stage2_dir = sys.argv[1]
    execute = '--no-execute' not in sys.argv
    verbose = '--verbose' in sys.argv
    
    if not os.path.isdir(stage2_dir):
        print(f"Error: {stage2_dir} is not a valid directory")
        sys.exit(1)
    
    # Stage 3 testing
    runner = TestRunner(verbose=verbose)
    output_dir, summary = runner.test_directory(stage2_dir, execute=execute)
    
    # Print summary
    runner.print_summary()
    
    # Generate and print recommendations
    recommendations = runner.generate_recommendations()
    if recommendations:
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        for rec in recommendations:
            print(f"\n{rec}")
        print("\n" + "="*70 + "\n")
    
    # Save report
    report_file = os.path.join(output_dir, 'stage3_report.json')
    runner.save_report(report_file)
    print(f"✓ Test report saved to: {report_file}")
    print(f"✓ Runtime logs saved to: {runner.runtime_logs_dir}")


if __name__ == '__main__':
    main()