"""Evolus integration for Two Hands: the paper-form intake process runs as an Evolus case.

Building blocks driven over the Evolus REST API (see docs/EVOLUS.md for every endpoint and its doc URL):
  * document extractor  - an independent third reader of the masked page (compared, never trusted blindly)
  * agent chat          - an Evolus agent running on Gemma-4-31B-IT on AMD drafts the reviewer note
  * AI Tool "translate" - turns the note into Spanish for the records-office reviewer
  * knowledge library   - accepted records are filed as documents (the office's register)
  * workflow            - routed forms start the "review hand-off" workflow (a person takes the case)
Our own gate (POST /api/gate) decides; Evolus carries the case.
"""
