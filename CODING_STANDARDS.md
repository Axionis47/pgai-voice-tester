# Coding Standards

Every piece of code in this project is written by a coding subagent. This file is
the contract they must follow. The director reviews and approves but may not read
code line by line, so the code itself and its documentation must make the intent
obvious to anyone, including a beginner.

## Core rule

Write the simplest code that works. Optimize for a reader who is new to the
codebase, not for cleverness or brevity.

## Naming

- Use full, descriptive names. `transcribe_call` not `tc`. `patient_reply` not `pr`.
- No single letter variables except a simple loop counter.
- Names should say what the thing is or does in plain words.

## Functions

- One function does one job.
- Keep functions short enough to read on one screen.
- If a function needs a comment to explain a section, that section probably wants
  to be its own function with a clear name.

## Documentation (this matters most here)

- Every file starts with a short header comment: what this file is for, in one or
  two plain sentences.
- Every function has a docstring that explains, in plain English, what it does,
  what goes in, and what comes out.
- Comments explain why, not what. The code already shows what.
- Assume the reader will read the docs, not trace the logic. The docs must stand
  on their own.

## What to avoid

- No clever one liners. No dense comprehensions stacked together. Unpack logic
  into readable steps.
- No premature abstraction. Do not build a framework for a single use.
- No dead code. Delete it, do not comment it out.
- No AI attribution, no AI sounding filler, no decorative comments.
- No undocumented magic numbers. Give them names or explain them.

## Structure

- One file, one job. A file should have a clear single purpose.
- Configuration lives in config files, not hard coded inside the logic.
- Follow the patterns already in the repo. Consistency beats personal taste.

## Errors

- Handle errors explicitly and describe what went wrong in plain language.
- Fail loudly during development. Do not swallow errors silently.

## The test

Before code is considered done, ask: could a beginner open this file, read the
header and the docstrings, and understand what it does without asking anyone?
If not, it is not done.
