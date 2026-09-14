/**
 * Assignment API - Assignment management service
 */
import { api } from './axios'

export interface AssignmentData {
  id?: number
  title: string
  description: string
  instructions: string
  dueDate: string
  totalPoints: number
  allowedFileTypes: string[]
  maxFileSize: number
  maxFiles: number
  submissionType: 'text' | 'file' | 'both'
}

/**
 * Create a new assignment
 */
export const createAssignment = async (courseId: number, assignmentData: AssignmentData) => {
  const response = await api.post(
    `/courses/${courseId}/assignments`,
    assignmentData
  )
  return response.data
}

/**
 * Get assignment by ID
 */
export const getAssignment = async (courseId: number, assignmentId: number): Promise<AssignmentData> => {
  const response = await api.get(`/courses/${courseId}/assignments/${assignmentId}`)
  return response.data
}

/**
 * Update assignment
 */
export const updateAssignment = async (courseId: number, assignmentId: number, assignmentData: AssignmentData) => {
  const response = await api.put(
    `/courses/${courseId}/assignments/${assignmentId}`,
    assignmentData
  )
  return response.data
}

/**
 * Delete assignment
 */
export const deleteAssignment = async (courseId: number, assignmentId: number) => {
  const response = await api.delete(`/courses/${courseId}/assignments/${assignmentId}`)
  return response.data
}

/**
 * Submit assignment
 */
export const submitAssignment = async (assignmentId: number, submissionData: any) => {
  const response = await api.post(`/assignments/${assignmentId}/submit`, submissionData)
  return response.data
}

/**
 * Get assignment submissions (instructor only)
 */
export const getSubmissions = async (assignmentId: number) => {
  const response = await api.get(`/assignments/${assignmentId}/submissions`)
  return response.data
}

/**
 * Grade submission (instructor only)
 */
export const gradeSubmission = async (submissionId: number, gradeData: any) => {
  const response = await api.post(`/submissions/${submissionId}/grade`, gradeData)
  return response.data
}
