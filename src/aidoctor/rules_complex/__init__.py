"""rules_complex — Python-coded rules that need flow logic beyond declarative kinds.

These are the ~30% of rules where AST traversal + small reasoning beats
shoehorning into a generic detect kind. Registered with the declarative
engine's python escape hatch via register_python_detector().
"""
