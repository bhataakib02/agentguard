/**
 * Automated test suite for @agentguard/sdk (TypeScript / Node.js)
 */

import assert from "node:assert";
import {
  AgentGuardClient,
  AgentGuardError,
  AgentGuardAuthError,
  AgentGuardGovernanceRefusal,
  AgentGuardCircuitBreakerError,
  AgentGuardExecutionError
} from "../dist/index.js";

async function runTests() {
  console.log("=== Testing @agentguard/sdk TypeScript SDK ===");

  // 1. Instantiation
  const client = new AgentGuardClient({
    agentCode: "AGENT-FIN-001",
    agentKey: "ag_agent_test_key_1234567890",
    baseUrl: "http://localhost:8000",
    orgId: "org-test-uuid",
    timeoutMs: 5000,
    raiseOnRefusal: true
  });

  assert.ok(client, "Client should instantiate properly");
  assert.strictEqual(typeof client.authenticate, "function");
  assert.strictEqual(typeof client.authorize, "function");
  assert.strictEqual(typeof client.execute, "function");
  assert.strictEqual(typeof client.invoke, "function");
  assert.strictEqual(typeof client.heartbeat, "function");
  assert.strictEqual(typeof client.scanPii, "function");
  assert.strictEqual(typeof client.scanOutput, "function");
  console.log("✓ Test 1 Passed: Client instantiated with full API surface");

  // 2. Custom Error Hierarchy
  const refusal = new AgentGuardGovernanceRefusal("Action blocked", "dec_123", 85);
  assert.ok(refusal instanceof AgentGuardError);
  assert.strictEqual(refusal.decisionId, "dec_123");
  assert.strictEqual(refusal.riskScore, 85);

  const cbError = new AgentGuardCircuitBreakerError("Circuit tripped", "AGENT-001");
  assert.ok(cbError instanceof AgentGuardError);
  assert.strictEqual(cbError.agentCode, "AGENT-001");

  const execError = new AgentGuardExecutionError("SSRF Blocked", 400);
  assert.ok(execError instanceof AgentGuardError);
  assert.strictEqual(execError.statusCode, 400);

  const authError = new AgentGuardAuthError("Invalid key", 401);
  assert.ok(authError instanceof AgentGuardError);
  assert.strictEqual(authError.statusCode, 401);
  console.log("✓ Test 2 Passed: Custom error class hierarchy and properties verified");

  // 3. Mock Network Verification for Authorize & Refusal
  const originalFetch = globalThis.fetch;
  try {
    // Mock Authorize REFUSE
    globalThis.fetch = async (url, opts) => {
      if (url.includes("/api/runtime/authorize")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            decision_id: "dec_refuse_test",
            decision: "REFUSE",
            explanation: "Amount exceeds risk threshold",
            risk_score: 90
          })
        };
      }
      return { ok: true, status: 200, json: async () => ({}) };
    };

    let threwRefusal = false;
    try {
      await client.authorize({
        action_requested: "TRANSFER_FUNDS",
        amount: 500000.0,
        target_resource: "bank_ledger"
      });
    } catch (e) {
      if (e instanceof AgentGuardGovernanceRefusal) {
        threwRefusal = true;
        assert.strictEqual(e.decisionId, "dec_refuse_test");
        assert.strictEqual(e.riskScore, 90);
      }
    }
    assert.ok(threwRefusal, "Client should throw AgentGuardGovernanceRefusal on policy REFUSE");
    console.log("✓ Test 3 Passed: raiseOnRefusal throws AgentGuardGovernanceRefusal on policy REFUSE");

    // Mock Circuit Breaker rejection
    globalThis.fetch = async (url, opts) => {
      if (url.includes("/api/runtime/authorize")) {
        return {
          ok: false,
          status: 403,
          text: async () => "Circuit breaker is active for agent"
        };
      }
      return { ok: false, status: 500, text: async () => "Server error" };
    };

    let threwCb = false;
    try {
      await client.authorize({ action_requested: "EXECUTE" });
    } catch (e) {
      if (e instanceof AgentGuardCircuitBreakerError) {
        threwCb = true;
        assert.strictEqual(e.agentCode, "AGENT-FIN-001");
      }
    }
    assert.ok(threwCb, "Client should throw AgentGuardCircuitBreakerError on circuit breaker refusal");
    console.log("✓ Test 4 Passed: 403 Circuit breaker response throws AgentGuardCircuitBreakerError");

    // Mock scanOutput
    globalThis.fetch = async (url, opts) => {
      if (url.includes("/api/runtime/scan-output")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            blocked: false,
            action: "ALLOW",
            sanitized_output: "Report approved",
            violations_count: 0,
            toxicity_score: 0.02,
            hallucination_score: 0.05,
            findings: []
          })
        };
      }
      return { ok: false, status: 500, text: async () => "Error" };
    };

    const scanResult = await client.scanOutput({
      output_text: "Report approved",
      reference_context: "Corporate context"
    });
    assert.strictEqual(scanResult.blocked, false);
    assert.strictEqual(scanResult.action, "ALLOW");
    console.log("✓ Test 5 Passed: scanOutput correctly dispatches and parses response");

  } finally {
    globalThis.fetch = originalFetch;
  }

  console.log("\n=== ALL TypeScript SDK Tests Passed Successfully (5/5) ===");
}

runTests().catch(err => {
  console.error("Test failed:", err);
  process.exit(1);
});
