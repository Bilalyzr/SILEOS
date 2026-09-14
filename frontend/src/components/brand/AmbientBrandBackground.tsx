/** Decorative atmosphere for Aurum shells. It never receives pointer input. */
export function AmbientBrandBackground() {
  return (
    <div className="aurum-ambient" aria-hidden="true" data-ambient>
      <span className="aurum-orb aurum-orb-top" />
      <span className="aurum-orb aurum-orb-bottom" />
      <span className="aurum-grain" />
      <span className="aurum-vignette" />
    </div>
  );
}

export default AmbientBrandBackground;
