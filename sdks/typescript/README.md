# @agentguard/sdk

Official TypeScript / Node.js SDK for the AgentGuard AI Runtime Governance Control Plane.

## Installation

```bash
npm install @agentguard/sdk
# or
pnpm add @agentguard/sdk
# or
yarn add @agentguard/sdk
```

## Quickstart

```typescript
import { AgentGuardClient, AgentGuardGovernanceRefusal } from "@agentguard/sdk";

const client = new AgentGuardClient({
  agentCode: "AG-FIN-01",
  agentKey: "ag_agent_...",
  baseUrl: "https://agentguard-backend.onrender.com",
});

async function run() {
  // 1. Authenticate Machine Credentials
  await client.authenticate();

  // 2. Pre-flight Action Authorization
  try {
    const decision = await client.authorize({
      action_requested: "execute_wire_transfer",
      amount: 1200.0,
      parameters: { recipient: "ACC-1029", amount: 1200.0 },
    });

    console.log("Action allowed! Execution token:", decision.execution_gate_token);

    // 3. Egress Tool Execution Proxy
    const result = await client.execute({
      tool_name: "stripe_payout",
      parameters: { amount: 1200.0 },
      execution_gate_token: decision.execution_gate_token!,
    });

    console.log("Tool execution result:", result);
  } catch (err) {
    if (err instanceof AgentGuardGovernanceRefusal) {
      console.warn("Governance refused action:", err.message);
    } else {
      console.error("Agent error:", err);
    }
  }
}

run();
```
