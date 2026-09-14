import { api } from './axios'

export interface Blog {
  id: number
  title: string
  slug: string
  status: 'draft' | 'published' | 'pending'
  category: string | null
  author_name: string
  views: number
  created_at: string
}

export interface BlogListResponse {
  blogs: Blog[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AdminBlogsParams {
  page?: number
  page_size?: number
  search?: string
  status?: 'draft' | 'published' | 'pending'
  category?: string
}

export interface CreateBlogData {
  title: string
  excerpt: string
  content: string
  category?: string
  tags?: string[]
  featured_image?: string
  status?: 'draft' | 'published' | 'pending'
}

export interface UpdateBlogData {
  title?: string
  excerpt?: string
  content?: string
  category?: string
  tags?: string[]
  featured_image?: string
  status?: 'draft' | 'published' | 'pending'
}

/**
 * Get all blogs for admin management
 */
export const getAdminBlogs = async (params: AdminBlogsParams = {}): Promise<BlogListResponse> => {
  const response = await api.get('/admin/blogs', { params })
  return response.data
}

/**
 * Every distinct blog category. Deliberately independent of the list filters —
 * deriving the dropdown from the filtered page left only the selected category
 * in it.
 */
export const getAdminBlogCategories = async (): Promise<string[]> => {
  const response = await api.get('/admin/blogs/categories')
  return Array.isArray(response.data) ? response.data : []
}

/**
 * Update a blog
 */
export const updateBlog = async (id: number, data: UpdateBlogData): Promise<Blog> => {
  const response = await api.put(`/admin/blogs/${id}`, data)
  return response.data
}

/**
 * Delete a blog
 */
export const deleteBlog = async (id: number): Promise<void> => {
  await api.delete(`/admin/blogs/${id}`)
}

/**
 * Update blog status (publish/unpublish)
 */
export const updateBlogStatus = async (id: number, status: 'draft' | 'published' | 'pending'): Promise<Blog> => {
  const response = await api.patch(`/admin/blogs/${id}/status`, { status })
  return response.data
}

/**
 * Bulk delete blogs
 */
export const bulkDeleteBlogs = async (ids: number[]): Promise<void> => {
  await api.post('/admin/blogs/bulk-delete', { ids })
}
