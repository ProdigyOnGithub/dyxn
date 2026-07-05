from core.llm import get_llm


llm = get_llm()


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

def latex_agent(state):

    notes = state["synthesized_section"]

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
    response = llm.invoke(prompt)

    latex_doc = LATEX_TEMPLATE.format(content=response.content)

    state["latex_output"] = latex_doc

    return state