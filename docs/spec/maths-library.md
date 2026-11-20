# The maths library

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the maths library: what it reads, how it compares, and how it checks pictures. The models and the prompt are in [`ai-layer.md`](ai-layer.md).

## The maths library

The library is SymPy. Where it runs in a check is in [`mastery-check.md`](mastery-check.md).

- **What it reads:** only LaTeX, with the Lark backend. `parse_expr` and `sympify` never run on outside text ([#716]).
- **What goes to it:** expression and number answers, quantities with units, a file's maths step, and a graph's function. Equations, sets, intervals and worded answers go to the AI's independent working ([#716], [#751]).
- **Units:** SymPy's own units module checks quantities with units ("15 m/s") wherever the library reads: model answers, learners' final answers, file mistakes and graphs' axes ([#751]).
- **How it compares:** by simplifying and a numeric spot-check. Each comparison runs in a separate process, killed after a few seconds ([#716]).

| Result | When |
|---|---|
| Match | The difference simplifies to 0, or is near 0 at several random points |
| No match | Any valid point clearly differs |
| Can't tell | A point cannot be evaluated, the time runs out, or the answer is not an expression or number |

- **Model answers:** a match is saved. No match throws the problem away unseen, and a new one is written and checked. "Can't tell" goes to the AI's independent working ([#679]).
- **Final answers:** it also compares the learner's final answer with the model answer. A disagreement with the marker brings a fresh re-mark, told whether the final values match, before the learner sees a result ([#679]).
- The library never marks alone, and the working is still judged ([#679]).
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
