import { useState } from "react";

export default function ProductThumb({
  src,
  alt,
  size = 40,
  block = false,
}: {
  src?: string;
  alt: string;
  /** Fixed pixel size for inline use (cart/order rows). Ignored when `block`. */
  size?: number;
  /** Fill the container's width at a 1:1 aspect ratio instead (product cards). */
  block?: boolean;
}) {
  const [failed, setFailed] = useState(false);

  const dims = block
    ? { width: "100%", height: "auto", aspectRatio: "1 / 1" }
    : { width: size, height: size, flexShrink: 0 };

  if (!src || failed) {
    return <div aria-hidden style={{ ...dims, borderRadius: 6, background: "var(--surface-2)" }} />;
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      style={{ ...dims, objectFit: "cover", borderRadius: 6 }}
    />
  );
}
