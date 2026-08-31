import { formatInr } from "../api";
import type { SuggestedProduct } from "../utils";

export default function ProductCard({
  product,
  onAdd,
}: {
  product: SuggestedProduct;
  onAdd: (product: SuggestedProduct) => void;
}) {
  return (
    <div className="product-card">
      <div className="product-card-title">{product.title}</div>
      <div className="product-card-desc">{product.description}</div>
      <div className="product-card-footer">
        <span className="product-card-price">{formatInr(product.price_paise)}</span>
        <button className="btn btn-primary" type="button" disabled={!product.in_stock} onClick={() => onAdd(product)}>
          {product.in_stock ? "Add to cart" : "Out of stock"}
        </button>
      </div>
    </div>
  );
}
