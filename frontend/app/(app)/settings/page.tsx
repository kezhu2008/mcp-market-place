import { PageHeader } from "@/components/platform/PageHeader";

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Account and workspace." />
      <div className="p-s-5 md:p-s-8 max-w-[720px]">
        <div className="card p-s-5">
          <div className="overline mb-[10px]">account</div>
          <dl className="grid grid-cols-[140px_1fr] gap-y-[8px] font-mono text-mono">
            <dt className="text-text-mute">tenant</dt><dd>acme/prod</dd>
            <dt className="text-text-mute">region</dt><dd>ap-southeast-2</dd>
          </dl>
        </div>
      </div>
    </>
  );
}
