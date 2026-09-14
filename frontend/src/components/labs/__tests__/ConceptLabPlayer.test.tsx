import { cleanup, render, screen, act } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ConceptLabPlayer } from "../ConceptLabPlayer";
import { templateConfig } from "../concept-templates";

afterEach(cleanup);
it("accepts captured evidence only from its own frame, origin and channel", () => {
  const capture = vi.fn();
  render(
    <ConceptLabPlayer
      config={templateConfig("linear")}
      title="Linear lab"
      onTrial={capture}
    />,
  );
  const iframe = screen.getByTitle("Linear lab") as HTMLIFrameElement;
  const channel = new URL(iframe.src).searchParams.get("channel");
  const data = { type: "sasha-lab-trial", channel, trial: { slope: 2 } };
  act(() =>
    window.dispatchEvent(
      new MessageEvent("message", {
        source: iframe.contentWindow,
        origin: "https://untrusted.example",
        data,
      }),
    ),
  );
  act(() =>
    window.dispatchEvent(
      new MessageEvent("message", {
        source: window,
        origin: window.location.origin,
        data,
      }),
    ),
  );
  act(() =>
    window.dispatchEvent(
      new MessageEvent("message", {
        source: iframe.contentWindow,
        origin: window.location.origin,
        data: { ...data, channel: "wrong" },
      }),
    ),
  );
  expect(capture).not.toHaveBeenCalled();
  act(() =>
    window.dispatchEvent(
      new MessageEvent("message", {
        source: iframe.contentWindow,
        origin: window.location.origin,
        data,
      }),
    ),
  );
  expect(capture).toHaveBeenCalledWith({ slope: 2 });
});
