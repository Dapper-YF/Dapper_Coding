# -*- coding: utf-8 -*-
import importlib.util
spec = importlib.util.spec_from_file_location("la", r'E:\Study\Dapper_Coding\learning_agent.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

# List public names
names = [n for n in dir(m) if not n.startswith('_')]
print('Public names:', names[:30])

# Check for classes
classes = [n for n in names if isinstance(getattr(m, n, None), type)]
print('Classes:', classes)

# Check for functions
funcs = [n for n in names if callable(getattr(m, n, None))]
print('Functions:', funcs[:20])
