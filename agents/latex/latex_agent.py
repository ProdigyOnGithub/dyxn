from typing import Any, Dict

from agents.base_agent import BaseAgent

LATEX_TEMPLATE = r"""
\documentclass{article}

\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{hyperref}

\begin{document}

{content}

\end{document}
"""


class LatexAgent(BaseAgent):
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        notes = state.get("synthesized_section", "")
        prompt = f"""
Convert the following notes into clean LaTeX.

Requirements:
- proper sections
- equations in math mode
- bullet formatting
- theorem formatting
- avoid invalid latex syntax

NOTES:
{notes}
"""
        latex_body = self.llm.invoke(prompt).content
        state["latex_output"] = LATEX_TEMPLATE.format(content=latex_body)
        return state
