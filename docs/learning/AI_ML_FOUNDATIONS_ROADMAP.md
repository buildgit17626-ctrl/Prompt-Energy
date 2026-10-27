# Learn the foundations through small implementations

Your experiment teaches measurement, evaluation, paired comparisons and research
honesty. It does not teach how weights are learned by itself. Finish its review
and then study training explicitly. You do not need to learn every current tool
before approaching a professor, and an internship cannot be guaranteed by a paper.

Use this as a competency sequence, not a promise to master AI in a few weeks.
At roughly 10-15 focused hours per week, an initial pass might take 10-14 weeks;
allow longer wherever the checkpoints expose a gap. Keep new learning projects
in a separate environment so the experiment's pinned stack remains intact.

| Phase | Foundations | Concrete checkpoint |
| --- | --- | --- |
| 1. Close this study | Estimand, pairing, uncertainty, bias, association versus mechanism | Explain the P1-P0 forest plot and why its accuracy interval does not prove equivalence. Independently verify five failure annotations. |
| 2. Numerical and mathematical basics | Array shapes, broadcasting, matrix products, derivatives, chain rule, probability, expectation and variance | Implement linear regression with NumPy; derive its squared-error gradient and check it by finite differences. |
| 3. Statistical learning | Train/validation/test splits, logistic regression, cross-entropy, regularization, leakage, overfitting, resampling | Build a small classifier and explain why test-set tuning invalidates its reported performance. Implement a task bootstrap without copying the study helper. |
| 4. Neural networks | Forward pass, activations, backpropagation, gradient descent, minibatches, optimization versus generalization | Implement a two-layer network in NumPy, then reproduce it in PyTorch and compare gradients and learning curves. |
| 5. Language models | Tokenization, embeddings, softmax, next-token loss, causal attention, positional information, generation | Build a tiny character model, then a small decoder; trace tensor shapes and explain training targets versus inference sampling. |
| 6. Systems and research | Profiling, memory hierarchy, model weights versus KV cache, prefill/decode, quantization, throughput versus latency | Profile a tiny model and identify its measured bottleneck. Propose one controlled follow-up with quality, latency and energy metrics before collecting data. |

Begin phases 2-3 with [An Introduction to Statistical Learning with Python](https://www.statlearning.com/).
It supplies regression, classification and resampling chapters with Python labs.
Use the [official PyTorch basics](https://docs.pytorch.org/tutorials/beginner/basics/)
for tensors, automatic differentiation and training loops after implementing a
small gradient calculation yourself. Later, use
[Stanford CS336: Language Modeling from Scratch](https://cs336.stanford.edu/)
selectively: it explicitly expects Python, ML, calculus/linear algebra, probability,
deep learning and systems knowledge. It is an advanced destination, not a shortcut
around those prerequisites. Its distributed/GPU assignments need resources beyond
your laptop; tiny educational implementations can be scaled down first.

For each topic, spend roughly one session deriving or explaining it, one coding
it, and one testing your understanding. A useful checkpoint is whether you can
implement the core idea without an AI-generated solution, then use assistance
to review a specific bug or explanation. Keep a one-page note of what failed,
what you measured and what evidence changed your mind. Avoid collecting courses
instead of completing exercises, and avoid buying hardware before identifying a
specific workload that needs it.

For professor outreach, prepare a short account of the question, your own work,
the strongest bounded finding, the largest limitation, and one proposed next
experiment. Be candid about AI assistance and missing measurements. Match the
proposed question to the professor's actual research after reading their work.
Specific technical questions and evidence you can explain are more credible than
claims to have mastered all of AI or solved sustainable inference.

## Five questions before the next project

1. What is the difference between the gradient used to train a model and the
   next-token selection used when it generates an answer?
2. Why can more output tokens mean more request energy without a different
   internal reasoning algorithm?
3. Why are model weights, conversation context and prefix-cache entries different?
4. What evidence would distinguish a real efficiency gain from lower quality,
   measurement drift or a change in workload?
5. Which single variable would you change next, and what would remain controlled?
