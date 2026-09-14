

// Student blog create/edit page.
//
// App.tsx and the student dashboard nav ("Write Blog" -> /student/blog/create)
// referenced `@/pages/student/blog-create`, but the file was never committed,
// which broke the production Vite build (ENOENT on this module).
//
// The blog editing UI is identical for every author role, so we reuse the
// shared BlogEditorPage. Role-specific behaviour (e.g. the post-save redirect)
// is handled inside BlogEditorPage based on the logged-in user's role.
export { BlogEditorPage as StudentBlogCreate } from '@/pages/instructor/blog-editor'
