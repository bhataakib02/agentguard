# SDK Integration Guide

This guide details how to integrate the official **AGENTGUARD** Python and TypeScript SDKs with your autonomous AI agents, LangChain workflows, CrewAI teams, and custom application backends.

---

## 1. Python SDK (`agentguard`)

The Python SDK provides idiomatic bindings, asynchronous clients, and direct middleware for popular agentic frameworks.

### 1.1 Installation

Install the Python SDK from source or local checkout:

```bash
cd sdks/python
pip install -e .

# Or install with framework extensions:
pip install -e ".[langchain,crewai]"
```

### 1.2 Basic Client Usage

```python
from agentguard import AgentGuardClient

# 1. Initialize client
client = AgentGuardClient(
    api_key="ag_live_pk_YOUR_ORGANIZATION_API_KEY",
    base_url="http://localhost:8000/api"
)

# 2. Evaluate an agent action before execution
decision = client.evaluate(
    agent_id="agent-uuid-001",
    action="send_external_email",
    target_resource="email_service",
    parameters={
        "recipient": "partner@external.com",
        "subject": "Q3 Financial Summary"
    }
)

# 3. Handle the decision outcome
if decision.outcome == "ALLOW":
    print("Action permitted. Executing tool...")
elif decision.outcome == "REVIEW":
    print(f"Action held for human approval: Escalation ID {decision.escalation_id}")
elif decision.outcome == "REFUSE":
    print(f"Action blocked by AGENTGUARD! Reason: {decision.reasons}")
```

### 1.3 LangChain Integration

Wrap your LangChain agents with the `AgentGuardCallbackHandler`:

```python
from langchain.agents import initialize_agent, load_tools
from langchain_openai import ChatOpenAI
from agentguard import AgentGuardCallbackHandler

# Initialize callback handler
guard_handler = AgentGuardCallbackHandler(
    api_key="ag_live_pk_YOUR_API_KEY",
    agent_id="langchain-analyst-agent",
    base_url="http://localhost:8000/api"
)

llm = ChatOpenAI(model="gpt-4o")
tools = load_tools(["serpapi", "llm-math"], llm=llm)

agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    callbacks=[guard_handler]
)

# Agent tool calls are automatically evaluated by AGENTGUARD PACE
agent.run("Calculate the quarterly bonus allocation for Employee 4490")
```

### 1.4 CrewAI Integration

Enforce guardrails on CrewAI agents:

```python
from crewai import Agent, Task, Crew
from agentguard import AgentGuardCrewMiddleware

guard_middleware = AgentGuardCrewMiddleware(
    api_key="ag_live_pk_YOUR_API_KEY",
    base_url="http://localhost:8000/api"
)

researcher = Agent(
    role="Senior Market Analyst",
    goal="Analyze confidential market data",
    backstory="You analyze sensitive enterprise market documents.",
    step_callback=guard_middleware.on_agent_step
)
```

---

## 2. TypeScript / Node.js SDK (`@agentguard/sdk`)

The TypeScript SDK provides a typed interface for Node.js backends and serverless functions.

### 2.1 Installation

Build and link the TypeScript SDK:

```bash
cd sdks/typescript
npm install
npm run build
```

### 2.2 Client Usage Example

```typescript
import { AgentGuardClient, DecisionOutcome } from '@agentguard/sdk';

// 1. Initialize client
const client = new AgentGuardClient({
  apiKey: process.env.AGENTGUARD_API_KEY || 'ag_live_pk_TEST',
  baseUrl: process.env.AGENTGUARD_API_URL || 'http://localhost:8000/api'
});

// 2. Evaluate action with PACE
async function runToolSafely() {
  const decision = await client.evaluate({
    agentId: 'ts-agent-01',
    action: 'execute_sql',
    targetResource: 'postgres://customers_db',
    parameters: {
      query: 'DROP TABLE customers;'
    }
  });

  // 3. Inspect decision
  switch (decision.outcome) {
    case DecisionOutcome.ALLOW:
      console.log('Permitted by policy. Capability Token:', decision.capabilityToken);
      break;
    case DecisionOutcome.REVIEW:
      console.warn('Action held for Security Officer review. Escalation:', decision.escalationId);
      break;
    case DecisionOutcome.REFUSE:
      console.error('BLOCKED by AGENTGUARD PACE:', decision.reasons);
      throw new Error(`Agent action refused: ${decision.reasons.join(', ')}`);
  }
}
```

---

## 3. Error Handling & Retry Policies

Both SDKs handle network transient errors and provide typed exception classes:

1. **Authentication Error (`401`):** Raised when the API key or JWT token is invalid or expired.
2. **Authorization Error (`403`):** Raised when the caller lacks the required role or organization scope.
3. **Validation Error (`422`):** Raised when payload schemas fail parameter validation.
4. **Rate Limit Error (`429`):** Indicates quota or rate limit exhaustion. The client automatically backs off with exponential jitter.
