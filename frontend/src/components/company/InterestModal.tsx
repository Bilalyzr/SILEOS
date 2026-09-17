import { useState } from 'react'
import toast from 'react-hot-toast'
import { companyAPI, CandidateBrowseItem } from '@/api/company'

interface Props {
  candidate: CandidateBrowseItem
  onClose: () => void
  onSent: () => void
}

export function InterestModal({ candidate, onClose, onSent }: Props) {
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const send = async () => {
    if (message.trim().length < 10) {
      toast.error('Please write at least a short message (10+ chars)')
      return
    }
    setSubmitting(true)
    try {
      await companyAPI.expressInterest(candidate.user_id, message.trim())
      toast.success(`Interest sent to ${candidate.display_name}`)
      onSent()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to send interest')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-xl font-bold text-slate-900 mb-1">
          Express interest in {candidate.display_name}
        </h3>
        <p className="text-sm text-slate-600 mb-4">
          Write a short message — they will accept or decline. On accept, their
          email and phone will be revealed to you.
        </p>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={6}
          placeholder="Hi — we saw your profile and would love to talk about a role at our startup…"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md border border-slate-300 text-slate-700"
          >
            Cancel
          </button>
          <button
            onClick={send}
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold"
          >
            {submitting ? 'Sending…' : 'Send interest'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default InterestModal
