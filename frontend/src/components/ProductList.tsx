import React from "react";
import ProductCard from "./ProductCard";
import { BuyLink } from "@/services/api";

interface ProductListProps {
  products: BuyLink[];
  onSwap?: (slot: string) => void;
}

/** Derive a slot identifier from a product name (e.g. "Coffee Table" -> "coffee_table"). */
function toSlot(name: string): string {
  return name.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
}

function ProductList({ products, onSwap }: ProductListProps) {
  if (products.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200">
          <span className="font-semibold text-gray-900">
            Мебели в дизайна
          </span>
        </div>
        <div className="px-4 py-8 text-center text-sm text-gray-400">
          Няма намерени продукти
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex justify-between items-center">
        <span className="font-semibold text-gray-900">
          Мебели в дизайна
        </span>
        <span className="text-sm text-gray-500">
          {products.length} продукта
        </span>
      </div>

      {/* Scrollable product list */}
      <div className="overflow-y-auto max-h-[600px] divide-y divide-gray-100">
        {products.map((product, index) => (
          <div key={`${product.name}-${index}`} className="p-3">
            <ProductCard
              name={product.name}
              price={product.price}
              currency={product.currency}
              imageUrl={product.image_url}
              sourceDomain={product.source}
              productUrl={product.url}
              widthCm={null}
              heightCm={null}
              depthCm={null}
              slot={toSlot(product.name)}
              onSwap={onSwap}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

export default ProductList;
