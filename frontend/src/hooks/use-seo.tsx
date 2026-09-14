import { useEffect } from 'react'
import { Helmet } from 'react-helmet-async'

export interface SEOProps {
  title?: string
  description?: string
  image?: string | null
  url?: string
  type?: 'website' | 'article'
  author?: string
  publishedTime?: string
  modifiedTime?: string
}

const DEFAULT_SEO = {
  title: 'SashaInfinity - Premium Technology Learning Platform',
  description: 'Master cutting-edge technologies with expert-led courses in full stack development, AI, cloud computing, and more. Advance your career with premium technology education.',
  image: 'https://sashainfinity.com/brand/share-default.png',
  type: 'website',
} satisfies SEOProps

/**
 * The canonical host. www.sashainfinity.com and lms.sashainfinity.com 301 to
 * it at the Cloudflare edge, so every SEO URL (canonical, og:url, og:image)
 * is built on the apex regardless of which host the visitor browsed in on.
 */
const SITE_ORIGIN = 'https://sashainfinity.com'

/**
 * Convert relative URL to absolute URL on the canonical host
 */
const toAbsoluteUrl = (url: string | null | undefined): string | undefined => {
  if (!url) return undefined
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  // Handle relative URLs like /uploads/...
  return `${SITE_ORIGIN}${url.startsWith('/') ? '' : '/'}${url}`
}

/**
 * Hook to manage Open Graph and Twitter Card meta tags dynamically
 * This helps with social media sharing previews
 *
 * @example
 * ```tsx
 * useSEO({
 *   title: course.post_title,
 *   description: course.post_excerpt,
 *   image: course.course_thumbnail,
 *   url: window.location.href,
 * })
 * ```
 */
export function useSEO(props: SEOProps = {}) {
  const {
    title = DEFAULT_SEO.title,
    description = DEFAULT_SEO.description,
    image = DEFAULT_SEO.image,
    url,
    type = DEFAULT_SEO.type,
    author,
    publishedTime,
    modifiedTime,
  } = props

  // Convert relative URLs to absolute for social media crawlers
  const absoluteImage = toAbsoluteUrl(image) || DEFAULT_SEO.image

  // Canonical page URL: caller-provided, or derived from the current route on
  // the canonical host. Query strings are dropped — they don't change content.
  const pageUrl = url ?? `${SITE_ORIGIN}${window.location.pathname}`

  useEffect(() => {
    // Set document title
    document.title = title

    // Update or create meta tags
    const metaTags: Array<{ property?: string; name?: string; content: string }> = [
      // Basic meta
      { name: 'description', content: description },

      // Open Graph
      { property: 'og:title', content: title },
      { property: 'og:description', content: description },
      { property: 'og:image', content: absoluteImage },
      { property: 'og:type', content: type },
      { property: 'og:url', content: pageUrl },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: title },
      { name: 'twitter:description', content: description },
      { name: 'twitter:image', content: absoluteImage },
      { name: 'twitter:url', content: pageUrl },
    ]

    // Add article-specific tags
    if (type === 'article') {
      if (author) {
        metaTags.push({ property: 'article:author', content: author })
      }
      if (publishedTime) {
        metaTags.push({ property: 'article:published_time', content: publishedTime })
      }
      if (modifiedTime) {
        metaTags.push({ property: 'article:modified_time', content: modifiedTime })
      }
    }

    // Create or update meta tags
    metaTags.forEach(({ property, name, content }) => {
      const selector = property ? `meta[property="${property}"]` : `meta[name="${name}"]`
      let meta = document.querySelector(selector) as HTMLMetaElement

      if (!meta) {
        meta = document.createElement('meta')
        if (property) meta.setAttribute('property', property)
        if (name) meta.setAttribute('name', name)
        document.head.appendChild(meta)
      }

      meta.setAttribute('content', content)
    })

    // Update or create the canonical link — index.html ships a static one that
    // must be rewritten per route, or every page would declare itself a
    // duplicate of the homepage.
    let canonical = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.setAttribute('rel', 'canonical')
      document.head.appendChild(canonical)
    }
    canonical.setAttribute('href', pageUrl)

    // Cleanup function to reset to defaults when component unmounts
    return () => {
      document.title = DEFAULT_SEO.title
      const homeUrl = `${SITE_ORIGIN}/`
      const defaultMeta = [
        'description',
        'og:title',
        'og:description',
        'og:image',
        'og:type',
        'og:url',
        'article:author',
        'article:published_time',
        'article:modified_time',
        'twitter:card',
        'twitter:title',
        'twitter:description',
        'twitter:image',
        'twitter:url',
      ]

      defaultMeta.forEach((name) => {
        const selector = name.startsWith('og:') || name.startsWith('article:')
          ? `meta[property="${name}"]`
          : `meta[name="${name}"]`
        const meta = document.querySelector(selector)
        if (meta) {
          const defaultContent = name === 'og:url' || name === 'twitter:url'
            ? homeUrl
            : DEFAULT_SEO.description
          meta.setAttribute('content', defaultContent)
        }
      })

      const canonical = document.querySelector('link[rel="canonical"]')
      if (canonical) canonical.setAttribute('href', homeUrl)
    }
  }, [title, description, absoluteImage, pageUrl, type, author, publishedTime, modifiedTime])
}

/**
 * Component version for use with React Helmet for SSR support
 * Use this if you plan to add SSR in the future
 */
export function SEOHead({ title, description, image, url, type = 'website', author, publishedTime, modifiedTime }: SEOProps) {
  const fullTitle = title ? `${title} | SashaInfinity` : DEFAULT_SEO.title
  const fullDescription = description || DEFAULT_SEO.description
  const fullImage = toAbsoluteUrl(image) || DEFAULT_SEO.image

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={fullDescription} />

      {/* Open Graph / Facebook */}
      <meta property="og:type" content={type} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={fullDescription} />
      <meta property="og:image" content={fullImage} />
      {url && <meta property="og:url" content={url} />}

      {/* Article specific */}
      {type === 'article' && author && <meta property="article:author" content={author} />}
      {type === 'article' && publishedTime && <meta property="article:published_time" content={publishedTime} />}
      {type === 'article' && modifiedTime && <meta property="article:modified_time" content={modifiedTime} />}

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={fullDescription} />
      <meta name="twitter:image" content={fullImage} />
      {url && <meta name="twitter:url" content={url} />}
    </Helmet>
  )
}
