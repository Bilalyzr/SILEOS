import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { GuidedLabPlayer } from "./GuidedLabPlayer";
import labs from "../../../labs/catalog/labs.json";
import type { ConceptConfig, Trial } from "@/api/lab-studio";
const ModelViewer = lazy(() =>
  import("@/components/three-d/ThreeDViewer").then((m) => ({
    default: m.ThreeDViewer,
  })),
);

export function ConceptLabPlayer({
  config,
  slug,
  revision,
  sourceUrl,
  sourceBlob,
  previewOnly,
  title,
  height = 640,
  onTrial,
}: {
  config: ConceptConfig;
  slug?: string;
  revision?: string;
  sourceUrl?: string;
  sourceBlob?: Blob;
  previewOnly?: boolean;
  title: string;
  height?: number;
  onTrial?: (trial: Trial) => void;
}) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [channel] = useState(() => crypto.randomUUID());
  const [showModel, setShowModel] = useState(false);
  useEffect(() => {
    const send = () =>
      frame.current?.contentWindow?.postMessage(
        {
          type: "sasha-lab-config",
          channel,
          config,
          title,
          canCapture: !!onTrial,
        },
        window.location.origin,
      );
    const receive = (event: MessageEvent) => {
      if (
        event.origin !== window.location.origin ||
        event.source !== frame.current?.contentWindow ||
        event.data?.channel !== channel
      )
        return;
      if (event.data.type === "sasha-lab-ready") send();
      if (
        event.data.type === "sasha-lab-trial" &&
        event.data.trial &&
        JSON.stringify(event.data.trial).length < 5000
      )
        onTrial?.(event.data.trial);
    };
    window.addEventListener("message", receive);
    send();
    return () => window.removeEventListener("message", receive);
  }, [channel, config, title, onTrial]);
  return (
    <div className="lab-experience">
      {config.model_id &&
        !(config.guided_steps?.length || config.hotspots?.length) && (
          <section className="astra-model-guide">
            <div>
              <h3>Explore the 3D model</h3>
              <p>
                Rotate, zoom and inspect the model, then use the investigation
                below to test your ideas.
              </p>
            </div>
            <button
              type="button"
              className="sf-secondary"
              aria-expanded={showModel}
              onClick={() => setShowModel((v) => !v)}
            >
              {showModel ? "Close 3D model" : "Open 3D model"}
            </button>
            {showModel && (
              <Suspense fallback={<p role="status">Loading 3D viewer…</p>}>
                <ModelViewer
                  modelId={config.model_id}
                  sourceUrl={sourceUrl}
                  sourceBlob={sourceBlob}
                  enableXR
                  height={420}
                  description={config.model_description}
                />
              </Suspense>
            )}
          </section>
        )}
      {config.guided_steps?.length || config.hotspots?.length ? (
        <GuidedLabPlayer
          key={slug || "preview"}
          config={config}
          slug={slug}
          revision={revision}
          sourceUrl={sourceUrl}
                  sourceBlob={sourceBlob}
          previewOnly={previewOnly}
        />
      ) : null}
      <iframe
        ref={frame}
        src={
          config.engine === "supplied"
            ? labs.find((l) => l.slug === config.source_slug)?.embed_url
            : `/labs/cbse/concept.html?channel=${encodeURIComponent(channel)}`
        }
        title={title}
        className="lab-frame"
        style={{ height }}
        allow="fullscreen; xr-spatial-tracking"
        allowFullScreen
      />
    </div>
  );
}
