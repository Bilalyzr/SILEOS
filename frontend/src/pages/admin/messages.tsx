import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  adminMessagesAPI,
  CompanyRecipient,
  StudentRecipient,
  AdminMessage,
} from "@/api/admin-messages";
import { Send, Users, Building2 } from "lucide-react";

type RecipientType = "individual" | "company";

export function AdminMessagesPage() {
  const [tab, setTab] = useState<RecipientType>("individual");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState<AdminMessage[]>([]);

  const [students, setStudents] = useState<StudentRecipient[]>([]);
  const [companies, setCompanies] = useState<CompanyRecipient[]>([]);
  const [search, setSearch] = useState("");

  const loadRecipients = async () => {
    try {
      const [s, c] = await Promise.all([
        adminMessagesAPI.getStudentRecipients(),
        adminMessagesAPI.getCompanyRecipients(),
      ]);
      setStudents(s);
      setCompanies(c);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load recipients");
    }
  };

  const loadSent = async () => {
    try {
      setSent(await adminMessagesAPI.getSent());
    } catch (e: any) {
      console.error("Failed to load sent messages", e);
    }
  };

  useEffect(() => {
    loadRecipients();
    loadSent();
  }, []);

  const filteredStudents = search
    ? students.filter(
        (s) =>
          s.name.toLowerCase().includes(search.toLowerCase()) ||
          s.email.toLowerCase().includes(search.toLowerCase()),
      )
    : students;

  const filteredCompanies = search
    ? companies.filter((c) =>
        c.name.toLowerCase().includes(search.toLowerCase()),
      )
    : companies;

  const toggleId = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const handleSend = async () => {
    if (!subject.trim() || !body.trim()) {
      return toast.error("Please enter subject and message");
    }
    if (selectedIds.length === 0) {
      return toast.error("Please select at least one recipient");
    }

    setLoading(true);
    try {
      const result = await adminMessagesAPI.bulkSend({
        recipient_type: tab === "individual" ? "user" : "company",
        recipient_ids: selectedIds,
        subject: subject.trim(),
        body: body.trim(),
      });
      // Report the email outcome separately — the in-app message always saves,
      // but the email is what the student actually notices.
      if (result.email_failed_count > 0) {
        toast.error(
          `Sent to ${result.sent_count} recipients, but ${result.email_failed_count} email${result.email_failed_count !== 1 ? "s" : ""} could not be delivered`,
        );
      } else {
        toast.success(
          `Sent and emailed to ${result.sent_count} recipient${result.sent_count !== 1 ? "s" : ""}${result.failed_count > 0 ? ` (${result.failed_count} skipped)` : ""}`,
        );
      }
      setSubject("");
      setBody("");
      setSelectedIds([]);
      loadSent();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-2xl font-bold text-slate-900">
            Send Messages to Students
          </h1>
          <p className="text-slate-600 mt-1">
            Send announcements to individual students or to all interns at a
            company.
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-admin-messages"
    >
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Compose */}
        <div className="lg:col-span-2 space-y-6">
          {/* Type tabs */}
          <div className="flex gap-2 border-b border-slate-200">
            <button
              onClick={() => {
                setTab("individual");
                setSelectedIds([]);
              }}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                tab === "individual"
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              <Users className="w-4 h-4 inline mr-2" />
              Individual Students
            </button>
            <button
              onClick={() => {
                setTab("company");
                setSelectedIds([]);
              }}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
                tab === "company"
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              }`}
            >
              <Building2 className="w-4 h-4 inline mr-2" />
              By Company
            </button>
          </div>

          {/* Search */}
          <div>
            <input
              type="text"
              placeholder={`Search ${tab === "individual" ? "students" : "companies"}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Recipient list */}
          <div
            className="bg-white rounded-xl border border-slate-200 max-h-80 overflow-y-auto"
            data-glass="work"
          >
            {tab === "individual" ? (
              filteredStudents.length === 0 ? (
                <div className="p-6 text-center text-slate-500">
                  No students found
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {filteredStudents.map((s) => (
                    <label
                      key={s.id}
                      className={`flex items-center gap-3 px-4 py-3 hover:bg-slate-50 cursor-pointer ${
                        selectedIds.includes(s.id) ? "bg-indigo-50" : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(s.id)}
                        onChange={() => toggleId(s.id)}
                        className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-slate-900 truncate">
                          {s.name}
                        </div>
                        <div className="text-xs text-slate-500 truncate">
                          {s.email}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )
            ) : filteredCompanies.length === 0 ? (
              <div className="p-6 text-center text-slate-500">
                No companies found
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {filteredCompanies.map((c) => (
                  <label
                    key={c.id}
                    className={`flex items-center gap-3 px-4 py-3 hover:bg-slate-50 cursor-pointer ${
                      selectedIds.includes(c.id) ? "bg-indigo-50" : ""
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(c.id)}
                      onChange={() => toggleId(c.id)}
                      className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-slate-900 truncate">
                        {c.name}
                      </div>
                      <div className="text-xs text-slate-500">
                        {c.industry} · {c.intern_count} intern
                        {c.intern_count !== 1 ? "s" : ""}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Message compose */}
          <div
            className="bg-white rounded-xl border border-slate-200 p-5 space-y-4"
            data-glass="work"
          >
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Subject
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Message subject..."
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Message
              </label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Type your message here..."
                rows={5}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="text-sm text-slate-500">
                {selectedIds.length}{" "}
                {tab === "individual" ? "student" : "company"}
                {selectedIds.length !== 1 ? "s" : ""} selected
                {tab === "company" && selectedIds.length > 0 && (
                  <span className="ml-2 text-slate-600">
                    (~
                    {selectedIds.reduce((sum, id) => {
                      const c = companies.find((x) => x.id === id);
                      return sum + (c?.intern_count || 0);
                    }, 0)}{" "}
                    interns)
                  </span>
                )}
              </div>
              <button
                onClick={handleSend}
                disabled={loading || selectedIds.length === 0}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-medium rounded-lg flex items-center gap-2 transition-colors"
              >
                <Send className="w-4 h-4" />
                {loading ? "Sending..." : "Send Message"}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Sent history */}
        <div className="lg:col-span-1">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Recently Sent
          </h2>
          <div
            className="bg-white rounded-xl border border-slate-200"
            data-glass="content"
          >
            {sent.length === 0 ? (
              <div className="p-6 text-center text-slate-500">
                No messages sent yet
              </div>
            ) : (
              <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                {sent.slice(0, 20).map((msg) => (
                  <div key={msg.id} className="p-4">
                    <div className="font-medium text-slate-900 text-sm">
                      {msg.subject}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      To: {msg.recipient_name}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-slate-400">
                        {new Date(msg.sent_at).toLocaleString()}
                      </span>
                      {msg.email_status && (
                        <span
                          className={`text-[11px] px-1.5 py-0.5 rounded-full font-medium ${
                            msg.email_status === "sent"
                              ? "bg-green-100 text-green-700"
                              : "bg-red-100 text-red-700"
                          }`}
                          title={
                            msg.email_status === "sent"
                              ? "Email delivered to the recipient"
                              : msg.email_status === "no_email"
                                ? "Recipient has no email address on file"
                                : "Email delivery failed"
                          }
                        >
                          {msg.email_status === "sent"
                            ? "Emailed"
                            : "Email failed"}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
}

export default AdminMessagesPage;
