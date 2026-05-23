---
description: Create a spec file for the next development step 
argument-hint: "Step number, feature name, and description e.g. 2 registration \"Allow users to sign up with email and password\""
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer guide to a junior developer. Always follow the rules in CLAUDE.md.

User input: $ARGUMENTS

## Step 1 — Parse the arguments
From $ARGUMENTS extract:

1. `step_number` — zero-padded to 2 digits: 2 → 02, 11 → 11

2. `feature_title` — human readable title in Title Case
   - Example: "Registration" or "Login and Logout"

3. `feature_slug` — git and file safe slug
   - Lowercase, kebab-case
   - Only a-z, 0-9 and -
   - Maximum 40 characters
   - Example: registration, login-logout

4. `feature_description` — optional free-text description provided by the user
   - Use verbatim from $ARGUMENTS if provided
   - If not provided, leave empty — Claude will infer the overview from the codebase

If you cannot infer these from $ARGUMENTS, ask the user
to clarify before proceeding.


## Step 2 — Research the codebase
Read these files before writing the spec:
- `CLAUDE.md` — roadmap, conventions, schema
- All files in `.claude/specs/` — avoid duplicating existing specs

Check `CLAUDE.md` to confirm the requested step is not already
marked complete. If it is, warn the user and stop.

## Step 3 — Write the spec
Generate a spec document with this exact structure:

---
# Spec: <feature_title>

## Overview
If `feature_description` was provided, use it as the basis for this paragraph.
Otherwise, write one paragraph describing what this feature does and why
it exists at this stage of the development roadmap.

## Depends on
Which previous steps this feature requires to be complete.

## Implementation steps 
Step by step guide for junior developer to follow.

## Files to change
Every file that will be modified.

## Files to create
Every new file that will be created.

## New dependencies
Any new python packages. If none: state "No new dependencies".

## Definition of done
A specific testable checklist. Each item must be
something that can be verified by running the app.
---

## Step 4 — Save the spec
Save to: `.claude/specs/<step_number>-<feature_slug>.md`

## Step 5 — Report to the user
Print a short summary in this exact format:
```
Spec file: .claude/specs/<step_number>-<feature_slug>.md
Title:     <feature_title>
```

Do not print the full spec in chat unless explicitly asked.