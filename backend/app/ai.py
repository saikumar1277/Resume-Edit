"""
The resume assistant: blocks + chat history -> a reply plus concrete edits.

Concept: the model never sees our JSON. It sees one line per block, tagged
with that block's id ("[b12] - Built Sam Bot ..."), and it answers with
edits that point back at those ids. The ids are the shared vocabulary
between the model and the editor, which is what lets the UI apply a
suggestion to exactly one paragraph instead of regenerating the document.

We ask for a typed response (see ChatReply) rather than parsing prose, so a
malformed suggestion is a parse error here instead of a broken edit in the
browser. Nothing in this file writes to storage - suggestions only become
real once the user accepts them in the editor.
"""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_MODEL = "gpt-4o-mini"
MAX_EDITS = 12


class AiError(RuntimeError):
    """Anything the user can act on: missing key, refused request, bad reply."""


class ResumeEdit(BaseModel):
    op: Literal["replace", "insert_after"]
    block_id: str
    text: str


class ChatReply(BaseModel):
    reply: str
    edits: list[ResumeEdit]


SYSTEM_PROMPT = """\
You are a resume editor built into a resume editing app. You help the user
improve their resume: rewriting bullets, tightening wording, grouping skills,
and tailoring existing lines to a job description they paste in the chat.

The resume is given to you as one line per block, like
"[b12] - Built Sam Bot, an AI-powered ...". The bracketed id is how you refer
to a line you want to change. Bold text is marked with **.

Writing rules:
1. Never invent a metric, tool, technology, employer, date, or outcome that
   is not already in the resume or given by the user. If a bullet needs a
   number the input does not have, put the literal placeholder
   "[QUANTIFY: <suggested metric type>]" in that edit's text. Do not invent
   a number, and do not only mention the missing number in `reply`.
2. If the user pastes a job description or names a target role, reuse that
   wording when it truthfully describes their real experience (e.g. use
   "CI/CD pipelines" not "automation" if the resume supports it).
3. Rewrite experience bullets as: Action Verb + Task + Tool/Method +
   Quantified Result. Strong past-tense verbs (Built, Shipped, Cut,
   Automated). Never "Responsible for" or "Helped with". No first person,
   no filler adjectives, no stacking buzzwords. One line where possible,
   two at most.
4. When the user asks about skills, regroup the existing skills line(s)
   into categories (Languages, Frameworks, Cloud/Infra, Methodologies).
   Put job-description matches first in each category. Do not invent
   skills. If the resume has no skills lines, do not create a skills
   section.
5. When asked to tailor or reorder projects, keep or drop existing project
   lines by relevance to the job description. Quantify only when the
   resume already supports it. If there are no project lines, do not
   create a projects section.
6. Edit text must be ATS-safe plain text: no tables, columns, icons,
   emojis, or decorative symbols. Allowed exceptions: the original bullet
   character so a new line matches its section; ** only where the source
   line already had bold (a job title or "Languages:" label); and the
   literal "[QUANTIFY: ...]" / "[VERIFY: ...]" placeholders.
7. If input is ambiguous, inconsistent, or contradictory, insert
   "[VERIFY: <what needs checking>]" in the edit, or mention it in `reply`
   if no edit applies. Do not guess or silently resolve it.
8. Only change lines the user asked about. Do not add sections, headers,
   or content that were not requested. Leave section headers (SUMMARY,
   EXPERIENCE, ...) and divider lines (---) alone. If the resume has no
   experience / skills / projects lines, do not create those sections.

Reply behavior:
- `reply` is a short conversational message, 2-4 sentences, no markdown
  headings or bullet lists.
- If the user did not paste a job description, still apply general ATS
  practices to the lines they asked about, and include this sentence in
  `reply`: "No job description provided — optimized without keyword
  targeting."
- If the user did paste a job description, mention in `reply` which of
  those terms the resume already supports and which are still missing.
  Do not invent coverage for terms the resume does not support.
- If the resume text is empty, return no edits and one explanatory
  `reply`.
- If the user only asked a question, return an empty edits list and
  answer in `reply`.

`edits` are the concrete changes: op "replace" rewrites an existing line,
op "insert_after" adds a new line below an existing one. When adding a
line, open it with the same bullet character the neighbouring lines use.
Propose at most 12 edits per turn, and make the smallest change that
does the job.
"""


def _bold_marked(runs: list[dict]) -> str:
    """Render runs as text, wrapping bold stretches in ** - the same
    notation the model is asked to use when it writes a line back."""
    parts: list[tuple[bool, str]] = []
    for run in runs:
        text = run.get("text", "")
        if not text:
            continue
        bold = bool(run.get("bold")) and bool(text.strip())
        if parts and bold == parts[-1][0]:
            parts[-1] = (bold, parts[-1][1] + text)
        else:
            parts.append((bold, text))
    out = []
    for bold, text in parts:
        if not bold:
            out.append(text)
            continue
        # Keep padding outside the markers: "**Languages:** JS", not "**Languages: **JS".
        core = text.strip()
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()) :]
        out.append(f"{lead}**{core}**{trail}")
    return "".join(out)


def render_blocks(blocks: list[dict]) -> str:
    lines = []
    for block in blocks:
        block_id = block.get("id") or "?"
        if block.get("type") == "divider":
            lines.append(f"[{block_id}] ---")
            continue
        lines.append(f"[{block_id}] {_bold_marked(block.get('runs') or [])}".rstrip())
    return "\n".join(lines)


def chat(blocks: list[dict], messages: list[dict]) -> ChatReply:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AiError(
            "No OpenAI key found. Add OPENAI_API_KEY to backend/.env and restart the API."
        )

    client = OpenAI(api_key=api_key)
    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT},
        # Re-sent every turn: the user keeps editing, so last turn's copy is stale.
        {"role": "system", "content": f"Current resume:\n\n{render_blocks(blocks)}"},
        *[{"role": m["role"], "content": m["content"]} for m in messages],
    ]

    try:
        completion = client.chat.completions.parse(
            model=os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL,
            messages=conversation,
            response_format=ChatReply,
        )
    except OpenAIError as exc:
        raise AiError(f"The assistant could not be reached: {exc}") from exc

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise AiError("The assistant returned an unreadable reply. Try again.")

    # An edit pointing at a block we don't have is unappliable, so drop it
    # here rather than showing the user a card that silently does nothing.
    known_ids = {block.get("id") for block in blocks}
    parsed.edits = [
        edit for edit in parsed.edits if edit.block_id in known_ids
    ][:MAX_EDITS]
    return parsed
