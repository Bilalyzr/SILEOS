import { PageLayout, PageHeader } from "@/components/design-system/PageLayout";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "@/api/axios";

export interface StudentAdminMessage {
  id: number;
  sender_name: string;
  subject: string;
  body: string;
  sent_at: string;
  read_at: string | null;
}

export function StudentMessagesPage() {
  const [messages, setMessages] = useState<StudentAdminMessage[]>([]);
  const [loading, setLoading] = useState(true);

  const loadMessages = async () => {
    setLoading(true);
    try {
      const res = await api.get<StudentAdminMessage[]>(
        "/admin/messages/my-messages",
      );
      setMessages(res.data);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load messages");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
  }, []);

  return (
    <PageLayout
      header={
        <PageHeader>
          <h1 className="text-2xl font-bold text-slate-900">Messages</h1>
          <p className="text-sm text-slate-600 mt-1">
            Announcements and updates from SashaInfinity admin
          </p>
        </PageHeader>
      }
      className="rd-screen rd-screen-dashboard-messages"
    >
      {loading ? (
        <div className="py-10 text-center text-slate-500">Loading…</div>
      ) : messages.length === 0 ? (
        <div
          className="py-16 text-center text-slate-500 bg-white rounded-xl border border-slate-200"
          data-glass="content"
        >
          No messages yet
        </div>
      ) : (
        <ul className="space-y-4">
          {messages.map((msg) => (
            <li
              key={msg.id}
              className={`bg-white rounded-xl border p-5 shadow-sm ${
                !msg.read_at
                  ? "border-l-4 border-l-indigo-600"
                  : "border-slate-200"
              }`}
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <div className="font-semibold text-slate-900">
                    {msg.subject}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    From: {msg.sender_name} ·{" "}
                    {new Date(msg.sent_at).toLocaleString()}
                  </div>
                </div>
                {!msg.read_at && (
                  <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-medium rounded">
                    New
                  </span>
                )}
              </div>
              <div className="text-sm text-slate-700 whitespace-pre-wrap">
                {msg.body}
              </div>
            </li>
          ))}
        </ul>
      )}
    </PageLayout>
  );
}

export default StudentMessagesPage;
