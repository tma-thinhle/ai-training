# 01: Models, Training, and Generating an Answer

Purpose: understand the part an AI model plays in our issue classifier before connecting it to Python.

## 1. What is a model?

An AI model is a program whose behavior depends on learned numbers called **weights**, or **parameters**. A **large language model (LLM)** learns patterns useful for processing and generating language. OpenAI describes model development as including data preparation, pre-training, post-training, and evaluation. [OpenAI: how models are developed](https://help.openai.com/en/articles/7842364-how-chatgpt-and-our-foundation-models-are-developed)

For our application, OpenAI provides the trained model. We write the Python program that uses it.

## 2. How does training produce those weights?

First, text is split into **tokens**: units that can represent words, word fragments, or punctuation. The model processes numeric representations of these units.

A simplified language-training loop is:

1. Provide part of a text sequence.
2. Have the model predict the next token.
3. Compare the prediction with the token actually present in the training text.
4. Adjust weights to reduce prediction error across many examples.

A **transformer** is a model architecture that uses **attention** to make a token's representation depend on surrounding context. We only need that broad idea now; the matrix calculations can wait. [Microsoft: large language models](https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/3-language-models)

For example, context helps distinguish a computer mouse from an animal. This is a teaching example, not a description of any particular model's training data.

**Post-training** further shapes behavior after the initial language-learning stage, including how usefully a model follows instructions. Our Week 1 work uses an already trained model; we change its input instructions. [OpenAI: model-development stages](https://help.openai.com/en/articles/7842364-how-chatgpt-and-our-foundation-models-are-developed)

## 3. What happens when we send an issue?

**Inference** means using a trained model to produce an output. Given the supplied context, a language model predicts a next token, adds it to the sequence, and continues. This is a simplified account of generation. [Microsoft: predicting completions](https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/3-language-models#predicting-completions-from-prompts)

Our planned flow is:

```text
Instructions + issue text
          |
          v
Python sends an HTTP request to OpenAI
          |
          v
Model generates a response
          |
          v
Python checks the response and saves the result
```

Your web-development experience applies directly: authentication, request payloads, responses, and error handling still matter.

## 4. Why can the same question get different answers?

There can be several plausible continuations. Generation can involve randomness in selecting among them, so repeated requests can differ. Producing a second answer does not itself show that the model was retrained between requests. [OpenAI: generation and variability](https://help.openai.com/en/articles/7842364-how-chatgpt-and-our-foundation-models-are-developed)

OpenAI documents text generation as **non-deterministic**: identical inputs do not guarantee identical outputs. That is one reason we compare results under recorded, consistent settings. [OpenAI: text generation](https://developers.openai.com/api/docs/guides/text#prompt-engineering)

In our lab, wording differences in next actions might be harmless. Changing an issue's category or missing an urgent incident could matter. We must measure those separately.

## 5. What does a prompt change?

A **prompt** is the input supplied to guide a model's response. It can contain instructions, context, examples, and a requested format. Clearer category definitions give the model more specific guidance about our task. [Microsoft: prompts](https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/6-writing-prompts)

We will keep the reusable classification instructions separate from the individual issue. The course calls for system/user roles; when implementing, we will explain the exact OpenAI message roles we use. Current API documentation also describes developer messages for application instructions. [OpenAI: message roles](https://developers.openai.com/api/docs/guides/text#message-roles-and-instruction-following)

Prompt V1, V2, and V3 will therefore be different inputs to the same selected model. Their effects must be observed through evaluation.

## 6. One concrete example

**Illustration only: this example and response are written for teaching, not returned by an API or scored as evaluation evidence.**

Issue:

> Please add a keyboard shortcut for opening the help panel.

An intended response could be:

```json
{
  "category": "Feature",
  "priority": "P3",
  "next_actions": [
    "Confirm the shortcut and check for keyboard conflicts."
  ]
}
```

Our proposed interpretation: it requests a new capability, with no stated urgent operational impact. P3 is provisional until we document our priority policy; it is not an authoritative course label for this example.

| Responsibility | What it does here |
| --- | --- |
| Prompt | Describes labels, priority rules, and expected fields. |
| Model | Interprets the request and proposes the classification and action. |
| Python | Sends the request, validates the output, handles failures, and saves evidence. |
| Evaluation | Compares predictions with independent human reference labels. |

A **schema** specifies allowed fields, types, and values. Schema validation could reject `"priority": "urgent"` because our allowed values are P1/P2/P3. It could still accept a wrongly chosen P1. Structure checks and correctness checks answer different questions.

## Next increment

Establish the project Python environment and pass the supplied starter checks. Then implement one real request and walk through its actual response. No model call was needed for this lesson.
