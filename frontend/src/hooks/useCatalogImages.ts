import { useEffect, useState } from "react";
import { api } from "../api";

/** Cart/order line items only ever store {sku, title, price_paise, quantity} -
 * no image, since they're point-in-time snapshots, not live product refs.
 * This fetches the public catalog once and maps sku -> image_url so those
 * views can still show a thumbnail without changing what gets persisted. */
export function useCatalogImages(): Record<string, string | undefined> {
  const [images, setImages] = useState<Record<string, string | undefined>>({});

  useEffect(() => {
    api
      .catalog()
      .then((c) => {
        const map: Record<string, string | undefined> = {};
        for (const p of c.products) {
          const sku = p.sku || p.id;
          if (sku) map[sku] = p.image_url;
        }
        setImages(map);
      })
      .catch(() => {});
  }, []);

  return images;
}
