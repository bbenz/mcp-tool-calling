# Prompts

The prompts that generated this repository, kept so the demo can be regenerated,
extended, or re-targeted at a different event rather than hand-patched.

| File | What it does |
| --- | --- |
| `demopromptv2.md` | **Start here.** The prompt that produced the demo and its documentation, in phases. |
| `demopromptv1.md` | The first draft, superseded by v2. Kept for the comparison below. |
| `comparison-demopromptv1-vs-v2.md` | What changed between v1 and v2, and why. Useful if you are writing a prompt of this size yourself. |
| `powerpointprompt-claude v1.md` | Generates the conference deck. Written for Claude. |
| `powerpointprompt-gpt6 v1.md` | The same job, written for GPT-6. Self-contained — it does not need the chat history. |

## One external input

Every prompt here treats the accepted conference proposal as its requirements
document, and refers to it as:

```
Events/MCP-Dev-Summit-Toronto-2026-Approved-Proposals.md
```

**That file is deliberately not in this repository.** It is a personal
conference submission rather than anything you need in order to run the demo,
so it is kept with the presenter's own event material.

The prompts still run without it — supply your own source of requirements in its
place. If you are adapting this demo for a different talk, that substitution is
the point: replace the proposal with your own session description and the rest of
the prompt still holds.

## Before you re-run one of these

These prompts build and deploy things. Read the phase you are about to run
first, and note that the deck prompts are written to inspect the repository
rather than to execute it — they will not run tests or touch a deployment.
