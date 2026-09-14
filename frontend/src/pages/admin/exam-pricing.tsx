import { useEffect, useState } from "react";
import { api } from "@/api/axios";
import { money, paperError, type PriceSlab } from "@/api/exam-papers";
import { PageLayout, PageHeading } from "@/components/design-system/PageLayout";
import { Button } from "@/components/ui/button";

const empty = {
  exam: "JEE" as "JEE" | "NEET",
  title: "",
  min_questions: 5,
  max_questions: 10,
  price: "",
  active: false,
};
export default function ExamPricing() {
  const [rows, setRows] = useState<PriceSlab[]>([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState<number>();
  const [deleting, setDeleting] = useState<PriceSlab>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reload = async () => {
    const { data } = await api.get("/exam-papers/admin/slabs");
    setRows(data.slabs);
  };
  useEffect(() => {
    reload().catch((e) => setError(paperError(e)));
  }, []);
  const perform = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await reload();
    } catch (e) {
      setError(paperError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <PageLayout
      header={
        <PageHeading
          eyebrow="Commerce"
          title="Exam paper pricing"
          description="Set question-count ranges and the price per paper. Published slabs appear for students; teaching staff generate without payment."
        />
      }
    >
      {error && (
        <p role="alert" className="astra-work p-4 text-red-800">
          {error}
        </p>
      )}
      <div className="grid gap-6 xl:grid-cols-2">
        <form
          className="astra-work p-5 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            void perform(async () => {
              const payload = {
                exam: form.exam,
                title: form.title,
                min_questions: form.min_questions,
                max_questions: form.max_questions,
                price_paise: Math.round(Number(form.price) * 100),
                active: form.active,
              };
              if (editing)
                await api.put(`/exam-papers/admin/slabs/${editing}`, payload);
              else await api.post("/exam-papers/admin/slabs", payload);
              setForm(empty);
              setEditing(undefined);
            });
          }}
        >
          <h2 className="text-xl font-bold">
            {editing ? "Edit pricing slab" : "Create pricing slab"}
          </h2>
          <label className="block">
            Exam
            <select
              className="w-full"
              value={form.exam}
              onChange={(e) =>
                setForm({ ...form, exam: e.target.value as "JEE" | "NEET" })
              }
            >
              <option>JEE</option>
              <option>NEET</option>
            </select>
          </label>
          <label className="block">
            Slab name
            <input
              className="w-full"
              required
              maxLength={100}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-2 gap-4">
            {(["min_questions", "max_questions"] as const).map((key, i) => (
              <label key={key}>
                {i ? "Maximum questions" : "Minimum questions"}
                <input
                  className="w-full"
                  type="number"
                  min={5}
                  max={180}
                  required
                  value={form[key]}
                  onChange={(e) =>
                    setForm({ ...form, [key]: Number(e.target.value) })
                  }
                />
              </label>
            ))}
          </div>
          <label className="block">
            Price per paper (INR)
            <input
              className="w-full"
              type="number"
              min={1}
              max={100000}
              step="0.01"
              required
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
            />
          </label>
          <label className="flex gap-2 items-center">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
            />
            Published to students
          </label>
          <p className="text-sm">
            Active ranges for the same exam cannot overlap. Changes apply to new
            purchases; existing checkouts retain their quoted price.
          </p>
          <div className="flex gap-3">
            <Button disabled={busy}>{busy ? "Saving…" : "Save slab"}</Button>
            {editing && (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditing(undefined);
                  setForm(empty);
                }}
              >
                Cancel edit
              </Button>
            )}
          </div>
        </form>
        <section className="astra-content p-5 space-y-4">
          <h2 className="text-xl font-bold">Configured slabs</h2>
          {!rows.length && (
            <p>
              No prices configured. Create and publish a slab to enable student
              purchases.
            </p>
          )}
          {rows.map((row) => (
            <article key={row.id} className="astra-work p-4">
              <h3 className="font-bold">
                {row.exam} · {row.title}
              </h3>
              <p>
                {row.min_questions}–{row.max_questions} questions ·{" "}
                {money(row.price_paise)} per paper
              </p>
              <p>{row.active ? "Published" : "Hidden from students"}</p>
              <div className="flex gap-2 mt-3">
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => {
                    setEditing(row.id);
                    setForm({ ...row, price: String(row.price_paise / 100) });
                  }}
                >
                  Edit
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => setDeleting(row)}
                >
                  Delete
                </Button>
              </div>
              {deleting?.id === row.id && (
                <div role="alert" className="mt-3">
                  <p>
                    Remove “{row.title}” from pricing? Existing purchases remain
                    available.
                  </p>
                  <Button
                    disabled={busy}
                    onClick={() =>
                      void perform(async () => {
                        await api.delete(`/exam-papers/admin/slabs/${row.id}`);
                        setDeleting(undefined);
                        if (editing === row.id) {
                          setEditing(undefined);
                          setForm(empty);
                        }
                      })
                    }
                  >
                    Confirm deletion
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setDeleting(undefined)}
                  >
                    Keep slab
                  </Button>
                </div>
              )}
            </article>
          ))}
        </section>
      </div>
    </PageLayout>
  );
}
