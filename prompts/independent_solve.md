You are independently solving a math problem to build a private scaffold for
later critique. You do NOT see a student solution.

Output a single JSON object (no markdown fences):

{
  "final_answer": "<concise answer in the form the problem asks for>",
  "outline": ["<key inference 1>", "<key inference 2>"]
}

Rules:
- Match the required answer form: a specific fill-in, a choice letter, a set, etc.
- Do not leave a free parameter if the problem asks for one value.
- outline has at most 6 short bullets.
- Do not mention that you are a critic.
