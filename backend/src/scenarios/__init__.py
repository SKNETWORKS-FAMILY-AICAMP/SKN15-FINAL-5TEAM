"""Scenario-specific hooks for the story engine.

Modules placed in this package can implement optional hook functions:

def on_stage_enter(state, stage, scenario):
    ...

def on_stage_complete(state, stage, scenario):
    ...

def patch_children_ctx(state, ctx, stage, scenario):
    return ctx
"""

__all__ = []
