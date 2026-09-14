import React, { useState, useCallback, useRef, useEffect } from 'react'
import {
  Move,
  Type,
  Image,
  Calendar,
  BookOpen,
  User,
  Settings,
  PenTool as Signature,
  X
} from 'lucide-react'
import { TemplateElement, TemplateBackground, TemplateDimensions } from '@/api/admin'

interface TemplateBuilderProps {
  name: string
  description: string
  background: TemplateBackground
  dimensions: TemplateDimensions
  elements: TemplateElement[]
  orientation: 'landscape' | 'portrait'
  onChange: (data: {
    name: string
    description: string
    background: TemplateBackground
    dimensions: TemplateDimensions
    elements: TemplateElement[]
    orientation: 'landscape' | 'portrait'
  }) => void
  readOnly?: boolean
}

const TemplateBuilder: React.FC<TemplateBuilderProps> = ({
  name,
  description,
  background,
  dimensions,
  elements,
  orientation,
  onChange,
  readOnly = false
}) => {
  const [selectedElement, setSelectedElement] = useState<TemplateElement | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const canvasRef = useRef<HTMLDivElement>(null)

  // Element types that can be added
  const elementTypes = [
    { type: 'text' as const, label: 'Text', icon: Type },
    { type: 'student_name' as const, label: 'Student Name', icon: User },
    { type: 'course_name' as const, label: 'Course Name', icon: BookOpen },
    { type: 'date' as const, label: 'Completion Date', icon: Calendar },
    { type: 'image' as const, label: 'Image/Logo', icon: Image },
    { type: 'signature' as const, label: 'Signature', icon: Signature }
  ]

  const addElement = useCallback((type: TemplateElement['type']) => {
    const newElement: TemplateElement = {
      id: `element-${Date.now()}`,
      type,
      x: 100,
      y: 100,
      width: type === 'text' || type === 'student_name' || type === 'course_name' ? 300 : 100,
      height: type === 'text' || type === 'student_name' || type === 'course_name' ? 50 : 100,
      content: type === 'text' ? 'Sample Text' : undefined,
      font_size: 24,
      font_family: 'Arial',
      font_color: '#000000',
      font_weight: 'normal',
      text_align: 'left',
      z_index: elements.length,
      rotation: 0
    }

    onChange({
      name,
      description,
      background,
      dimensions,
      elements: [...elements, newElement],
      orientation
    })
    setSelectedElement(newElement)
  }, [elements, name, description, background, dimensions, orientation, onChange])

  const updateElement = useCallback((elementId: string, updates: Partial<TemplateElement>) => {
    const updatedElements = elements.map(el =>
      el.id === elementId ? { ...el, ...updates } : el
    )
    onChange({
      name,
      description,
      background,
      dimensions,
      elements: updatedElements,
      orientation
    })
  }, [elements, name, description, background, dimensions, orientation, onChange])

  const deleteElement = useCallback((elementId: string) => {
    const updatedElements = elements.filter(el => el.id !== elementId)
    onChange({
      name,
      description,
      background,
      dimensions,
      elements: updatedElements,
      orientation
    })
    if (selectedElement?.id === elementId) {
      setSelectedElement(null)
    }
  }, [elements, name, description, background, dimensions, orientation, selectedElement, onChange])

  const handleMouseDown = useCallback((e: React.MouseEvent, element: TemplateElement) => {
    if (readOnly) return
    e.stopPropagation()
    setIsDragging(true)
    setSelectedElement(element)

    const rect = (e.target as HTMLElement).getBoundingClientRect()
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    })
  }, [readOnly])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !selectedElement || !canvasRef.current) return

    const canvasRect = canvasRef.current.getBoundingClientRect()
    const x = Math.round(e.clientX - canvasRect.left - dragOffset.x)
    const y = Math.round(e.clientY - canvasRect.top - dragOffset.y)

    updateElement(selectedElement.id, { x, y })
  }, [isDragging, selectedElement, dragOffset, updateElement])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  const handleCanvasClick = useCallback((e: React.MouseEvent) => {
    if (e.target === canvasRef.current) {
      setSelectedElement(null)
    }
  }, [])

  useEffect(() => {
    document.addEventListener('mouseup', handleMouseUp)
    return () => document.removeEventListener('mouseup', handleMouseUp)
  }, [handleMouseUp])

  const renderElement = (element: TemplateElement) => {
    const isSelected = selectedElement?.id === element.id
    const baseStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${element.x}px`,
      top: `${element.y}px`,
      width: `${element.width}px`,
      height: `${element.height}px`,
      zIndex: element.z_index,
      cursor: readOnly ? 'default' : 'move',
      transform: element.rotation ? `rotate(${element.rotation}deg)` : undefined,
      border: isSelected ? '2px dashed #3b82f6' : '1px dashed transparent',
      minWidth: '50px',
      minHeight: '30px',
      boxSizing: 'border-box',
      // Ensure alignment relative to the canvas origin
      transformOrigin: 'top left'
    }

    const contentStyle: React.CSSProperties = {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: element.text_align === 'center' ? 'center' : element.text_align === 'right' ? 'flex-end' : 'flex-start',
      fontSize: `${element.font_size}px`,
      fontFamily: element.font_family,
      color: element.font_color,
      fontWeight: element.font_weight,
      backgroundColor: element.background_color || 'transparent',
      padding: '4px',
      overflow: 'hidden',
      wordBreak: 'break-word'
    }

    let content = null

    switch (element.type) {
      case 'text':
        content = <span style={contentStyle}>{element.content || 'Text'}</span>
        break
      case 'student_name':
        content = <span style={contentStyle}>Student Name</span>
        break
      case 'course_name':
        content = <span style={contentStyle}>Course Title</span>
        break
      case 'date':
        content = <span style={contentStyle}>January 1, 2025</span>
        break
      case 'image':
      case 'signature':
        content = (
          <div style={contentStyle}>
            {element.image_url ? (
              <img src={element.image_url} alt="" style={{ maxWidth: '100%', maxHeight: '100%' }} />
            ) : (
              <span className="text-gray-400 text-xs">No image</span>
            )}
          </div>
        )
        break
    }

    return (
      <div
        key={element.id}
        style={baseStyle}
        onMouseDown={(e) => handleMouseDown(e, element)}
        onClick={(e) => e.stopPropagation()}
      >
        {content}
        {!readOnly && isSelected && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              deleteElement(element.id)
            }}
            className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
          >
            <X size={14} />
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      {/* Canvas Area */}
      <div className="flex-1">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          {/* Toolbar */}
          {!readOnly && (
            <div className="flex flex-wrap items-center gap-2 mb-4 pb-4 border-b">
              {elementTypes.map(({ type, label, icon: Icon }) => (
                <button
                  key={type}
                  onClick={() => addElement(type)}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
                >
                  <Icon size={16} />
                  {label}
                </button>
              ))}
            </div>
          )}

          {/* Canvas - Fixed alignment using transform scale for responsive preview */}
          <div
            className="relative mx-auto border border-gray-300 shadow-lg overflow-hidden flex items-center justify-center bg-gray-100"
            style={{
              maxWidth: '100%',
              minHeight: '400px'
            }}
          >
            <div
              ref={canvasRef}
              className="relative overflow-hidden"
              style={{
                width: dimensions.width,
                height: dimensions.height,
                backgroundColor: background.type === 'color' ? background.value : '#ffffff',
                backgroundImage: background.type === 'image' && background.image_url
                  ? `url(${background.image_url})`
                  : undefined,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                transform: 'scale(1)',
                transformOrigin: 'top left'
              }}
              onMouseMove={handleMouseMove}
              onClick={handleCanvasClick}
            >
              {elements.map(renderElement)}
            </div>
          </div>

          {/* Canvas controls */}
          <div className="flex justify-between items-center mt-4 text-sm text-gray-600">
            <span>
              Size: {dimensions.width} x {dimensions.height}px
            </span>
            <span>
              {elements.length} element{elements.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>

      {/* Properties Panel */}
      <div className="w-full lg:w-80">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Settings size={18} />
            Properties
          </h3>

          {selectedElement ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Element Type
                </label>
                <input
                  type="text"
                  value={selectedElement.type}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    X Position
                  </label>
                  <input
                    type="number"
                    value={selectedElement.x}
                    onChange={(e) => updateElement(selectedElement.id, { x: Number(e.target.value) })}
                    disabled={readOnly}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Y Position
                  </label>
                  <input
                    type="number"
                    value={selectedElement.y}
                    onChange={(e) => updateElement(selectedElement.id, { y: Number(e.target.value) })}
                    disabled={readOnly}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Width
                  </label>
                  <input
                    type="number"
                    value={selectedElement.width}
                    onChange={(e) => updateElement(selectedElement.id, { width: Number(e.target.value) })}
                    disabled={readOnly}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Height
                  </label>
                  <input
                    type="number"
                    value={selectedElement.height}
                    onChange={(e) => updateElement(selectedElement.id, { height: Number(e.target.value) })}
                    disabled={readOnly}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
              </div>

              {(selectedElement.type === 'text' ||
                selectedElement.type === 'student_name' ||
                selectedElement.type === 'course_name' ||
                selectedElement.type === 'date') && (
                <>
                  {selectedElement.type === 'text' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Content
                      </label>
                      <input
                        type="text"
                        value={selectedElement.content || ''}
                        onChange={(e) => updateElement(selectedElement.id, { content: e.target.value })}
                        disabled={readOnly}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Font Size
                    </label>
                    <input
                      type="number"
                      value={selectedElement.font_size || 16}
                      onChange={(e) => updateElement(selectedElement.id, { font_size: Number(e.target.value) })}
                      disabled={readOnly}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Font Family
                    </label>
                    <select
                      value={selectedElement.font_family || 'Arial'}
                      onChange={(e) => updateElement(selectedElement.id, { font_family: e.target.value })}
                      disabled={readOnly}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="Arial">Arial</option>
                      <option value="Helvetica">Helvetica</option>
                      <option value="Times New Roman">Times New Roman</option>
                      <option value="Georgia">Georgia</option>
                      <option value="Courier New">Courier New</option>
                      <option value="Verdana">Verdana</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Font Color
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={selectedElement.font_color || '#000000'}
                        onChange={(e) => updateElement(selectedElement.id, { font_color: e.target.value })}
                        disabled={readOnly}
                        className="w-12 h-10 rounded cursor-pointer"
                      />
                      <input
                        type="text"
                        value={selectedElement.font_color || '#000000'}
                        onChange={(e) => updateElement(selectedElement.id, { font_color: e.target.value })}
                        disabled={readOnly}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Font Weight
                    </label>
                    <select
                      value={selectedElement.font_weight || 'normal'}
                      onChange={(e) => updateElement(selectedElement.id, { font_weight: e.target.value })}
                      disabled={readOnly}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="normal">Normal</option>
                      <option value="bold">Bold</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Text Align
                    </label>
                    <select
                      value={selectedElement.text_align || 'left'}
                      onChange={(e) => updateElement(selectedElement.id, { text_align: e.target.value })}
                      disabled={readOnly}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="left">Left</option>
                      <option value="center">Center</option>
                      <option value="right">Right</option>
                    </select>
                  </div>
                </>
              )}

              {(selectedElement.type === 'image' || selectedElement.type === 'signature') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Image URL
                  </label>
                  <input
                    type="text"
                    value={selectedElement.image_url || ''}
                    onChange={(e) => updateElement(selectedElement.id, { image_url: e.target.value })}
                    disabled={readOnly}
                    placeholder="https://example.com/image.png"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rotation (degrees)
                </label>
                <input
                  type="number"
                  value={selectedElement.rotation || 0}
                  onChange={(e) => updateElement(selectedElement.id, { rotation: Number(e.target.value) })}
                  disabled={readOnly}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Move size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">Select an element to edit its properties</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TemplateBuilder
