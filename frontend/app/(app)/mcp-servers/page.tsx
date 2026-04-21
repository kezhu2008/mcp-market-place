import { PageHeader } from "@/components/platform/PageHeader";
import { EmptyState } from "@/components/platform/icons";

export default function McpServersPage() {
  return (
    <>
      <PageHeader title="MCP Servers" description="Bundles of tools exposed via Bedrock AgentCore Gateway." />
      <div className="p-s-8"><EmptyState title="MCP Servers — coming in Phase 2" /></div>
    </>
  );
}
