import { useParams } from 'react-router-dom'
import { CodingWorkspace } from '@/components/coding/CodingWorkspace'

export default function CodingWorkspacePage() {
  const { slug = '' } = useParams()
  return <CodingWorkspace slug={slug} />
}
