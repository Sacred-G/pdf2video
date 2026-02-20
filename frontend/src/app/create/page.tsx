import { JobCreateForm } from "@/components/jobs/job-create-form";
import { SectionHeading } from "@/components/shared/section-heading";

export default function CreatePage() {
  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="New Workflow"
        title="Create video job"
        description="Upload a PDF or text+images, configure style and voice, then launch an async generation job."
      />
      <JobCreateForm />
    </div>
  );
}
