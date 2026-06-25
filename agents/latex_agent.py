from core.llm import get_llm


llm = None


LATEX_TEMPLATE = r"""
\documentclass{article}

\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{hyperref}

\begin{document}

<<CONTENT>>

\end{document}
"""


def _get_latex_llm():
    global llm
    if llm is None:
        llm = get_llm()
    return llm


def _extract_document_body(latex: str) -> str:
    begin_marker = r"\begin{document}"
    end_marker = r"\end{document}"

    if begin_marker in latex:
        latex = latex.split(begin_marker, 1)[1]

    if end_marker in latex:
        latex = latex.split(end_marker, 1)[0]

    return latex.strip()


def latex_agent(state):

    notes = state["synthesized_section"]

    if state.get("generation_blocked"):
        state["latex_output"] = LATEX_TEMPLATE.replace("<<CONTENT>>", notes.strip())
        return state

    prompt = f"""
Convert the following notes into clean LaTeX body content.

Requirements:
- proper sections
- equations in math mode
- bullet formatting
- theorem formatting
- avoid invalid latex syntax
- return only content that belongs inside \\begin{{document}} and \\end{{document}}
- do not include \\documentclass, package imports, \\begin{{document}}, or \\end{{document}}

NOTES:
{notes}
"""
    response = _get_latex_llm().invoke(prompt)

    latex_body = _extract_document_body(response.content)
    latex_doc = LATEX_TEMPLATE.replace("<<CONTENT>>", latex_body)

    state["latex_output"] = latex_doc

    return state
