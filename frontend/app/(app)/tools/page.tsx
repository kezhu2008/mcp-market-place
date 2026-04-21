import { PageHeader } from "@/components/platform/PageHeader";
import { EmptyState } from "@/components/platform/icons";

export default function ToolsPage() {
  return (
    <>
      <PageHeader title="Tools" description="REST endpoints wrapped as reusable actions." />
      <div className="p-s-8"><EmptyState title="Tools — coming in Phase 2" /></div>
    </>
  );
}
