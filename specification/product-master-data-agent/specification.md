# Specification: product-master-data-agent

> **Guidelines**: Read all applicable guidelines before executing ANY tasks below:
> - [guidelines.md](../guidelines.md) — Universal execution rules
> - [guidelines-agent.md](../guidelines-agent.md) — Universal agent patterns
> - [guidelines-agent-python.md](../guidelines-agent-python.md) — Python implementation details
> - [guidelines-agent-skills.md](../guidelines-agent-skills.md) — Runtime skills patterns
> - [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) — MCP integration patterns

---

## Basic Setup

- [x] Read the project input (`product-requirements-document.md` and `intent.md` at the solution root)
- [x] Bootstrap agent code in `assets/product-master-data-agent/` using instructions from the `sap-agent-bootstrap` skill (invoke from inside `assets/product-master-data-agent/`, use copy commands — do NOT create files manually)
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

---

## Runtime Skills

> Read [guidelines-agent-skills.md](../guidelines-agent-skills.md) to decide if runtime skills are needed.

No runtime skills are required for this agent — the product data query logic is straightforward and can be handled entirely by the system prompt and MCP tools without separate skill files.

---

## Project-Specific Tasks

### System Prompt

- [x] Open `assets/product-master-data-agent/app/agent.py` and write the system prompt in the `get_system_prompt()` function with the following instructions:
  - The agent is a Product Master Data Assistant for Sales Representatives, accessible via SAP Joule.
  - It helps users find product information by querying SAP S/4HANA — including product descriptions, base units of measure, product categories, and product classifications.
  - It MUST use tools to retrieve live data from S/4HANA. It must NEVER fabricate, guess, or invent product data.
  - When calling tools that support pagination, always set the page size parameter (`top`, `limit`, etc.) to a maximum of 100 items to prevent context overflow. Inform the user when this limit is applied.
  - If a product is not found, the agent must clearly state this and not guess or infer data.
  - If partial data is returned (e.g. no classification data for a product), the agent should return what is available and clearly note what is missing.
  - If a tool returns an error, relay the error message exactly as received. Do not suggest workarounds unless asked.
  - Keep responses concise and clear — Sales Representatives need quick answers during customer interactions.

### Product Base Data Query (REQ-01, REQ-02)

- [x] Ensure the agent can answer questions about product descriptions using the Product Master MCP tools (e.g. "What is the description of product X?", "What unit of measure is used for product Y?")
- [x] Ensure the agent can retrieve product category information for a given product number
- [x] Ensure the agent can search for products by name or partial description and return matching results with their base data

### Product Classification Data Query (REQ-03)

- [x] Ensure the agent can answer questions about product classifications and characteristics (e.g. "What class does product X belong to?", "What are the characteristic values for product Y?")
- [x] Ensure the agent correctly handles products with no classification data by returning available base data and noting the absence of classification

### Graceful Error Handling (REQ-05)

- [x] Ensure the agent returns a clear, user-friendly message when a product number does not exist in S/4HANA
- [x] Ensure the agent handles API errors gracefully — relaying the error without fabricating fallback data

---

## Business Instrumentation

- [x] Implement business step instrumentation for each milestone from the PRD using structured logging and OpenTelemetry spans. Extract business logic from `stream()` into a plain async helper (e.g. `_run_agent()`) to avoid `GeneratorExit` context errors:
  - `M1` — Natural Language Query Received: `[M1.achieved]: user query received and parsed successfully` / `[M1.missed]: query could not be parsed or received`
  - `M2` — Product Data Retrieved from S/4HANA: `[M2.achieved]: product data retrieved from S/4HANA API` / `[M2.missed]: S/4HANA API returned no data or an error`
  - `M3` — Answer Delivered to User: `[M3.achieved]: answer delivered to user within target latency` / `[M3.missed]: response not delivered or exceeded latency target`
- [x] Verify `bootstrap(app)` is called after `app = server.build()` in `main.py`

---

## MCP Tool Integration

> Read [guidelines-agent-mcp.md](../guidelines-agent-mcp.md) for complete MCP integration patterns.
> This agent uses **Path A** — API spec files with no existing MCP server.

**MCP API:** `sap.s4:apiResource:API_PRODUCT_SRV:v1`
**MCP tool scope:** read-only
**Resources in scope:** A_Product, A_ProductDescription, A_ProductPlant, A_ProductBasicText

**MCP API:** `sap.s4:apiResource:API_CLFN_PRODUCT_SRV:v1`
**MCP tool scope:** read-only
**Resources in scope:** A_ClfnProduct, A_ClfnProductClass, A_ClfnProductCharc

- [x] Invoke the `mcp-translation-file` skill for `specification/product-master-data-agent/api-specs/API_PRODUCT_SRV.edmx` to generate the MCP translation file
- [x] Invoke the `mcp-translation-file` skill for `specification/product-master-data-agent/api-specs/API_CLFN_PRODUCT_SRV.edmx` to generate the MCP translation file
- [x] Invoke the `setup-solution` skill to create and register both MCP server assets from the generated translation files
- [x] Read the generated `asset.yaml` files for both MCP server assets and copy the exact `ordId` values — do NOT invent or guess ORD IDs
- [x] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from the `mcp_tools` module — NEVER import directly from `sap_cloud_sdk.agentgateway`, NEVER create direct HTTP clients
- [x] Add both MCP server dependencies to `assets/product-master-data-agent/asset.yaml` under `requires` using the exact ORD IDs from the generated assets
- [x] Generate `mcp-mock.json` using the `mcp-mock-config` skill (required before tests can run)

---

## Testing

> See [guidelines-agent-python.md](../guidelines-agent-python.md) for Python testing setup and patterns.

- [x] `conftest.py` only sets `IBD_TESTING=true`
- [x] Write unit tests in `assets/product-master-data-agent/tests/`:
  - One unit test for the Product Master MCP tool (querying product base data)
  - One unit test for the Product Classification MCP tool (querying classification data)
  - One unit test for the graceful not-found handling path
- [x] Write one integration test executing an end-to-end flow: simulated Sales Rep query → agent selects correct MCP tool → returns formatted product answer (mocked LLM + mocked MCP)
- [x] Run `pytest` from `assets/product-master-data-agent/` (no args) — if coverage < 70%, add tests until threshold met
- [x] Run `pytest` again (no args) to generate final `test_report.json`
- [x] Verify `test_report.json` exists in `assets/product-master-data-agent/`
