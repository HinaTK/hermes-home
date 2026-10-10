---
name: agreed-plan-execution
description: "Use when an agreed multi-step plan is in force. Keep it."
---

# Agreed plan execution

Use this whenever a session already has a sequenced plan (health check → fix → UI → scheduler, etc.) and new findings, nits, or field audits appear mid-work.

## Iron rule

The last **explicitly agreed** next step stays in force until the user changes it. An audit gap is a **note**, not a new plan.

Before you say “下一步” or start implementing after “好 / 你决定吧 / 做吧”, restate the agreed sequence in one line and act on **that** item. Do not act on whatever you just discovered.

## In-session stickiness (this is the usual failure)

Long chats get compressed. Plans live in the conversation, not in durable memory unless the user asked to persist them.

- Do **not** write the project roadmap into cross-session memory “so you won’t forget.” Users often only want you not to lose the plan **inside this session**.
- Do **not** let the newest sampling mismatch (missing PE, 涨跌幅, 价格日, a review nit) replace the agreed product step.
- If you catch yourself promoting a note, stop and return to the agreed step. One-sentence correction is enough.

## After the user points out a wrong next step

Acknowledge the mix-up in one short sentence and continue the agreed work. Do **not**:

- explain the memory system
- rewrite user/profile memory unless they asked
- narrate “what I was thinking” at length
- open a new planning round

If they ask “你在思考个啥”, they want a brief admission of the error, not a process essay.

## Audit vs product step

| Keep as a note | Do not treat as next work |
|---|---|
| Missing fields on a card | Adding those fields when the plan was a decision surface |
| Review nits | Replacing the next product milestone |
| Dual pipelines still in the repo | “Cleaning up everything” unless that was the agreed step |

When reporting an audit, label leftovers as “抽查备注，不是下一步”.

## Dual-track codebases

If a repo still has legacy and current flows, say which path is **official** vs **demo/legacy** when the user asks. Do not imply the others were deleted. Session notes for this class of AH research app: `references/ah-analyse-official-path.md`.

**整理 ≠ 合并.** Relabeling demo, moving tabs, or defaulting the UI to the new card is anti-misuse, not retirement. If the user asks 「整理到底干了什么」, answer with two columns: what changed vs what still runs. Never paraphrase that as 「路线已收成一条」.

## Literal-true answers that hide the live path

If asked whether entry X does Y (e.g. 「run_daily_job 推飞书吗」), a bare “no” is wrong when another entry does Y. Same breath: X does not; **this** command/task does. Search webhooks/`--push` before claiming there is no delivery path.

## Scoped official path

If the user says 「后续只聊」 one route (here: Feishu `stock_recommend --push`), stay on that route until they reopen. Do not re-explain dual pipelines, multi-factor, ML, or legacy daily reports unless they ask.
