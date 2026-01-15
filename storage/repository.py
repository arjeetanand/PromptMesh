from storage.db import get_conn

from storage.db import get_conn

def save_prompt(task, version, prompt_text):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO prompts (task, version, prompt_text) VALUES (?, ?, ?)",
        (task, version, prompt_text)
    )

    conn.commit()
    prompt_id = cur.lastrowid
    conn.close()

    return prompt_id



def save_run(prompt_id, iteration, failure_type):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO runs (prompt_id, iteration, failure_type) VALUES (?, ?, ?)",
        (prompt_id, iteration, failure_type)
    )
    conn.commit()
    return cur.lastrowid


# def save_evaluation(run_id, model, eval_result, latency_ms, output):
#     conn = get_conn()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         INSERT INTO evaluations
#         (run_id, model, score, accuracy, completeness, adherence, hallucination, latency_ms, output)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """,
#         (
#             run_id,
#             model,
#             eval_result.score,
#             eval_result.breakdown["accuracy"],
#             eval_result.breakdown["completeness"],
#             eval_result.breakdown["adherence"],
#             eval_result.breakdown["hallucination"],
#             latency_ms,
#             output
#         )
#     )
#     conn.commit()

def save_evaluation(run_id, model, eval_result, latency_ms, output):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO evaluations
        (run_id, model, score, accuracy, completeness, adherence, hallucination, latency_ms, output)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            model,
            eval_result.score,
            eval_result.breakdown.get("accuracy", None),
            eval_result.breakdown.get("completeness", None),
            eval_result.breakdown.get("adherence", None),
            eval_result.breakdown.get("hallucination", None),
            latency_ms,
            output
        )
    )
    conn.commit()
