# -*- coding: utf-8 -*-
import importlib.util
spec = importlib.util.spec_from_file_location("la", r'E:\Study\Dapper_Coding\learning_agent.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

import inspect

# Check process_user_message signature
print('process_user_message:', inspect.signature(m.process_user_message))
print()

# Check LearningAgent
la_cls = m.LearningAgent
print('LearningAgent methods:', [x for x in dir(la_cls) if not x.startswith('_')])
