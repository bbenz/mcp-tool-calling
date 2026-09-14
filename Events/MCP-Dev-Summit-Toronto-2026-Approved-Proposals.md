# MCP Dev Summit Toronto 2026 - Session Proposals

**Speaker:** Brian Benz  
**Event:** MCP Dev Summit Toronto, October 5-6, 2026  
**CFP deadline:** July 14, 2026  
**Event:** https://events.linuxfoundation.org/mcp-dev-summit-toronto

---

## Accepted Proposal

### Session Title

Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy

### Description

MCP authorization gets a client to a protected remote server. The harder question arrives at tools/call: may this user, through this client, refund this order with these arguments?

We'll trace that request through MCP's authorization flow: Protected Resource Metadata, authorization-server discovery, PKCE, resource indicators, delegated scopes, and audience-bound access tokens. Then we cross the protocol boundary. The MCP server maps identity and scopes to tool-level policy, validates arguments against business rules, and preserves the user's identity when it calls the upstream API. Tool annotations can help a client present risk, but the server never treats them as authorization. The client owns human approval for the irreversible action.

Finally, we'll test prompt injection that selects an unintended tool, a confused-deputy request, and token reuse against the wrong MCP server. Attendees leave with an MCP-specific control map and an audit record that ties a tools/call request to the user, client, resource, policy, and result.

### Topic

Security, Identity + Trust

### Session Format

Session Presentation (25 minutes)

### Audience Level

Intermediate

### Benefits to the Ecosystem

Consistent authorization patterns make remote MCP servers easier to combine and safer to reuse. The talk gives server authors, client developers, and platform teams a shared model for delegated identity, tool-level policy, approvals, and audit evidence instead of leaving each integration to invent those boundaries independently.

---

### Published Event Details: https://events.linuxfoundation.org/mcp-dev-summit-toronto/program/schedule/


6 Oct • 15:40-16:05

Ballroom East/Center

Security, Identity + Trust
Intermediate

MCP authorization gets a client to a protected remote server. The harder question arrives at tools/call: may this user, through this client, refund this order with these arguments?

We'll trace that request through MCP's authorization flow: Protected Resource Metadata, authorization-server discovery, PKCE, resource indicators, delegated scopes, and audience-bound access tokens. Then we cross the protocol boundary. The MCP server maps identity and scopes to tool-level policy, validates arguments against business rules, and preserves the user's identity when it calls the upstream API. Tool annotations can help a client present risk, but the server never treats them as authorization. The client owns human approval for the irreversible action.

Finally, we'll test prompt injection that selects an unintended tool, a confused-deputy request, and token reuse against the wrong MCP server. Attendees leave with an MCP-specific control map and an audit record that ties a tools/call request to the user, client, resource, policy, and result.

Speakers

Brian Benz
Principal AI Advocate, Microsoft

