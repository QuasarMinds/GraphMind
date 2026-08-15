# GraphMind
Final Year Project


# GraphMind: Detailed Architecture and Implementation Plan

Absolutely. Since the project is already finalized, let's stop discussing whether GraphMind is a good idea and turn it into an actual implementation plan.

I'll divide this into exactly the two parts you asked for.

---

## PART 1 — VERY SHORT: WHAT EXACTLY ARE WE BUILDING?

### 1. What are we building?
We are building a CLI-based middleware/tool for AI coding agents.

**Its job is:**
Given a developer's coding request and a repository, find the smallest useful set of code that an AI model needs to solve the task.

Instead of giving the AI a huge amount of repository code, GraphMind tries to select the relevant code intelligently.

### 2. The final system
The final system will roughly look like:

```text
                    GRAPHMIND

Developer
   │
   │ "Fix expired token bug"
   ↓
┌──────────────────────────┐
│      Task Analyzer       │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│    Hybrid Retrieval      │
│                          │
│ Keyword + Semantic       │
│ + Symbol/AST Search      │
└────────────┬─────────────┘
             ↓
      Candidate Code
             │
             ↓
┌──────────────────────────┐
│   Code Knowledge Graph   │
│                          │
│ files/functions/classes  │
│ calls/imports/depends... │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│ Graph Ranking / Search   │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│   Context Optimizer      │
│                          │
│ Token budget + relevance │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│     Model Selector       │
└────────────┬─────────────┘
             ↓
          LLM/API
             ↓
       Answer / Patch

```

### 3. There are actually TWO systems inside GraphMind

This is extremely important.

**System A — Repository Understanding**
This happens mostly before the user asks anything.

```text
Repository
    ↓
Tree-sitter
    ↓
AST
    ↓
Entity Extraction
    ↓
Relationship Extraction
    ↓
Code Knowledge Graph
    ↓
Index / Storage

```

This creates your understanding of the repository.

**System B — Query Processing**
This happens when the developer asks something.

```text
User Query
    ↓
Task Analysis
    ↓
Keyword/Semantic/Symbol Retrieval
    ↓
Graph Mapping
    ↓
Graph Ranking
    ↓
Context Selection
    ↓
LLM

```

### 4. Implementation order

Don't build everything simultaneously. Build in this order:

1. Repository Scanner
2. Tree-sitter Parser
3. AST Extraction
4. Code Entity Extraction
5. Relationship Extraction
6. Code Knowledge Graph
7. Graph Storage
8. Keyword Retrieval
9. Semantic Retrieval
10. Hybrid Retrieval
11. Graph-based Ranking
12. Context Optimization
13. LLM Integration
14. Model Selection
15. CLI
16. Evaluation / Benchmark

### 5. Prerequisites

Before serious development, your team should understand:

* **Programming:** Python, Git/GitHub, CLI development, JSON, REST APIs
* **Code analysis:** Parsing, AST, Tree-sitter, Symbol extraction, Static code analysis
* **AI/RAG:** Embeddings, Vector similarity, Semantic search, RAG, LLM APIs, Tokenization
* **Graphs:** Graph, Node, Edge, Directed graph, Weighted graph, BFS, DFS, Best-first search, Graph traversal, Graph ranking
* **Software engineering:** Repository indexing, Caching, Persistence, Logging, Testing, Benchmarking

You do not need to master all of these before starting. Learn each concept when you reach that module.

---

## PART 2 — DETAILED EXPLANATION

Now let's go through the whole thing from zero to final GraphMind.

### 1. First understand the actual problem

Imagine this repository:

```text
my_project/
src/
├── main.cpp
├── auth/
│   ├── login.cpp
│   ├── auth.cpp
│   ├── token.cpp
│   └── session.cpp
│
├── database/
│   ├── database.cpp
│   └── user.cpp
│
├── payment/
│   ├── payment.cpp
│   └── invoice.cpp
│
└── ui/
    ├── dashboard.cpp
    └── profile.cpp

```

Suppose there are 500 files, 20,000 functions, and 200,000 lines.
Developer asks: *"Fix the bug where expired authentication tokens still allow access."*

The AI doesn't need all 200,000 lines. It probably needs something like:
`login.cpp`, `auth.cpp`, `token.cpp`, `session.cpp`.

**The difficult question is:** How does the system determine that these files are important and that 90% of the repository is unnecessary? That's GraphMind's problem.

### 2. Existing AI retrieval

Before GraphMind, an AI coding agent can use several techniques:

```text
User Query
    ↓
Search
    ├── keyword
    ├── semantic
    ├── symbol
    ├── AST
    ├── repository index
    └── tool calls

```

We are not replacing these techniques. We are building an additional layer that tries to combine them intelligently.

### 3. What is keyword retrieval?

Suppose: *"expired token authentication"*
Search for: `expired`, `token`, `authentication`.

It may find: `token.cpp`, `auth.cpp`, `login.cpp`.
Very simple.

* **Advantages:** fast, easy, predictable
* **Disadvantages:** It can miss semantic relationships. For example, `checkSessionValidity()` might be relevant even though it doesn't contain the word `token`.

### 4. What is semantic retrieval?

We use an embedding model. An embedding converts text/code into a vector.

Conceptually:
`"expired authentication token"` → `[0.12, 0.81, -0.23, ...]`

Another piece of code:
`"check whether JWT is still valid"` gets another vector.

If their vectors are close (similarity = high), we consider them semantically related. Usually, this is calculated using something like cosine similarity:

$$\text{similarity}(A,B) = \frac{A \cdot B}{\vert{}A\vert{}\vert{}B\vert{}}$$

You don't need to implement embeddings mathematically yourself. You'll use an embedding model/library.

### 5. Why do we need the graph?

Suppose semantic search finds: `validateToken()`
Excellent. But the AI might need to know:

* Who calls `validateToken()`?
* What calls that function?
* Where is `TokenManager`?
* What happens when validation fails?
* Which session code depends on it?

The graph can represent:

```text
login()
   │
   │ calls
   ↓
authenticate()
   │
   │ calls
   ↓
validateToken()
   │
   │ uses
   ↓
TokenManager

```

Now GraphMind can explore the relevant software neighborhood.

### 6. First real component: Repository Scanner

We need to scan the repository.
Example: `graphmind index ./myproject`

GraphMind discovers: `main.cpp`, `auth.cpp`, `token.cpp`, `database.cpp`...
It should ignore things such as: `.git/`, `node_modules/`, `build/`, `dist/`, `.venv/` depending on configuration.

The scanner produces something like:

```json
{
  "files": [
    "src/main.cpp",
    "src/auth.cpp",
    "src/token.cpp"
  ]
}

```

This is the first layer.

### 7. Second component: Tree-sitter

Now each source file goes through Tree-sitter.
`token.cpp` → Tree-sitter → Syntax Tree

For:

```cpp
bool validateToken(Token token) {
    return token.expiry > currentTime();
}

```

Tree-sitter gives us structured syntax information. We can identify:

* **Function:** `validateToken`
* **Parameter:** `token`
* **Function call:** `currentTime`
* **Return statement:** ...

### 8. What is parsing?

Parsing simply means: Convert source code into a structured representation according to the language grammar.

```text
Source Code
     ↓
Parser
     ↓
AST / Syntax Tree

```

You don't want GraphMind to understand source code by doing: `if "function" in line:`
That's unreliable. We want actual syntax-aware analysis.

### 9. Entity extraction

From the syntax tree, GraphMind extracts entities.

For example, File: `token.cpp`

* **Class:** `TokenManager`
* **Functions:** `validateToken()`, `refreshToken()`
* **Variables:** `expiry`, `token`

These become graph nodes.

### 10. Relationship extraction

This is harder and more important.

Suppose:

```cpp
bool login(User user) {
    return authenticate(user);
}

```

GraphMind should determine: `login()` → `calls` → `authenticate()`

Similarly: `#include "token.h"` can produce: `auth.cpp` → `imports` → `token.h`
Inheritance: `class Admin : public User` can produce: `Admin` → `inherits` → `User`

Now we have a graph.

### 11. Code Knowledge Graph

A simplified graph could look like:

```text
                 Repository
                     │
                     ↓
                   auth/
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
       login.cpp             token.cpp
          │                     │
          ↓ contains            ↓ contains
       login()             validateToken()
          │                     │
          │ calls               │ uses
          ↓                     ↓
   authenticate()          TokenManager

```

This graph is the heart of GraphMind.

### 12. What should be stored?

A node might contain: `node_id`, `type`, `name`, `file_path`, `start_line`, `end_line`, `language`.

Example:

```json
{
  "id": "func_123",
  "type": "function",
  "name": "validateToken",
  "file": "src/auth/token.cpp",
  "start_line": 42,
  "end_line": 58
}

```

Why store line numbers? Because later we don't necessarily want to send the entire file to the LLM. We might want: `token.cpp lines 42–58` instead. That can dramatically improve context efficiency.

### 13. Edges

An edge could look like:

```json
{
  "source": "func_100",
  "target": "func_123",
  "type": "calls"
}

```

Later we can give different relationship types different weights.

* `calls` → strong
* `inherits` → strong
* `imports` → medium
* `contains` → weaker

But these weights should eventually be experimentally tested.

### 14. Where do we store the graph?

For MVP: Python → NetworkX → Graph.
We can persist it using something simple initially: JSON, SQLite, or pickle.
Don't start with Neo4j unless you have a concrete reason.

### 15. Now the second half starts: Query processing

Graph exists. Now user asks:
`graphmind ask "Fix expired token authentication"`

The query goes into the Task Analyzer.

### 16. Task Analyzer

The task analyzer tries to identify: Task type, Target, Action, Important concepts, Potential scope.

For: *"Fix expired token authentication."*
We might derive:

* `task_type = bug_fix`
* `concepts = [authentication, token, expiration, validation]`
* `operation = modify`

This does not need to be extremely complicated initially.

### 17. Candidate retrieval

Now we run multiple retrieval systems.

```text
                    Query
                      ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
     Keyword       Semantic       Symbol
        ↓             ↓             ↓
        └─────────────┼─────────────┘
                      ↓
                Candidates

```

Suppose:

* Candidate 1: `validateToken()`
* Candidate 2: `TokenManager`
* Candidate 3: `authenticate()`
* Candidate 4: `login()`
* Candidate 5: `SessionManager`
* Candidate 6: `database.cpp`

### 18. Map candidates to graph

Now we locate these entities inside the graph.

For example, `validateToken()`:

* `called_by` → `authenticate()`
* `uses` → `TokenManager`
* `defined_in` → `token.cpp`

Now GraphMind knows the neighborhood around the candidate.

### 19. Graph expansion

We can perform controlled graph traversal.

* **Seed:** `validateToken()`
* **Depth 1:** `authenticate()`, `TokenManager`
* **Depth 2:** `login()`, `SessionManager`

But we don't blindly take everything. Each candidate receives a score.

### 20. Graph ranking

This is where we implement the research idea. Potential score:

$$\text{Score}(n) = \alpha \text{Semantic}(n) + \beta \text{Structural}(n) + \gamma \text{Task}(n) - \lambda \text{Cost}(n)$$

For example:

* `validateToken()`: 0.94
* `TokenManager`: 0.88
* `authenticate()`: 0.84
* `SessionManager`: 0.73
* `database.cpp`: 0.22

Then we select the highest-value nodes.

### 21. Why subtract cost?

Suppose:

* Function A: relevance = 0.90, size = 500 tokens
* Function B: relevance = 0.92, size = 20,000 tokens

Function B is slightly more relevant but extremely expensive. We may prefer A depending on the task. This is why context optimization is important.

### 22. Context Builder

Now we convert selected graph nodes back into actual source code.

Selected nodes: `validateToken()`, `authenticate()`, `TokenManager`, `SessionManager`.
GraphMind retrieves their source locations:

* `token.cpp:42-58`
* `auth.cpp:20-41`
* `token_manager.cpp:10-70`
* `session.cpp:31-45`

Then constructs:

```text
SYSTEM:
You are a coding assistant.

TASK:
Fix expired token authentication.

RELEVANT CODE:

--- token.cpp:42-58 ---
...

--- auth.cpp:20-41 ---
...

--- session.cpp:31-45 ---
...

```

This is the context sent to the LLM.

### 23. Context optimization

Suppose initial retrieval gives 30 files = 35,000 tokens.
GraphMind decides: 7 files = 8,000 tokens.

Reduction: 35,000 → 8,000.
But remember: Reduction alone is not success. We need: smaller context + same/better task performance.

### 24. Model Selector

After context construction, GraphMind can estimate task complexity.

* **Task:** Rename variable
* Graph complexity: 1 file, 2 nodes, 0 dependencies
* → Small model


* **Task:** Refactor authentication system
* Graph complexity: 18 files, 73 nodes, 42 relationships, depth = 6
* → Strong model



Again, implement this after retrieval works.

### 25. LLM integration

Finally:
`GraphMind` → `Optimized Context` → `LLM API` → `Response`

Initially, one provider is enough. Don't waste time supporting five providers. Create an abstraction:

```python
class LLMProvider:
    def generate(self, prompt):
        pass

```

### 26. What does the user actually see?

Ideally: `graphmind ask "Fix expired token authentication"`

Output:

```text
GraphMind
──────────────────────────────────
Task: Bug fix / Authentication

Retrieval:
Keyword       ✓
Semantic      ✓
Symbol        ✓
Graph         ✓

Candidates: 42
Selected: 9
Context: 7,840 tokens
Original estimated context: 31,200 tokens
Model: Medium

Sending context to LLM...

AI Response
──────────────────────────────────
The authentication issue is caused by
validateToken() not checking expiration
before returning success.

Suggested changes:
...

```

### 27. Evaluation — THE MOST IMPORTANT PART

Now imagine we have 30 coding tasks.
For each task:

* Task → Baseline → Result
* Task → GraphMind → Result

**Metric 1 — Retrieval Precision**
Suppose GraphMind retrieves 10 functions and 8 are actually relevant.


$$\text{Precision} = \frac{8}{10} = 80\%$$

### 28. Retrieval Recall

Suppose there are actually 10 relevant functions and GraphMind found 8.


$$\text{Recall} = \frac{8}{10} = 80\%$$

* Precision asks: "Of what we retrieved, how much was useful?"
* Recall asks: "Of what was useful, how much did we find?"
Both matter.

### 29. Context efficiency

Measure Baseline tokens vs GraphMind tokens.
For example, Baseline: 15,000, GraphMind: 8,000.


$$\text{Reduction} = \frac{15000 - 8000}{15000} \times 100$$

### 30. Task success

This is perhaps more important than token reduction. Did the generated solution compile? pass tests? fix the bug?
For coding tasks, automated tests are extremely useful.

Example: Baseline Tests passed = 8/10, GraphMind Tests passed = 9/10.
Now you have meaningful evidence.

### 31. Latency

Measure: Indexing time, Retrieval time, Graph traversal time, LLM time, Total time.
Because GraphMind itself has overhead.

### 32. Cost

If using a paid LLM API: Input tokens, Output tokens, Price/token.
Your final report can say: *"We experimentally evaluated whether graph-aware context selection reduces token consumption and API cost while preserving coding-task performance."*

### 33. Baselines

You should have at least:

* Baseline 1: Keyword
* Baseline 2: Semantic
* Baseline 3: Semantic + Symbol
* Proposed: GraphMind

### 34. The complete final architecture

```text
                         GRAPHMIND
                             │
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 │ OFFLINE               │ ONLINE
                 │                       │
                 ↓                       ↓
             Repository              User Query
                 │                       │
                 ↓                       ↓
            File Scanner           Task Analyzer
                 │                       │
                 ↓                       ↓
            Tree-sitter             Candidate Retrieval
                 │                  ┌────┼────┐
                 ↓                  │    │    │
                AST              Keyword Semantic Symbol
                 │                  │    │    │
                 ↓                  └────┼────┘
         Entity Extraction               ↓
                 │                 Candidates
                 ↓                      │
       Relationship Extraction          ↓
                 │                 Graph Mapping
                 ↓                      │
        Code Knowledge Graph             ↓
                 │                 Graph Ranking
                 │                      │
                 └──────────────┐       ↓
                                │   Context Builder
                                │       │
                                │       ↓
                                │   Model Selector
                                │       │
                                │       ↓
                                │      LLM
                                │       │
                                │       ↓
                                └──► Response

```

### 35. What YOU should learn first

Follow this order:

* **Level 1 — Graph fundamentals:** Node, Edge, Directed/Weighted graph, BFS, DFS.
* **Level 2 — Code analysis:** Parsing, AST, Tree-sitter, Call/Dependency graph.
* **Level 3 — Retrieval:** Keyword search, Embeddings, Semantic search, RAG.
* **Level 4 — Graph retrieval:** Graph traversal, Ranking, Subgraph selection.
* **Level 5 — LLM systems:** Prompt construction, Context window, Tokenization.
* **Level 6 — Evaluation:** Precision, Recall, F1, Latency, Cost.

### 36. Your team's actual development roadmap

* **Milestone 0 — Project setup:** GitHub, Python env, Project structure.
* **Milestone 1 — Repository indexing:** File discovery → Tree-sitter → AST/symbols.
* **Milestone 2 — Graph construction:** Entities → Relationships → NetworkX graph.
* **Milestone 3 — Graph inspection:** CLI `graphmind graph / stats`.
* **Milestone 4 — Retrieval baseline:** Keyword + semantic search.
* **Milestone 5 — Hybrid retrieval:** Combine keyword + semantic + symbol.
* **Milestone 6 — Graph-aware retrieval:** Candidates → Graph → Expansion → Ranking. *(Major milestone)*
* **Milestone 7 — Context optimizer:** Ranked nodes → Token budget → Selected code.
* **Milestone 8 — LLM:** Selected context → LLM → Answer.
* **Milestone 9 — Model selection:** Routing based on complexity.
* **Milestone 10 — Evaluation:** Benchmark → Baselines vs GraphMind → Metrics.

### 37. What should you NOT decide yet?

Don't force these decisions today: Exact graph schema, exact scoring formula, exact graph traversal algorithm, exact embedding model, vector database, Neo4j, LangChain/LangGraph, MCP support.
Choose them when you reach the relevant milestone.

### 38. One very important thing about your final-year project

Your project should have this loop:

```text
        ┌─────────────────────┐
        │     Hypothesis      │
        └──────────┬──────────┘
                   ↓
             Implementation
                   ↓
               Experiment
                   ↓
                Results
                   ↓
              Improvement
                   │
                   └─────────────►

```

### 39. If I were starting GraphMind with your team tomorrow

I would give the team this exact first assignment:

* **Person 1:** Study and implement Tree-sitter (Output: files + functions + classes + imports).
* **Person 2:** Study and implement NetworkX (Output: nodes, edges, graph stats).
* **Person 3:** Study and implement Keyword + semantic retrieval (Output: query → ranked code candidates).

Then bring all three together.

### 40. The simplest possible understanding

1. **Tree-sitter** tells us what is inside the code (Code → AST).
2. **Graph** tells us how code entities are connected (Function A → calls → Function B).
3. **Retrieval** finds possible relevant code (Query → Candidates).
4. **GraphMind** ranks and filters those candidates (Candidates → Graph + relevance → Useful subset).
5. **LLM** receives the useful subset instead of the entire repository.

#### And the first thing we should do together:

Before writing GraphMind code, create four concrete documents:

1. `01_PROJECT_REQUIREMENTS.md`
2. `02_SYSTEM_ARCHITECTURE.md`
3. `03_GRAPH_SCHEMA.md`
4. `04_DEVELOPMENT_ROADMAP.md`

Then make the GitHub repository and start Milestone 1: Repository Scanner + Tree-sitter.

```

```
