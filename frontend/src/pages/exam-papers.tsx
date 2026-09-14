import { useCallback, useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import { api } from "@/api/axios";
import { ensureRazorpayLoaded } from "@/api/internship";
import { examAPI, money, paperError, type ExamPaper } from "@/api/exam-papers";
import { PageLayout } from "@/components/design-system/PageLayout";
import { PageBanner } from "@/components/design-system/PageBanner";
import { ShareButton } from "@/components/ui/share-button";
import { Button } from "@/components/ui/button";

export default function ExamPapers() {
  const [pricing, setPricing] =
    useState<Awaited<ReturnType<typeof examAPI.pricing>>>();
  const [papers, setPapers] = useState<ExamPaper[]>([]);
  const [selected, setSelected] = useState<ExamPaper>();
  const [exam, setExam] = useState("JEE");
  const [count, setCount] = useState(10);
  const [topic, setTopic] = useState("");
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [answers, setAnswers] = useState(false);
  const reload = useCallback(async () => {
    try {
      const [p, rows] = await Promise.all([examAPI.pricing(), examAPI.list()]);
      setPricing(p);
      setPapers(rows);
      setError("");
    } catch (e) {
      setError(paperError(e));
    }
  }, []);
  useEffect(() => {
    void reload();
    window.addEventListener("focus", reload);
    return () => window.removeEventListener("focus", reload);
  }, [reload]);
  useEffect(() => {
    if (!selected || selected.status !== "generating") return;
    let live = true;
    const timer = window.setInterval(() => {
      examAPI
        .get(selected.id)
        .then((p) => {
          if (live) {
            setSelected(p);
            if (p.status !== "generating") void reload();
          }
        })
        .catch(() => {
          if (live)
            setError(
              "Connection interrupted. Your paper stays saved; refresh to check progress.",
            );
        });
    }, 4000);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [selected, reload]);
  const slab = pricing?.slabs.find(
    (s) =>
      s.exam === exam && count >= s.min_questions && count <= s.max_questions,
  );
  const staff = pricing?.staff_access;
  const generate = async (paper: ExamPaper) => {
    setSelected(await examAPI.generate(paper.id));
    await reload();
  };
  const perform = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(paperError(e));
    } finally {
      setBusy(false);
    }
  };
  const create = async () => {
    if (!staff) await ensureRazorpayLoaded();
    const { data } = await api.post("/exam-papers", {
      exam,
      count,
      topic,
      source_text: staff ? source : "",
    });
    setSelected(data.paper);
    await reload();
    if (!data.checkout) {
      await generate(data.paper);
      return;
    }
    await new Promise<void>((resolve, reject) => {
      const checkout = new (window as any).Razorpay({
        ...data.checkout,
        name: "SashaInfinity",
        description: `${exam} · ${count} practice questions`,
        handler: async (response: any) => {
          try {
            const verified = await api.post(
              `/exam-papers/${data.paper.id}/verify`,
              response,
            );
            await generate(verified.data);
            resolve();
          } catch (e) {
            reject(e);
          }
        },
        modal: {
          ondismiss: () => {
            toast("Checkout closed. Use Check payment if money was deducted.");
            resolve();
          },
        },
        theme: { color: "#F47B20" },
      });
      checkout.on("payment.failed", () => {
        setError(
          "Payment did not complete. If charged, use Check payment before trying another purchase.",
        );
        resolve();
      });
      checkout.open();
    });
  };
  if (!pricing)
    return (
      <PageLayout
        header={
          <PageBanner
            eyebrow="Assessment studio"
            title="Practice papers"
            description="Build a focused JEE or NEET practice set and return to your saved work whenever you need it."
          />
        }
      >
        <div className="astra-work p-5" role={error ? "alert" : "status"}>
          {error || "Loading your paper workspace…"}
          {error && <Button onClick={() => void reload()}>Try again</Button>}
        </div>
      </PageLayout>
    );
  return (
    <PageLayout
      className="exam-workspace"
      header={
        <PageBanner
          eyebrow="Assessment studio"
          title="Practice papers"
          description="Build a focused JEE or NEET practice set. Your saved paper stays available after generation."
          share
          shareTitle="Build a focused practice paper"
          shareDescription="Create JEE and NEET practice sets in the SashaInfinity assessment studio."
        />
      }
    >
      {error && (
        <div role="alert" className="astra-work p-4 mb-4 text-red-800">
          {error}{" "}
          <Button variant="outline" onClick={() => void reload()}>
            Refresh
          </Button>
        </div>
      )}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(260px,0.65fr)] print:hidden">
        <form
          className="astra-work p-5 space-y-4 min-w-0"
          onSubmit={(e) => {
            e.preventDefault();
            void perform(create);
          }}
        >
          <h2 className="text-xl font-bold">
            {staff
              ? "Create from your teaching material"
              : "Choose your practice set"}
          </h2>
          <p>
            {staff
              ? "Teaching staff create papers without payment. Generated questions enter your question bank as drafts for review."
              : "One payment creates one paper. Failed generation can be retried without another payment."}
          </p>
          {pricing && !pricing.generation_available && (
            <p role="status">
              Generation is temporarily unavailable. Checkout will reopen when
              the service is ready.
            </p>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <label>
              Exam
              <select
                className="w-full"
                value={exam}
                onChange={(e) => setExam(e.target.value)}
              >
                <option>JEE</option>
                <option>NEET</option>
              </select>
            </label>
            <label>
              Questions
              <input
                className="w-full"
                type="number"
                min={5}
                max={180}
                required
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              />
            </label>
          </div>
          <label className="block">
            Topic or chapter
            <input
              className="w-full"
              value={topic}
              maxLength={500}
              placeholder="For example, rotational motion"
              onChange={(e) => setTopic(e.target.value)}
            />
          </label>
          {staff ? (
            <div className="space-y-3">
              <label className="block">
                Import source text (PDF, TXT or MD, up to 10 MB)
                <input
                  className="block w-full"
                  type="file"
                  accept=".pdf,.txt,.md"
                  disabled={busy}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    e.target.value = "";
                    if (!file) return;
                    if (file.size > 10 * 1024 * 1024) {
                      setError("Choose a file up to 10 MB.");
                      return;
                    }
                    void perform(async () => {
                      const form = new FormData();
                      form.append("file", file);
                      const { data } = await api.post(
                        "/exam-papers/sources",
                        form,
                      );
                      setSource(data.text);
                      toast.success("Source imported. Review the text below.");
                    });
                  }}
                />
              </label>
              <label className="block">
                Source text
                <textarea
                  className="w-full"
                  rows={8}
                  maxLength={80000}
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  placeholder="Paste teaching notes or review imported PDF text."
                />
              </label>
              <p className="text-sm">
                {source.length.toLocaleString()} / 80,000 characters. Upload
                replaces the current source text. Scanned PDFs need readable
                text first.
              </p>
            </div>
          ) : (
            <div className="astra-content p-4 space-y-3">
              <h3 className="font-bold">Available {exam} pricing</h3>
              {pricing?.slabs
                .filter((s) => s.exam === exam)
                .map((s) => (
                  <button
                    type="button"
                    key={s.id}
                    className={`block text-left w-full p-3 rounded-xl border ${slab?.id === s.id ? "border-orange-500" : "border-slate-200"}`}
                    onClick={() => setCount(s.min_questions)}
                  >
                    <strong>{s.title}</strong> · {s.min_questions}–
                    {s.max_questions} questions · {money(s.price_paise)}
                  </button>
                ))}
              {pricing && !pricing.slabs.some((s) => s.exam === exam) && (
                <p>The admin has not published pricing for {exam} yet.</p>
              )}
              {!slab && <p>Select a count within an available range.</p>}
            </div>
          )}
          <Button
            type="submit"
            disabled={
              busy || !pricing?.generation_available || (!staff && !slab)
            }
          >
            {busy
              ? "Working…"
              : staff
                ? "Generate paper"
                : slab
                  ? `Pay ${money(slab.price_paise)} & generate`
                  : "Pricing unavailable"}
          </Button>
        </form>
        <section className="astra-content p-5 min-w-0">
          <h2 className="text-xl font-bold mb-3">Your papers</h2>
          <div className="space-y-2 max-h-[600px] overflow-auto">
            {papers.map((p) => (
              <button
                key={p.id}
                type="button"
                className="w-full text-left rounded-xl border border-slate-200 p-3"
                onClick={() =>
                  void perform(async () => {
                    setSelected(await examAPI.get(p.id));
                    setAnswers(false);
                  })
                }
              >
                <strong className="block break-words">{p.title}</strong>
                <span>
                  {p.question_count} questions · {p.status.replace(/_/g, " ")}
                </span>
              </button>
            ))}
            {!papers.length && <p>Your generated papers will appear here.</p>}
          </div>
        </section>
      </div>
      {selected && (
        <section
          className="astra-work p-5 mt-6 exam-paper-result"
          aria-live="polite"
        >
          <h2 className="text-2xl font-bold break-words">{selected.title}</h2>
          <p>
            {selected.question_count} questions ·{" "}
            {selected.status.replace(/_/g, " ")}
          </p>
          {selected.error && <p role="alert">{selected.error}</p>}
          {selected.status === "generating" && (
            <p>
              Drafting and validating questions. You can leave this page and
              return to your saved paper.
            </p>
          )}
          <div className="flex flex-wrap gap-3 my-4 print:hidden">
            {["ready", "failed"].includes(selected.status) && (
              <Button
                disabled={busy}
                onClick={() => void perform(() => generate(selected))}
              >
                {selected.status === "failed"
                  ? "Retry without paying again"
                  : "Generate this paper"}
              </Button>
            )}
            {selected.status === "awaiting_payment" && (
              <Button
                disabled={busy}
                onClick={() =>
                  void perform(async () => {
                    const { data } = await api.post(
                      `/exam-papers/${selected.id}/reconcile`,
                    );
                    setSelected(data);
                    await reload();
                    if (data.status === "awaiting_payment")
                      toast("No captured payment found yet.");
                  })
                }
              >
                Check payment
              </Button>
            )}
            {selected.status === "completed" && (
              <>
                <Button variant="outline" onClick={() => setAnswers(!answers)}>
                  {answers ? "Hide answers" : "Show answers"}
                </Button>
                <Button onClick={() => window.print()}>Print / Save PDF</Button>
                <ShareButton
                  url={`${window.location.origin}/exam-papers`}
                  title={selected.title}
                  description={`${selected.question_count} focused ${selected.exam} practice questions created with SashaInfinity.`}
                />
                {selected.bank_id && (
                  <span>
                    Saved as drafts in question bank #{selected.bank_id}. Import
                    through your quiz builder for review.
                  </span>
                )}
              </>
            )}
          </div>
          {selected.questions?.map((q, i) => (
            <article
              key={i}
              className="border-t border-slate-200 py-5 break-inside-avoid"
            >
              <h3 className="font-semibold whitespace-pre-wrap">
                {i + 1}. {q.question_title}
              </h3>
              {q.options && (
                <ol className="list-[upper-alpha] pl-6 space-y-2 mt-3">
                  {q.options.map((o, n) => (
                    <li key={n}>{o}</li>
                  ))}
                </ol>
              )}
              {answers && (
                <div className="mt-3">
                  <strong>
                    Answer:{" "}
                    {q.options && typeof q.correct_answer === "number"
                      ? q.options[q.correct_answer]
                      : String(q.correct_answer)}
                  </strong>
                  <p className="whitespace-pre-wrap">{q.answer_explanation}</p>
                </div>
              )}
            </article>
          ))}
          {selected.status === "completed" && (
            <p className="text-sm mt-4">
              AI-generated practice material. Review answers before graded use.
              This is not an official examination paper.
            </p>
          )}
        </section>
      )}
    </PageLayout>
  );
}
