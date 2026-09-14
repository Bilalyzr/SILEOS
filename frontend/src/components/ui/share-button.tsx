import { useEffect, useState } from "react";
import {
  Share2,
  Link as LinkIcon,
  Facebook,
  Linkedin,
  MessageCircle,
  Download,
  ImagePlus,
} from "lucide-react";
import { Button } from "./button";
import { GlassDialog } from "./dialog";
import { BrandBanner } from "@/components/design-system/BrandBanner";
import {
  buildBrandArtwork,
  downloadArtwork,
  readBannerFile,
} from "@/utils/brand-artwork";
import { copyToClipboard } from "@/utils/certificate-share";
import toast from "react-hot-toast";
interface ShareButtonProps {
  url?: string;
  title?: string;
  description?: string;
  caption?: string;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
  className?: string;
  showLabel?: boolean;
}
export function ShareButton({
  url,
  title = "SashaInfinity · Keep discovering",
  description = "A little curiosity. A world of possibility.",
  caption,
  variant = "outline",
  size = "sm",
  className = "",
  showLabel = true,
}: ShareButtonProps) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [cover, setCover] = useState<string>();
  const [error, setError] = useState("");
  useEffect(
    () => () => {
      if (cover) URL.revokeObjectURL(cover);
    },
    [cover],
  );
  const shareUrl = url || window.location.href;
  const safeUrl = (() => {
    try {
      const u = new URL(shareUrl, window.location.origin);
      return /^https?:$/.test(u.protocol) ? u.href : "";
    } catch {
      return "";
    }
  })();
  const text = caption || `${title}\n${safeUrl}`;
  async function artwork(native = false) {
    setBusy(true);
    setError("");
    try {
      const blob = await buildBrandArtwork(title, description, cover);
      const file = new File([blob], "sashainfinity-share.png", {
        type: "image/png",
      });
      if (
        native &&
        navigator.canShare?.({ files: [file] }) &&
        navigator.share
      ) {
        await navigator.share({ files: [file], title, text });
      } else {
        downloadArtwork(blob);
        toast.success("Banner downloaded. Attach it to your post.");
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError"))
        setError("Unable to create the banner. Try downloading again.");
    } finally {
      setBusy(false);
    }
  }
  function platform(name: string) {
    const u = encodeURIComponent(safeUrl),
      t = encodeURIComponent(text);
    const targets: Record<string, string> = {
      whatsapp: `https://wa.me/?text=${t}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${u}`,
      linkedin: caption
        ? `https://www.linkedin.com/feed/?shareActive=true&text=${t}`
        : `https://www.linkedin.com/sharing/share-offsite/?url=${u}`,
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${u}`,
    };
    window.open(targets[name], "_blank", "noopener,noreferrer");
  }
  return (
    <>
      <Button
        variant={variant}
        size={showLabel ? size : "icon"}
        className={className}
        aria-label="Share"
        onClick={() => setOpen(true)}
      >
        <Share2 size={16} />
        {showLabel && <span className="ml-2">Share</span>}
      </Button>
      <GlassDialog
        open={open}
        onOpenChange={setOpen}
        title="Share something worth discovering"
        size="lg"
      >
        <BrandBanner
          compact
          title={title}
          description={description}
          image={cover}
        />
        <label className="brand-share-upload">
          <span>
            <ImagePlus size={14} className="inline mr-2" />
            Add your own banner artwork (optional)
          </span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const input = e.target;
              setError("");
              try {
                setCover(await readBannerFile(file));
              } catch (err) {
                setError(
                  err instanceof Error
                    ? err.message
                    : "Could not open this image.",
                );
              }
              input.value = "";
            }}
          />
        </label>
        {cover && (
          <Button variant="ghost" size="sm" onClick={() => setCover(undefined)}>
            Remove artwork
          </Button>
        )}
        <p className="brand-share-note">
          Download a matching banner to attach to your post. Your uploaded image
          stays in this browser. Social platforms control link previews; link
          sharing does not upload this custom artwork.
        </p>
        {error && (
          <p className="campus-error" role="alert">
            {error}
          </p>
        )}
        <div className="brand-share-options">
          <Button disabled={busy} onClick={() => artwork()}>
            <Download size={15} className="mr-2" />
            {busy ? "Preparing…" : "Download banner"}
          </Button>
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => artwork(true)}
          >
            <Share2 size={15} className="mr-2" />
            Share image
          </Button>
        </div>
        <div className="brand-share-grid">
          {[
            { name: "whatsapp", label: "WhatsApp", icon: MessageCircle },
            { name: "facebook", label: "Facebook", icon: Facebook },
            { name: "linkedin", label: "LinkedIn", icon: Linkedin },
            { name: "twitter", label: "Twitter / X", icon: Share2 },
          ].map(({ name, label, icon: Icon }) => (
            <button
              key={name}
              disabled={!safeUrl}
              onClick={() => platform(name)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
          <button
            disabled={!safeUrl}
            onClick={async () => {
              if (await copyToClipboard(safeUrl)) toast.success("Link copied");
              else
                setError(
                  "Clipboard unavailable. Copy the address from your browser.",
                );
            }}
          >
            <LinkIcon size={16} />
            Copy link
          </button>
          <button
            onClick={async () => {
              if (await copyToClipboard(text)) toast.success("Caption copied");
              else setError("Clipboard unavailable.");
            }}
          >
            Copy caption
          </button>
        </div>
      </GlassDialog>
    </>
  );
}
