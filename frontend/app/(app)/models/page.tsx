import { PageHeader } from "@/components/platform/PageHeader";
import { EmptyState } from "@/components/platform/icons";

export default function ModelsPage() {
  return (
    <>
      <PageHeader title="Models" description="BYO LLM credentials." />
      <div className="p-s-8"><EmptyState title="Models — coming in Phase 2" /></div>
    </>
  );
}
