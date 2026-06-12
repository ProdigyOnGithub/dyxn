from langchain.chat_models import init_chat_model


llm = init_chat_model(
    model="gpt-4.1-mini",
    model_provider="openai"
)


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