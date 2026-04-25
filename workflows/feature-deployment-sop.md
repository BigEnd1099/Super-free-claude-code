# Autonomous Feature Deployment SOP

This Standard Operating Procedure (SOP) defines the 4-phase framework for autonomously adding new features to the Antigravity project. Agents must follow these phases strictly to ensure system stability and alignment with project goals.

---

## 🛰️ Phase 1: Feature Documentation & Context Updating
Before any code changes, the context must be established and documented.

1. **Context Update**: Update the master `Gemini.md` (or create a feature-specific markdown like `feature_analytics.md`) in the workspace.
2. **Explicit Scope**: Define exactly what is being added. Detail UI changes, data requirements, and core logic.
3. **Brand Alignment**: Consult `brand_guidelines.md` to ensure the new feature matches the existing design system.
4. **MCP Dependencies**: Identify and configure any required external tools or API keys in the MCP configuration.

---

## 🚀 Phase 2: Agent Configuration & Briefing
Configure the agent for the specific task at hand.

1. **Model Selection**:
   - **Gemini 3 Pro**: Use for visual/UI-heavy components (dashboards, layouts).
   - **Claude Opus**: Use for complex backend logic, database restructuring, or complex routing.
2. **Planning Mode**: Ensure `Planning Mode` is enabled in the Antigravity manager. Use `cf -cfg planning:on`.
3. **The Brief**: Initiate a new chat and point the agent to the updated context file:
   > "Read the updated [FeatureFile].md. I want to add the [FeatureName] feature. Review the codebase, formulate an implementation plan, and ensure it follows brand_guidelines.md."

---

## 🧠 Phase 3: Plan Review & Iteration
Do not execute until the architecture is validated.

1. **Review Task List**: Review the generated `implementation_plan.md` artifact.
2. **Feedback Injection**: Use inline comments or the "Inject Comments" feature on the implementation plan to correct architecture or UI decisions.
3. **Approval**: Only provide the "just do it" or "approve" command once the plan is flawless.

---

## 🧪 Phase 4: Autonomous Testing & Debugging
The agent must verify its own work before the mission is considered complete.

1. **Browser Testing**: Use the `browser_subagent` to launch the application and verify routing, data display, and UI responsiveness.
2. **Review Artifacts**: Examine the browser recordings in the artifacts folder to confirm behavior without manual interaction.
3. **Vibe-Code Debugging**: If issues are found, use natural language to describe the problem (e.g., "The sidebar is overlapping") and let the agent refactor autonomously.
4. **Safety Net**: If the feature breaks existing stability, use the "Undo" command to revert to the pre-deployment state.
