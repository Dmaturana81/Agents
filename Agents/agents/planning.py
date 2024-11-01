"""Planning agent using instructor library"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/03_planning_agent.ipynb.

# %% auto 0
__all__ = ['TaskGraph', 'foo']

# %% ../../nbs/03_planning_agent.ipynb 4
from pydantic import BaseModel
from typing import List, Dict

class TaskGraph(BaseModel):
    """A graph of tasks and their dependencies"""
    tasks: List[str]
    dependencies: Dict[str, List[str]]


# %% ../../nbs/03_planning_agent.ipynb 5
def foo(): pass
