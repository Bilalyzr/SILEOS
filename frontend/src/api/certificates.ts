import { api } from './axios'

export interface Certificate {
  id: number
  course_id: number
  course_title: string
  student_name: string
  instructor_name: string
  completion_date: string
  certificate_url: string
  verification_code: string
  issued_at: string
}

/**
 * Payload behind the "Share on LinkedIn" dialog. `share_url` points at the
 * backend's Open-Graph landing page whose og:image is the rendered
 * certificate — that is what LinkedIn turns into the post preview.
 */
export interface CertificateShareMeta {
  student_name: string
  course_title: string
  completion_label: string
  certificate_id: string
  share_url: string
  image_url: string
  verify_url: string
  caption: string
  hashtags: string[]
  company_page: string
  company_handle: string
  og_title: string
  og_description: string
  linkedin_share_url: string
  linkedin_fallback_url: string
}

/**
 * Legacy issued certificates stored their download path as `/certificates/<file>.pdf`,
 * which the backend now serves from `/certificate-files/`. Rewrite only those paths:
 * the API's current URL is an API route (`/api/v1/certificates/download-pdf/...`) that
 * also contains "/certificates/", and blindly replacing it would rewrite the route
 * itself into a 404.
 */
const normaliseCertificateUrl = (url: string): string => {
  if (!url) return url
  if (url.startsWith('/api/')) return url
  return url.replace('/certificates/', '/certificate-files/')
}

export const certificatesAPI = {
  // Get all user certificates
  getUserCertificates: async (): Promise<Certificate[]> => {
    const response = await api.get('/certificates')
    const certificates = response.data

    certificates.forEach((cert: Certificate) => {
      cert.certificate_url = normaliseCertificateUrl(cert.certificate_url)
    })

    return certificates
  },

  // Get specific certificate
  getCertificate: async (certificateId: number): Promise<Certificate> => {
    const response = await api.get(`/certificates/${certificateId}`)
    const cert = response.data

    cert.certificate_url = normaliseCertificateUrl(cert.certificate_url)

    return cert
  },

  // Generate certificate for a course
  generateCertificate: async (courseId: number): Promise<{
    certificate_id: number
    message: string
    certificate_url: string
  }> => {
    const response = await api.post(`/certificates/generate/${courseId}`, {}, {
      timeout: 30000  // 30 second timeout for certificate generation
    })
    return response.data
  },

  // Regenerate certificate for a course (deletes old and creates new)
  regenerateCertificate: async (courseId: number): Promise<{
    certificate_id: number
    message: string
    certificate_url: string
  }> => {
    const response = await api.post(`/certificates/regenerate/${courseId}`, {}, {
      timeout: 30000  // 30 second timeout for certificate regeneration
    })
    return response.data
  },

  // Get certificate by course ID
  getCertificateByCourse: async (courseId: number): Promise<Certificate | null> => {
    try {
      const certificates = await certificatesAPI.getUserCertificates()
      const cert = certificates.find(cert => cert.course_id === courseId) || null

      if (cert) {
        cert.certificate_url = normaliseCertificateUrl(cert.certificate_url)
      }

      return cert
    } catch (error) {
      console.error('Error fetching certificate:', error)
      return null
    }
  },

  // Download certificate
  downloadCertificate: async (certificateId: number): Promise<void> => {
    const response = await api.get(`/certificates/download/${certificateId}`, {
      responseType: 'blob'
    })

    // Create a blob URL and trigger download
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `certificate-${certificateId}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },

  // Share payload (caption + OG share URL + certificate image) for a certificate
  getShareMeta: async (
    secureCertificateId: string,
    certificateHash: string
  ): Promise<CertificateShareMeta> => {
    const response = await api.get(
      `/certificates/share-meta/${secureCertificateId}/${certificateHash}`
    )
    return response.data
  },

  // Verify certificate
  verifyCertificate: async (verificationCode: string): Promise<{
    valid: boolean
    student_name: string
    course_title: string
    instructor_name: string
    completion_date: string
    issued_at: string
    verification_code: string
  }> => {
    const response = await api.get(`/certificates/verify/${verificationCode}`)
    return response.data
  },

  // Issue 4: Resolve a certificate's public verification/share URL by its
  // numeric ID — the ID-based public link.
  getPublicUrl: async (certificateId: number): Promise<{
    certificate_id: number
    secure_certificate_id: string
    verification_hash: string
    public_url: string
    share_url: string
    certificate_url: string
    image_url: string
  }> => {
    const response = await api.get(`/certificates/public-url/${certificateId}`)
    return response.data
  }
}
