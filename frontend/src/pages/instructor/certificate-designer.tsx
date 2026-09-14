import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
/**
 * Instructor certificate designer — gallery -> editor flow (plan Task 7).
 * No page-level shell: renders inside InstructorLayout, matching
 * gradebook.tsx / grading-queue.tsx conventions.
 */
import * as React from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { TemplateGallery } from "@/components/certificates/designer/TemplateGallery";
import { CertificateDesignerEditor } from "@/components/certificates/designer/CertificateDesignerEditor";
import { listDesignerTemplates, errorDetail } from "@/api/certificateDesigner";
import type { DesignerTemplate } from "@/lib/certificateDesignerTypes";
import { useAuthStore } from "@/store/auth";

export default function InstructorCertificateDesignerPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin" || user?.role === "superadmin";

  const [templates, setTemplates] = React.useState<DesignerTemplate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [editing, setEditing] = React.useState<DesignerTemplate | null | "new">(
    null,
  );

  const load = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listDesignerTemplates();
      setTemplates(data);
    } catch (err) {
      setError(errorDetail(err, "Failed to load certificate templates"));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  if (editing !== null) {
    return (
      <div>
        <button
          onClick={() => setEditing(null)}
          className="flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-4"
        >
          <ArrowLeft size={16} />
          Back to templates
        </button>
        <CertificateDesignerEditor
          template={editing === "new" ? null : editing}
          isAdmin={isAdmin}
          onCancel={() => setEditing(null)}
          onSaved={(saved) => {
            setEditing(null);
            load();
            setTemplates((prev) => {
              const exists = prev.some((t) => t.id === saved.id);
              return exists
                ? prev.map((t) => (t.id === saved.id ? saved : t))
                : [saved, ...prev];
            });
          }}
        />
      </div>
    );
  }

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="dash-h1 mb-1">Certificates</h1>
          <p className="text-slate-600 text-sm">
            Design and manage the certificate templates issued to your students.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-instructor-certificate-designer"
    >
      {error ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-danger-600 mb-3">{error}</p>
          <Button variant="outline" onClick={load}>
            Try again
          </Button>
        </Card>
      ) : (
        <TemplateGallery
          templates={templates}
          loading={loading}
          onCreateNew={() => setEditing("new")}
          onEdit={(t) => setEditing(t)}
          onChanged={load}
          isAdmin={isAdmin}
        />
      )}
    </PageLayout>
  );
}
