# AgentGuard Python SDK (`agentguard`)

Official enterprise runtime governance SDK and middleware for autonomous AI agents, LangChain, and CrewAI.

## Installation

```bash
pip install agentguard
# Or with framework integrations:
pip install "agentguard[langchain,crewai]"
```

## Quickstart

```python
from agentguard import AgentGuardClient, AgentGuardGovernanceRefusal

# Initialize client with Machine Identity
client = AgentGuardClient(
    agent_code="AG-FIN-01",
    agent_key="ag_agent_...",
    base_url="https://agentguard-backend.onrender.com"
)

# 1. Authenticate (acquires session JWT & cryptographic Ed25519 passport)
token = client.authenticate()

# 2. Pre-flight Action Authorization
try:
    decision = client.authorize(
        action_requested="execute_wire_transfer",
        amount=1500.0,
        parameters={"recipient": "ACC-9921", "amount": 1500.0}
    )
    print(f"Action allowed! Gate Token: {decision['execution_gate_token']}")
    
    # 3. Secure Outbound Tool Execution Proxy
    result = client.execute(
        tool_name="stripe_payout",
        parameters={"amount": 1500.0},
        execution_gate_token=decision["execution_gate_token"]
    )
except AgentGuardGovernanceRefusal as e:
    print(f"Action refused by AgentGuard policy: {e.explanation}")
```

## LangChain Integration

```python
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from agentguard import AgentGuardClient, LangChainAgentGuardHandler

client = AgentGuardClient(agent_code="AG-LANG-01", agent_key="ag_agent_...")
handler = LangChainAgentGuardHandler(client=client, block_on_pii=False)

agent = initialize_agent(
    tools=tools,
    llm=ChatOpenAI(temperature=0),
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    callbacks=[handler]
)
```

## CrewAI Integration

```python
from crewai import Agent, Crew, Task
from agentguard import AgentGuardClient, CrewAIAgentGuardMiddleware

client = AgentGuardClient(agent_code="AG-CREW-01", agent_key="ag_agent_...")
guard = CrewAIAgentGuardMiddleware(client=client)

@guard.guard_tool(tool_name="database_query", amount=0.0)
def query_database(sql: str):
    return db.execute(sql)
```
