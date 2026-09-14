// Vite plugin to add build timestamp for cache busting
export function versionPlugin() {
  const timestamp = Date.now()
  const version = timestamp.toString(36)

  return {
    name: 'version-plugin',
    transformIndexHtml: {
      order: 'post',
      handler(html) {
        const versionMeta = `<meta name="app-version" content="${version}" />`
        if (html.includes('name="app-version"')) {
          html = html.replace(/<meta name="app-version"[^>]*>/, versionMeta)
        } else {
          html = html.replace('<meta http-equiv="Cache-Control"', `${versionMeta}\n    <meta http-equiv="Cache-Control"`)
        }
        console.log(`\n✓ Build version: ${version} (timestamp: ${timestamp})`)
        return html
      }
    }
  }
}
