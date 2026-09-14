/**
 * Ebook detail — public data + per-user `owned` flag from the backend
 * (which already varies cache headers so the flag can't leak through a
 * shared edge). Buy = payments create-order with ebook_id. Free ebooks
 * grant instantly; paid ones open the gateway flow (in local dev without
 * Razorpay keys the API says so and we surface it honestly).
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, BookOpen, Download, FileText, ShoppingBag } from 'lucide-react'
import toast from 'react-hot-toast'
import { EBOOK_CATEGORY_LABELS, libraryAPI, type Ebook } from '@/api/library'
import { PriceTag } from './library'
import { PageLayout } from '@/components/design-system/PageLayout'
import { PageBanner } from '@/components/design-system/PageBanner'

export default function LibraryDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const [ebook, setEbook] = useState<Ebook | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [buying, setBuying] = useState(false)

  const reload = () => {
    if (!slug) return
    libraryAPI
      .detail(slug)
      .then((d) => { setEbook(d); setError(null) })
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load'))
      .finally(() => setLoading(false))
  }
  useEffect(reload, [slug])

  async function buy() {
    if (!ebook) return
    setBuying(true)
    try {
      const res = await libraryAPI.buy(ebook)
      if (res.requires_payment === false || res.granted) {
        toast.success('Added to your library!')
      } else if (res.order_id) {
        toast.success('Order created — complete the payment to unlock the download')
      } else {
        toast.success('Purchase recorded')
      }
      reload()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Purchase failed')
    } finally {
      setBuying(false)
    }
  }

  if (loading) {
    return <div className="max-w-4xl mx-auto px-4 py-8"><div className="h-72 rounded-xl bg-gray-100 animate-pulse" /></div>
  }
  if (error || !ebook) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <p role="alert" className="text-red-600 text-sm">{error ?? 'Not found'}</p>
        <Link to="/library" className="text-blue-600 text-sm hover:underline mt-2 inline-block">← Back to Library</Link>
      </div>
    )
  }

  return (
    <PageLayout
      className="rd-screen rd-screen-library-detail"
      header={
        <PageBanner
          eyebrow={EBOOK_CATEGORY_LABELS[ebook.category] ?? ebook.category}
          title={ebook.title}
          description={ebook.description.slice(0, 220)}
          image={ebook.cover_image || undefined}
          share
          shareUrl={`${window.location.origin}/library/${ebook.slug}`}
          shareDescription={ebook.description.slice(0, 160)}
        />
      }
    >
      <Link to="/library" className="text-sm text-gray-500 hover:text-gray-800 inline-flex items-center gap-1 mb-6">
        <ArrowLeft className="h-4 w-4" /> Back to Library
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="rounded-xl overflow-hidden border border-gray-200 bg-gradient-to-br from-blue-50 to-indigo-100 h-64 flex items-center justify-center">
          {ebook.cover_image ? (
            <img src={ebook.cover_image} alt="" className="h-full w-full object-cover" />
          ) : (
            <BookOpen className="h-16 w-16 text-blue-400" aria-hidden />
          )}
        </div>

        <div className="md:col-span-2">
          <span className="text-xs font-semibold bg-blue-50 text-blue-700 px-2 py-1 rounded-full">
            {EBOOK_CATEGORY_LABELS[ebook.category] ?? ebook.category}
          </span>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">{ebook.title}</h1>
          {ebook.course_title && (
            <p className="text-sm text-gray-500 mt-1">
              Companion to <span className="font-medium">{ebook.course_title}</span>
            </p>
          )}
          <p className="text-gray-700 mt-4 whitespace-pre-line">{ebook.description}</p>

          {ebook.concept_tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {ebook.concept_tags.map((t) => (
                <span key={t} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">{t}</span>
              ))}
            </div>
          )}

          <div className="flex items-center gap-4 mt-6 text-sm text-gray-500">
            {ebook.page_count ? <span>{ebook.page_count} pages</span> : null}
            {ebook.file_size_bytes ? <span>{(ebook.file_size_bytes / 1048576).toFixed(1)} MB</span> : null}
          </div>

          <div className="flex flex-wrap items-center gap-3 mt-8">
            <PriceTag ebook={ebook} />
            {ebook.owned ? (
              <button
                onClick={() => libraryAPI.download(ebook.id)}
                disabled={!ebook.has_file}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-40"
              >
                <Download className="h-4 w-4" /> {ebook.has_file ? 'Download' : 'File coming soon'}
              </button>
            ) : (
              <button
                onClick={buy}
                disabled={buying || !ebook.has_file}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-40"
              >
                <ShoppingBag className="h-4 w-4" />
                {buying ? 'Processing…' : ebook.effective_price_inr === 0 ? 'Get for FREE' : `Buy · ₹${ebook.effective_price_inr}`}
              </button>
            )}
            {ebook.has_sample && (
              <button
                onClick={() => libraryAPI.downloadSample(ebook.id)}
                className="inline-flex items-center gap-2 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:border-blue-400"
              >
                <FileText className="h-4 w-4" /> Free sample
              </button>
            )}
          </div>

          {ebook.owned && (
            <p className="text-xs text-emerald-700 mt-3">
              ✓ In your library — <Link to="/my-library" className="underline">go to My Library</Link>
            </p>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
