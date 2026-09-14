/**
 * LessonPreviewModal (2026-09-05): the public "try before you enrol" popup.
 * Loads GET /courses/{id}/lessons/{lid}/preview (works logged-out for lessons
 * the instructor marked as public preview) and plays the REAL lesson — video,
 * 3D model, virtual lab, learning game, H5P or text — inside a dark glass
 * dialog with an enrol call-to-action. Locked lessons get the 403 hint, never
 * a blank player.
 */
import * as React from 'react'
import { Link } from 'react-router-dom'
import { Lock, Sparkles } from 'lucide-react'
import { api } from '@/api/axios'
import { track } from '@/api/funnel'
import { GlassDialog } from '@/components/ui/dialog'
import { VideoPlayer } from '@/components/video/video-player'
import { ThreeDViewer } from '@/components/three-d/ThreeDViewer'
import { VirtualLabEmbed } from '@/components/labs/VirtualLabEmbed'
import { GamePlayer } from '@/components/games/GamePlayer'
import { H5PLesson } from '@/components/h5p/H5PLesson'

export interface PreviewLesson {
  id: number; title: string; content: string; video_url: string; youtube_url?: string
  lesson_content_type: string; three_d_model_id?: number | null; virtual_lab_sim?: string | null
  game_id?: number | null; h5p_public_id?: string | null; is_public_preview?: boolean
}

const TYPE_LABEL: Record<string, string> = {
  video: 'Video lesson', three_d: '3D model', virtual_lab: 'Virtual lab', game: 'Learning game', h5p: 'Interactive', geogebra: 'GeoGebra', text: 'Reading',
}

export function LessonPreviewModal({ courseId, lessonId, lessonTitle, open, onClose, isEnrolled, enrolHref }: {
  courseId: number; lessonId: number | null; lessonTitle?: string; open: boolean; onClose: () => void
  isEnrolled?: boolean; enrolHref?: string
}) {
  const [lesson, setLesson] = React.useState<PreviewLesson | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(false)

  React.useEffect(() => {
    if (!open || !lessonId) return
    let cancelled = false
    setLesson(null); setError(null); setLoading(true)
    track('preview_open', courseId, { lesson_id: lessonId })   // R1 funnel
    api.get(`/courses/${courseId}/lessons/${lessonId}/preview`)
      .then((r) => { if (!cancelled) setLesson(r.data) })
      .catch((e) => { if (!cancelled) setError(e?.response?.data?.detail || 'This lesson cannot be previewed') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [open, courseId, lessonId])

  const type = lesson?.lesson_content_type || 'video'
  const src = lesson?.video_url || lesson?.youtube_url || ''

  return (
    <GlassDialog open={open} onOpenChange={(o) => { if (!o) onClose() }} size="xl" tone="dark"
      eyebrow={lesson?.is_public_preview ? 'Public preview' : 'Lesson'} title={lesson?.title || lessonTitle || 'Lesson preview'}
      description={lesson ? TYPE_LABEL[type] || type : undefined} data-testid="lesson-preview-modal"
      actions={!isEnrolled && (
        <>
          <span className="text-xs text-white/60 self-center mr-auto flex items-center gap-1"><Sparkles className="h-3.5 w-3.5" /> Free previews are the instructor's pick — enrol to unlock the whole course.</span>
          <Link to={enrolHref || `/checkout/${courseId}`} className="si-btn-primary">Enrol to unlock everything</Link>
        </>
      )}>
      {loading && <p className="text-sm text-white/70 py-10 text-center">Loading preview…</p>}
      {error && (
        <div className="py-10 text-center" role="alert">
          <Lock className="h-8 w-8 mx-auto text-orange-300 mb-2" />
          <p className="text-white/90">{error}</p>
        </div>
      )}
      {lesson && !error && (
        <div className="space-y-3">
          {type === 'video' || type === 'text' ? (
            src ? (
              <div className="aspect-video max-h-[70vh] bg-black rounded-xl overflow-hidden"><VideoPlayer src={src} title={lesson.title} controls /></div>
            ) : null
          ) : type === 'three_d' && lesson.three_d_model_id ? (
            <div className="rounded-xl overflow-hidden bg-white/95 text-gray-900 p-2"><ThreeDViewer modelId={lesson.three_d_model_id} height={420} description={lesson.content || undefined} /></div>
          ) : type === 'virtual_lab' && lesson.virtual_lab_sim ? (
            <div className="rounded-xl overflow-hidden bg-white/95 text-gray-900 p-2"><VirtualLabEmbed sim={lesson.virtual_lab_sim} title={lesson.title} previewOnly /></div>
          ) : type === 'game' && lesson.game_id ? (
            <div className="rounded-xl overflow-hidden bg-white/95 text-gray-900 p-2"><GamePlayer gameId={lesson.game_id} previewOnly /></div>
          ) : type === 'h5p' && lesson.h5p_public_id ? (
            <div className="rounded-xl overflow-hidden bg-white/95 text-gray-900 p-2"><H5PLesson contentId={lesson.h5p_public_id} title={lesson.title} previewOnly /></div>
          ) : (
            <p className="text-sm text-white/70">This lesson type opens inside the course player after enrolment.</p>
          )}
          {lesson.content && type !== 'three_d' && (
            // Text lessons ARE the content — give them the full reading height; for
            // video/lab/game lessons the text is the supporting note underneath.
            <div className={`glass-panel-dark rounded-xl p-4 text-sm leading-relaxed text-white/90 whitespace-pre-wrap overflow-y-auto ${!src && (type === 'text' || type === 'video') ? 'max-h-[65vh] text-base' : 'max-h-48'}`} data-testid="preview-text">
              {lesson.content.replace(/<br\s*\/?>/gi, '\n').replace(/<\/p>/gi, '\n\n').replace(/<[^>]+>/g, '').trim()}
            </div>
          )}
        </div>
      )}
    </GlassDialog>
  )
}

export default LessonPreviewModal
