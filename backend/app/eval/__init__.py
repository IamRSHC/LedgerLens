"""Evaluation utilities kept SEPARATE from production decision logic.

Nothing in `app.eval.*` is imported by controller/policy/resolver/repository/
agent/investigator. This module exists only so evaluation scripts can read
ground truth and score the engine + agent honestly.
"""
