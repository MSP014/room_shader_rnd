# Technical Debt Notice: Pip Security Lock

**Attention**: Shader RND Agent

## Issue

Your environment (`shader_rnd`) is running `pip 24.0`.
If you plan to upgrade, do **NOT** exceed `pip 25.3`. `pip 26.0+` breaks `pip-tools`.

## Instruction

1. Maintain `pip <= 25.3` until `pip-tools` releases a fix (approx. Late Feb 2026).
2. Monitor `pip-tools` updates.
