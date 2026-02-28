"""
Dependency checker and installer for Tolov integrations.
"""
import sys
import warnings
import subprocess
from typing import List


class DependencyError(ImportError):
    """Raised when required dependencies are missing."""
    pass


def check_dependencies(framework: str, raise_error: bool = False) -> bool:
    """
    Check if dependencies for a specific framework are installed.
    
    Args:
        framework: Framework name ('django', 'fastapi', 'flask')
        raise_error: If True, raise DependencyError instead of warning
        
    Returns:
        bool: True if all dependencies are available
        
    Raises:
        DependencyError: If raise_error=True and dependencies are missing
    """
    dependencies_map = {
        'django': {
            'packages': ['django'],
            'install_cmd': 'pip install tolov[django]',
            'manual_install': 'pip install django'
        },
        'fastapi': {
            'packages': ['fastapi', 'sqlalchemy', 'pydantic'],
            'install_cmd': 'pip install tolov[fastapi]',
            'manual_install': 'pip install fastapi sqlalchemy pydantic python-multipart'
        },
        'flask': {
            'packages': ['flask', 'flask_sqlalchemy'],
            'install_cmd': 'pip install tolov[flask]',
            'manual_install': 'pip install flask flask-sqlalchemy'
        }
    }
    
    if framework not in dependencies_map:
        raise ValueError(f"Unknown framework: {framework}")
    
    config = dependencies_map[framework]
    missing_packages = []
    
    for package in config['packages']:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        error_msg = (
            f"\n{'='*70}\n"
            f"Tolov: Missing dependencies for {framework.upper()}!\n"
            f"{'='*70}\n"
            f"Missing packages: {', '.join(missing_packages)}\n\n"
            f"To install all required dependencies, run:\n\n"
            f"  {config['install_cmd']}\n\n"
            f"Or install manually:\n\n"
            f"  {config['manual_install']}\n"
            f"{'='*70}\n"
        )
        
        if raise_error:
            raise DependencyError(error_msg)
        else:
            warnings.warn(error_msg, ImportWarning, stacklevel=2)
            return False
    
    return True


def require_framework(framework: str):
    """
    Decorator to check framework dependencies before function execution.
    
    Usage:
        @require_framework('django')
        def my_django_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            check_dependencies(framework, raise_error=True)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_missing_dependencies(framework: str) -> List[str]:
    """
    Get list of missing dependencies for a framework.
    
    Args:
        framework: Framework name ('django', 'fastapi', 'flask')
        
    Returns:
        List of missing package names
    """
    dependencies_map = {
        'django': ['django'],
        'fastapi': ['fastapi', 'sqlalchemy', 'pydantic'],
        'flask': ['flask', 'flask_sqlalchemy']
    }
    
    if framework not in dependencies_map:
        raise ValueError(f"Unknown framework: {framework}")
    
    missing = []
    for package in dependencies_map[framework]:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return missing


def install_framework_dependencies(framework: str) -> bool:
    """
    Attempt to install framework dependencies using pip.
    
    Args:
        framework: Framework name ('django', 'fastapi', 'flask')
        
    Returns:
        bool: True if installation successful
    """

    extras_map = {
        'django': 'django',
        'fastapi': 'fastapi',
        'flask': 'flask'
    }

    if framework not in extras_map:
        raise ValueError(f"Unknown framework: {framework}")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", f"tolov[{extras_map[framework]}]"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except subprocess.CalledProcessError:
        return False
