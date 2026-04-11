"""
Tests for AST analyzer to demonstrate functionality.
"""

from src.utils.ast_analyzer import ASTAnalyzer, extract_changed_functions, parse_diff


def test_ast_analyzer_basic():
    """Test basic function extraction."""
    source_code = '''
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y
'''
    
    analyzer = ASTAnalyzer(source_code, "test.py")
    result = analyzer.analyze()
    
    # Should find 2 functions
    assert len(result['functions']) == 2
    assert 'add' in result['functions']
    assert 'multiply' in result['functions']
    
    # Check add signature
    add_info = result['functions']['add']
    assert add_info['name'] == 'add'
    assert add_info['args'] == ['x', 'y']
    assert add_info['arg_types'] == {'x': 'int', 'y': 'int'}
    assert add_info['return_type'] == 'int'
    
    print("✓ Basic function extraction works")


def test_ast_analyzer_class():
    """Test class extraction."""
    source_code = '''
class Calculator:
    """A simple calculator."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, x: int, y: int) -> int:
        return x + y
    
    async def multiply_async(self, x: float) -> float:
        return x * 2
'''
    
    analyzer = ASTAnalyzer(source_code, "test.py")
    result = analyzer.analyze()
    
    # Should find 1 class
    assert len(result['classes']) == 1
    assert 'Calculator' in result['classes']
    
    calc = result['classes']['Calculator']
    assert len(calc['methods']) == 3
    
    # Check async detection
    multiply_method = [m for m in calc['methods'] if m['name'] == 'multiply_async'][0]
    assert multiply_method['is_async'] is True
    
    print("✓ Class extraction works")


def test_call_graph():
    """Test call graph extraction."""
    source_code = '''
def helper(x):
    return x * 2

def main(y):
    result = helper(y)
    return result + 1

def unused():
    pass
'''
    
    analyzer = ASTAnalyzer(source_code, "test.py")
    result = analyzer.analyze()
    
    # Should find 1 call: main -> helper
    calls = result['calls']
    assert len(calls) == 1
    assert calls[0]['caller'] == 'main'
    assert calls[0]['callee'] == 'helper'
    
    print("✓ Call graph extraction works")


def test_parse_diff():
    """Test unified diff parsing."""
    diff_str = '''--- a/src/main.py
+++ b/src/main.py
@@ -10,3 +10,5 @@
 def old_function():
     pass
+
+def new_function():
+    return 42
--- a/src/utils.py
+++ b/src/utils.py
@@ -5,2 +5,3 @@
 def helper():
+    print("updated")
     return True
'''
    
    result = parse_diff(diff_str)
    
    # Should find 2 files
    assert 'src/main.py' in result
    assert 'src/utils.py' in result
    
    # Check line ranges
    main_ranges = result['src/main.py']
    assert len(main_ranges) >= 1
    
    print("✓ Unified diff parsing works")


def test_extract_changed_functions():
    """Test integration: find changed functions from diff."""
    source_code = '''
def function_a():
    return 1

def function_b():
    return 2

def function_c():
    return 3
'''
    
    # Diff that changes lines 5-6 (function_b)
    diff_str = '''--- a/test.py
+++ b/test.py
@@ -4,3 +4,3 @@
 def function_a():
     return 1
 def function_b():
-    return 2
+    return 2 # modified
 def function_c():
'''
    
    result = extract_changed_functions(source_code, diff_str, "test.py")
    
    assert result['parse_error'] is None
    assert 'function_b' in result['changed_functions']
    
    print("✓ Changed function detection works")


def test_decorators_and_async():
    """Test decorator and async detection."""
    source_code = '''
@property
def my_property(self):
    return self._value

@staticmethod
def static_method():
    return "static"

async def async_function():
    return "async"
'''
    
    analyzer = ASTAnalyzer(source_code, "test.py")
    result = analyzer.analyze()
    
    # Check property detection
    prop = result['functions']['my_property']
    assert 'property' in prop['decorators']
    
    # Check async detection
    async_func = result['functions']['async_function']
    assert async_func['is_async'] is True
    
    print("✓ Decorators and async detection works")


if __name__ == "__main__":
    test_ast_analyzer_basic()
    test_ast_analyzer_class()
    test_call_graph()
    test_parse_diff()
    test_extract_changed_functions()
    test_decorators_and_async()
    
    print("\n✅ All AST analyzer tests passed!")
