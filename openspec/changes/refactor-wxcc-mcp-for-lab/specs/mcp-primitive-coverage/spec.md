## ADDED Requirements

### Requirement: Demonstrate MCP tools

The server SHALL expose MCP tools with typed input schemas so learners can see how model-
invoked actions are declared and validated.

#### Scenario: Tool declares a typed input schema

- **WHEN** a client inspects any tool
- **THEN** the tool advertises a JSON schema derived from a typed input model

### Requirement: Demonstrate MCP resources

The server SHALL expose MCP resources that provide reference context (agent states,
troubleshooting runbook, config dependency map, write-safety guide) addressable by URI.

#### Scenario: Resource is readable by URI

- **WHEN** a client reads a registered resource URI
- **THEN** the server returns the corresponding reference content

### Requirement: Demonstrate MCP prompts

The server SHALL expose MCP prompts that template the diagnose and onboard flows for the
user to invoke.

#### Scenario: Prompt renders with arguments

- **WHEN** a client invokes the diagnose or onboard prompt with arguments
- **THEN** the server returns a rendered prompt string incorporating those arguments

### Requirement: Demonstrate elicitation for confirmations

The server SHALL use MCP elicitation (`ctx.elicit`) to obtain explicit user confirmation
before committing any write, replacing the prior `confirm=True` boolean parameter as the
primary confirmation mechanism.

#### Scenario: Write elicits confirmation before commit

- **WHEN** a write tool reaches the commit step
- **THEN** the server elicits a confirmation response from the user
- **AND** commits only if the user approves, otherwise aborts without mutating WxCC

### Requirement: Demonstrate progress notifications

The server SHALL emit progress notifications (`ctx.report_progress`) during the multi-step
onboarding flow.

#### Scenario: Onboarding reports progress

- **WHEN** the onboard flow performs its sequence of steps
- **THEN** the server reports incremental progress to the client

### Requirement: Demonstrate client-facing logging

The server SHALL emit client-facing log messages (`ctx.info`/`ctx.warning`/`ctx.error`)
from tools, distinct from server-side structured logging, so learners see MCP log
notifications in the client.

#### Scenario: Tool streams a log notification

- **WHEN** a tool executes a noteworthy step
- **THEN** the server sends a log notification visible to the MCP client

### Requirement: Optional sampling demonstration

The server MAY demonstrate MCP sampling by requesting a completion from the client's LLM
to summarize a diagnosis. When implemented, it SHALL degrade gracefully if the client does
not support sampling.

#### Scenario: Sampling summarizes a diagnosis when supported

- **WHEN** the diagnosis completes and the client supports sampling
- **THEN** the server requests an LLM summary and includes it in the result

#### Scenario: Graceful fallback without sampling

- **WHEN** the client does not support sampling
- **THEN** the diagnosis still returns its structured result without error
