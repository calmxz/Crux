# The maths library

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the maths library: what it reads, how it compares, how it checks practice answers, and how it checks pictures. The models and the prompt are in [`ai-layer.md`](ai-layer.md).

## The maths library

The library is SymPy. Where it runs in a check is in [`mastery-check.md`](mastery-check.md). In teaching, it checks practice answers (below).

- **What it reads:** only LaTeX, with the Lark backend. `parse_expr` and `sympify` never run on outside text ([#716]).
- **What goes to it:** expression and number answers, quantities with units, a file's maths step, a graph's function, and a practice answer's equation. In a check, equations, sets, intervals and worded answers are left to the independent check ([#716], [#751], [#802]).
- **Units:** SymPy's own units module checks quantities with units ("15 m/s") wherever the library reads: model answers, learners' final answers, file mistakes and graphs' axes ([#751]).
- **How it compares:** by simplifying and a numeric spot-check. Each comparison runs in a separate process, killed after a few seconds ([#716]).

| Result | When |
|---|---|
| Match | The difference simplifies to 0, or is near 0 at several random points |
| No match | Any valid point clearly differs |
| Can't tell | A point cannot be evaluated, the time runs out, or the answer is not an expression or number |

- **Model answers:** a match is saved, and the independent check still reads the worked solution (see [`mastery-check.md`](mastery-check.md)). No match throws the problem away unseen, and a new one is written and checked. "Can't tell" leaves it to the independent check ([#679], [#802]).
- **Final answers:** it also compares the learner's final answer with the model answer. A disagreement with the marker brings a fresh re-mark, told whether the final values match, before the learner sees a result ([#679]).
- The library never marks alone, and the working is still judged ([#679]).
- **Practice answers:** a report of right, fixed slip or bare right on a maths problem in teaching also carries the problem and the learner's final answer in LaTeX, plus the tutor's own answer for an expression ([#802]).
  - For an equation, the library solves it where it can and compares the learner's full answer with the full solution set, so an incomplete answer is no match. Where it can't solve, it substitutes the answer back.
  - On no match, Crux discards the report and says so in its reply to the tool call, and the tutor treats the answer as a slip before saying "right".
  - For an expression, a mismatch with the tutor's own answer goes to the tutor as "these differ, recheck both". It is a slip only if the recheck confirms the tutor's answer.
  - "Can't tell" and non-maths answers leave the report standing.
  - The check runs before the reply, with the library's usual time limit. The 5-second clock for "The tutor is busy right now" doesn't count its time. While it runs, the screen shows "The tutor is writing...".
- **Pictures:** a diagram's Mermaid text must parse before it is drawn. A graph's function is read like an answer, and the library works out the points and any tangent's slope. If either fails, nothing is drawn, and the tutor explains in words. Crux stores the description, not an image ([#751]).
- **Diagrams:** the parse check allows only the three type words in [`teaching.md`](teaching.md), so any other type fails like any picture. It refuses settings, styles, classes, colours, images and icons in the Mermaid text, so the contrast test holds and no diagram loads anything from outside ([#769]).
- **Diagram build notes,** checked while deciding ([#769]):
  - The refused grammar includes frontmatter `config:`, `%%{init}%%`, `style`, `classDef`, `class`, `:::`, `linkStyle`, sequence `rect` and `box` colours, and flowchart `img` and `icon` shapes.
  - The frontend runs Mermaid with `securityLevel: 'strict'`, and with `theme`, `themeVariables`, `themeCSS` and `fontFamily` added to its `secure` list.
- **File mistakes:** the library does the file's step itself and compares it with the file's result. Match: no flag. No match: the flag goes ahead. Can't tell: the tutor judges alone (see [`files.md`](files.md)) ([#751]).

[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#751]: https://github.com/calmxz/Crux/issues/751
[#769]: https://github.com/calmxz/Crux/issues/769
[#802]: https://github.com/calmxz/Crux/issues/802
