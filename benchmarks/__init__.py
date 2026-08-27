"""Fault-injection benchmark: reproducible reliability numbers for the runtime.

Generates tasks across difficulty/fault categories, runs them through the real
mission runtime (scheduler + recovery + memory), and measures genuine outcomes —
task success, recovery rate, tool selection, memory retrieval, safety, planning
validity, cost, latency, and human-intervention. Numbers are real and seeded, not
placeholders.
"""
