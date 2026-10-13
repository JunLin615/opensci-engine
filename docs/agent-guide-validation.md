# Agent-guide validation

Evidence for [issue #3](https://github.com/JunLin615/opensci-engine/issues/3),
following standing rules [#1](https://github.com/JunLin615/opensci-engine/issues/1)
and [#2](https://github.com/JunLin615/opensci-engine/issues/2).

## Entry size

On 2026-10-13, the complete UTF-8 Markdown of `AGENT_GUIDE.md` contained **1,289
tokens** and **5,755 bytes**. The optional `docs/agent-recipes.md` contained 1,098
tokens and 4,728 bytes. Counts use `tiktoken==0.14.0`, `o200k_base`, including
headings, links, code and table markup. This is a reproducible document-size
measure, not a claim about a particular agent's billed or internal tokens.

To measure a revision from the repository root (the tokenizer is a maintainer
measurement tool, not an example dependency):

```bash
python -m pip install "tiktoken==0.14.0"
python -c "from pathlib import Path; import tiktoken; p=Path('AGENT_GUIDE.md'); print(len(tiktoken.get_encoding('o200k_base').encode(p.read_text(encoding='utf-8'))))"
```

The measured document SHA-256 values were:

| File | SHA-256 |
| --- | --- |
| `AGENT_GUIDE.md` | `10216381aa5065575ed63af9dbd677527e24a369926743effab690a9431efebb` |
| `docs/agent-recipes.md` | `54c7844d23666812053ae30ce8322fd4f22884ebe6d0f4f5b6eeb480fc7ab7bc` |

## Command and recipe checks

Environment: Windows, Python 3.13.5, published PyPI `opensci-engine==0.6.1`
(build `0.6.1+e5785dea69453e1e`), catalog `2026-10-06.3`. The package was installed
in a virtual environment; no private source-tree imports were used. The baseline
remains consistent with both READMEs and the [results validation](result-summary-validation.md).

| Check | Observed result |
| --- | --- |
| Version discovery, `doctor`, engine `--help` | Exit 0; installed version 0.6.1 |
| Catalog list filtered to lenses at 780 nm, limit 5 | Exit 0 |
| Default ideal-lens run | `PASS`, exit 0 |
| Ideal maximum radius 0.02 mm | `PASS`, exit 0 |
| Ideal maximum radius 0.001 mm | `FAIL`, exit 1 |
| Catalog beam-expander baseline | `PASS`, exit 0 |
| Native saved summary, with and without `--details` | Parseable JSON with full artifact references |
| Complete editing recipe from the Markdown | `FAIL`, exit 1; waist radius 1.1148985411200965 mm outside 1.8–2.2 mm |
| Reading that revised run through the summary script | Same result, exit 1 |
| Recipe variant with radius interval 0–0.001 mm | `FAIL`, exit 1 |

The complete recipe's Python block was extracted and executed as written. The
strict variant changed only its interval and output directory. SHA-256 checks
confirmed the original native run files were unchanged. Failure here means the
computed design missed its target; it does not mean the recipe failed to execute.

Both READMEs link to the same English entry. Local Markdown links were checked,
and the three issue-template YAML files parsed successfully. English template
defaults retain links to both human documentation languages and permit feedback
in the reporter's preferred language.

## Representative task trial

The trial used a fresh agent without the implementation conversation. It received
the repository path, the already prepared Python environment, and a customer
task: create a beam-expander baseline, change the wavelength to 785 nm, shift L2
and the output plane by +1 mm in design X, set the waist-radius interval to
1.0–1.2 mm, and assess the result. It was directed to start with the agent guide
and read only relevant linked content, without changing tracked files.

The task completed successfully: the adapted waist radius was
**1.1148985411200965 mm**, `PASS` against **1.0–1.2 mm**. Saved inputs confirmed
785 nm, L2 X changing from 152.841 to 153.841 mm, and observation X changing from
252.841 to 253.841 mm. Both runs had `PASS` overall/engine/validation status,
empty issue/model-scope lists, and consistent verified artifacts. A separate
saved-summary invocation reproduced the adapted result. No blocking ambiguity
was reported.

Full files read into the trial agent's context:

| File | UTF-8 bytes |
| --- | ---: |
| `AGENT_GUIDE.md` | 5,755 |
| `docs/agent-recipes.md` | 4,728 |
| `run-agent-trial-baseline/project.json` | 3,353 |
| `run-agent-trial-adapted/project.json` | 3,326 |
| Total | 17,162 |

Documentation reading totaled **10,483 bytes / 2,387 tokens** by the tokenizer
method above; generated input artifacts accounted for another 6,679 bytes. No
implementation source or other validation report was read. Runtime imports are
excluded from model-visible reading volume; these are not total conversation
token counts.

The agent recorded **6 orchestration tool calls**, containing **7 shell-tool
calls and 1 file-edit call**. The seven shell invocations launched four Python
processes: version discovery, baseline simulation, adapted simulation, and saved
summary inspection. Other shell work read the four files with byte counts. There
were **2 simulation attempts, 0 retries**, and all shell/Python invocations exited
0. No separate measurement-accounting commands were needed; byte counts were
collected with the task's file reads.

The generated recipe applied the documented edits with the task's requested
interval and separate output paths. Local evidence was retained in
`run-agent-trial-baseline/`, `run-agent-trial-adapted/`, and the baseline arrivals
CSV. These generated artifacts are not committed; reproduce the task from the
linked recipe and substitutions above.

The trial tests routing and recipe use in a prepared environment. It is a
document-assisted task variant, not an independent benchmark or a comparison
against the old documentation. Installation effort is outside its measured task
window. No token-saving percentage or general performance claim is inferred.
