import { formatInr } from "../api";
import type { SuggestedProduct } from "../utils";
import ProductThumb from "./ProductThumb";

export default function ProductCard({
  product,
  onAdd,
}: {
  product: SuggestedProduct;
  onAdd: (product: SuggestedProduct) => void;
}) {
  const hasDiscount = !!product.discount_percent && product.discounted_price_paise !== undefined;
  const hasRating = product.rating !== undefined && product.rating > 0;
  return (
    <div className="product-card">
      <ProductThumb src={product.image_url} alt={product.title} block />
      <div className="product-card-title">{product.title}</div>
      <div className="product-card-desc">{product.description}</div>
      {hasRating && (
        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
          ★ {product.rating!.toFixed(1)} ({product.review_count?.toLocaleString() ?? 0} reviews)
        </div>
      )}
      {hasDiscount && (
        <div className="product-card-offer" style={{ fontSize: 12, color: "var(--status-good, #1a7f37)", fontWeight: 600 }}>
          {product.discount_percent}% off for you
        </div>
      )}
      <div className="product-card-footer">
        <span className="product-card-price">
          {hasDiscount ? (
            <>
              <span style={{ textDecoration: "line-through", opacity: 0.55, fontSize: 12, marginRight: 6 }}>
                {formatInr(product.price_paise)}
              </span>
              {formatInr(product.discounted_price_paise!)}
            </>
          ) : (
            formatInr(product.price_paise)
          )}
        </span>
        <button className="btn btn-primary" type="button" disabled={!product.in_stock} onClick={() => onAdd(product)}>
          {product.in_stock ? "Add to cart" : "Out of stock"}
        </button>
      </div>
    </div>
  );
}
