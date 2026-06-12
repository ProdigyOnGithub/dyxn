from graph import graph


initial_state = {
    "syllabus_topic": "Fourier Transform",
    "retrieved_chunks": [],
    "retrieved_metadata": [],
    "working_notes": "",
    "synthesized_section": "",
    "latex_output": "",
    "evaluation_score": 0.0
}


result = graph.invoke(initial_state)


with open("output/notes.tex", "w", encoding="utf-8") as f:
    f.write(result["latex_output"])


print("LaTeX notes generated.")
print(result["evaluation_score"])