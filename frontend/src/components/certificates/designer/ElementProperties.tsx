/**
 * ElementProperties — per-type property panel (plan Task 7). Position/
 * size/rotation/z for every element; then type-specific fields: font
 * picker (curated 12, live Google Fonts load) + size/color/weight/align/
 * letter-spacing for text-ish types, border editor for rect, image src
 * field with client-side allowlist validation + upload button for
 * image/signature_image, a QR size note (QR itself renders server-side),
 * free-text content for "text".
 */
import * as React from 'react'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { DesignerElement, BorderStyle } from '@/lib/certificateDesignerTypes'
import { TOKEN_ELEMENT_TYPES } from '@/lib/certificateDesignerTypes'
import { CURATED_FONT_NAMES, loadGoogleFont } from '@/lib/curatedFonts'
import { isSafeAssetSrc, assetSrcErrorMessage } from '@/lib/certificateAssetSrc'
import { uploadImage } from '@/api/upload'
import toast from 'react-hot-toast'

export interface ElementPropertiesProps {
  element: DesignerElement | null
  onChange: (patch: Partial<DesignerElement>) => void
  disabled?: boolean
}

const FIELD = 'block text-xs font-medium text-neutral-600 mb-1'
const INPUT = 'input w-full text-sm'

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  disabled,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
  disabled?: boolean
}) {
  return (
    <div>
      <label className={FIELD}>{label}</label>
      <input
        type="number"
        className={INPUT}
        value={Number.isFinite(value) ? value : 0}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        onChange={(e) => {
          const v = parseFloat(e.target.value)
          onChange(Number.isFinite(v) ? v : 0)
        }}
      />
    </div>
  )
}

function ColorField({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  disabled?: boolean
}) {
  const safeHex = /^#[0-9a-fA-F]{3,8}$/.test(value) ? value : '#000000'
  return (
    <div>
      <label className={FIELD}>{label}</label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={safeHex}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="w-9 h-9 rounded border border-neutral-300 cursor-pointer p-0.5"
          aria-label={`${label} swatch`}
        />
        <input
          type="text"
          className={`${INPUT} flex-1`}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#000000"
        />
      </div>
    </div>
  )
}

export const ElementProperties: React.FC<ElementPropertiesProps> = ({ element, onChange, disabled }) => {
  const [uploading, setUploading] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  if (!element) {
    return (
      <div className="text-sm text-neutral-500 p-4 text-center">
        Select an element on the canvas to edit its properties.
      </div>
    )
  }

  const isTextLike =
    element.type === 'text' || TOKEN_ELEMENT_TYPES.includes(element.type)
  const isImageLike = element.type === 'image' || element.type === 'signature_image'
  const isRect = element.type === 'rect'
  const isLine = element.type === 'line'
  const isQr = element.type === 'qr_code'

  const src = element.image_url || element.src || ''
  const srcValid = !src || isSafeAssetSrc(src)

  const handleUploadClick = () => fileInputRef.current?.click()

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setUploading(true)
    try {
      const res = await uploadImage(file)
      onChange({ image_url: res.file_url, src: res.file_url })
    } catch (err) {
      toast.error('Image upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const borderObj =
    typeof element.border === 'object' && element.border
      ? element.border
      : { width: 0, style: 'solid' as BorderStyle, color: '#000000' }

  const updateBorder = (patch: Partial<{ width: number; style: BorderStyle; color: string }>) => {
    onChange({ border: { ...borderObj, ...patch } })
  }

  return (
    <div className="space-y-4" data-testid="element-properties">
      <div>
        <p className="text-xs uppercase tracking-wide text-neutral-400 font-semibold mb-1">
          {element.type.replace(/_/g, ' ')}
        </p>
      </div>

      {/* Position / size / rotation / z */}
      <div className="grid grid-cols-2 gap-3">
        <NumberField label="X" value={element.x} disabled={disabled} onChange={(v) => onChange({ x: v })} />
        <NumberField label="Y" value={element.y} disabled={disabled} onChange={(v) => onChange({ y: v })} />
        <NumberField
          label="Width"
          value={element.width}
          min={1}
          disabled={disabled}
          onChange={(v) => onChange({ width: v })}
        />
        <NumberField
          label="Height"
          value={element.height}
          min={1}
          disabled={disabled}
          onChange={(v) => onChange({ height: v })}
        />
        <NumberField
          label="Rotation (°)"
          value={element.rotation ?? 0}
          disabled={disabled}
          onChange={(v) => onChange({ rotation: v })}
        />
        <NumberField
          label="Layer (z-index)"
          value={element.z_index ?? 0}
          disabled={disabled}
          onChange={(v) => onChange({ z_index: v })}
        />
      </div>

      {element.type === 'text' && (
        <div>
          <label className={FIELD}>Text content</label>
          <textarea
            className={`${INPUT} min-h-[64px]`}
            value={element.content || ''}
            disabled={disabled}
            onChange={(e) => onChange({ content: e.target.value })}
          />
        </div>
      )}

      {TOKEN_ELEMENT_TYPES.includes(element.type) && (
        <p className="text-xs text-neutral-500 bg-neutral-50 rounded p-2">
          This is a typed token — the real value is substituted automatically when the
          certificate is issued or previewed.
        </p>
      )}

      {isTextLike && (
        <>
          <div>
            <label className={FIELD}>Font</label>
            <select
              className={INPUT}
              value={element.font_family || ''}
              disabled={disabled}
              onChange={(e) => {
                const font = e.target.value
                if (font) loadGoogleFont(font)
                onChange({ font_family: font || null })
              }}
            >
              <option value="">Default</option>
              {CURATED_FONT_NAMES.map((f) => (
                <option key={f} value={f} style={{ fontFamily: `'${f}'` }}>
                  {f}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <NumberField
              label="Font size"
              value={element.font_size ?? 24}
              min={1}
              disabled={disabled}
              onChange={(v) => onChange({ font_size: v })}
            />
            <div>
              <label className={FIELD}>Weight</label>
              <select
                className={INPUT}
                value={element.font_weight || 'normal'}
                disabled={disabled}
                onChange={(e) => onChange({ font_weight: e.target.value })}
              >
                <option value="normal">Normal</option>
                <option value="bold">Bold</option>
                {[100, 200, 300, 400, 500, 600, 700, 800, 900].map((w) => (
                  <option key={w} value={String(w)}>
                    {w}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <ColorField
            label="Text color"
            value={element.font_color || '#000000'}
            disabled={disabled}
            onChange={(v) => onChange({ font_color: v })}
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={FIELD}>Align</label>
              <select
                className={INPUT}
                value={element.text_align || 'left'}
                disabled={disabled}
                onChange={(e) => onChange({ text_align: e.target.value as DesignerElement['text_align'] })}
              >
                <option value="left">Left</option>
                <option value="center">Center</option>
                <option value="right">Right</option>
              </select>
            </div>
            <NumberField
              label="Letter spacing (px)"
              value={element.letter_spacing ?? 0}
              disabled={disabled}
              onChange={(v) => onChange({ letter_spacing: v })}
            />
          </div>

          <ColorField
            label="Background color"
            value={element.background_color || ''}
            disabled={disabled}
            onChange={(v) => onChange({ background_color: v })}
          />
        </>
      )}

      {isImageLike && (
        <div>
          <label className={FIELD}>Image source</label>
          <div className="flex gap-2">
            <input
              type="text"
              className={`${INPUT} flex-1 ${!srcValid ? 'border-danger-400' : ''}`}
              value={src}
              disabled={disabled}
              onChange={(e) => onChange({ image_url: e.target.value, src: e.target.value })}
              placeholder="/uploads/..."
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={disabled || uploading}
              onClick={handleUploadClick}
            >
              <Upload size={14} className="mr-1" />
              {uploading ? 'Uploading…' : 'Upload'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              className="hidden"
              onChange={handleFileSelected}
            />
          </div>
          {!srcValid && <p className="text-xs text-danger-600 mt-1">{assetSrcErrorMessage()}</p>}
        </div>
      )}

      {isRect && (
        <>
          <ColorField
            label="Fill color"
            value={element.background_color || element.fill || ''}
            disabled={disabled}
            onChange={(v) => onChange({ background_color: v, fill: v })}
          />
          <NumberField
            label="Corner radius"
            value={element.border_radius ?? 0}
            min={0}
            max={1000}
            disabled={disabled}
            onChange={(v) => onChange({ border_radius: v })}
          />
          <div>
            <p className={FIELD}>Border</p>
            <div className="grid grid-cols-3 gap-2">
              <NumberField
                label="Width"
                value={borderObj.width}
                min={0}
                max={20}
                disabled={disabled}
                onChange={(v) => updateBorder({ width: v })}
              />
              <div>
                <label className={FIELD}>Style</label>
                <select
                  className={INPUT}
                  value={borderObj.style}
                  disabled={disabled}
                  onChange={(e) => updateBorder({ style: e.target.value as BorderStyle })}
                >
                  <option value="solid">Solid</option>
                  <option value="dashed">Dashed</option>
                  <option value="dotted">Dotted</option>
                </select>
              </div>
              <ColorField
                label="Color"
                value={borderObj.color}
                disabled={disabled}
                onChange={(v) => updateBorder({ color: v })}
              />
            </div>
          </div>
        </>
      )}

      {isLine && (
        <>
          <ColorField
            label="Line color"
            value={element.line_color || element.font_color || '#000000'}
            disabled={disabled}
            onChange={(v) => onChange({ line_color: v, font_color: v })}
          />
          <NumberField
            label="Thickness (px)"
            value={element.line_thickness ?? 2}
            min={0}
            max={100}
            disabled={disabled}
            onChange={(v) => onChange({ line_thickness: v })}
          />
        </>
      )}

      {isQr && (
        <p className="text-xs text-neutral-500 bg-neutral-50 rounded p-2">
          The QR code is generated server-side from the certificate's verify URL when the
          certificate is previewed or issued — its size follows the box width/height above.
        </p>
      )}
    </div>
  )
}

export default ElementProperties
