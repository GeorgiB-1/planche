import React from "react";

interface ProductCardProps {
  name: string;
  price: number | null;
  currency?: string;
  imageUrl: string | null;
  sourceDomain: string | null;
  productUrl: string | null;
  widthCm: number | null;
  heightCm: number | null;
  depthCm: number | null;
  slot?: string;
  onSwap?: (slot: string) => void;
}

function formatDimensions(
  width: number | null,
  height: number | null,
  depth: number | null
): string | null {
  const parts: string[] = [];
  if (width != null) parts.push(`\u0428${width}`);
  if (height != null) parts.push(`\u0412${height}`);
  if (depth != null) parts.push(`\u0414${depth}`);
  if (parts.length === 0) return null;
  return `${parts.join(" \u00d7 ")} \u0441\u043c`;
}

function ProductCard({
  name,
  price,
  currency = "\u20ac",
  imageUrl,
  sourceDomain,
  productUrl,
  widthCm,
  heightCm,
  depthCm,
  slot,
  onSwap,
}: ProductCardProps) {
  const dimensions = formatDimensions(widthCm, heightCm, depthCm);

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* Product image */}
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={name}
          className="w-full h-40 object-cover bg-gray-100"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-40 bg-gray-100 flex items-center justify-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-12 w-12 text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 10h1l1-2h14l1 2h1v2H3v-2zm1 2v6a1 1 0 001 1h14a1 1 0 001-1v-6M6 18v2M18 18v2"
            />
          </svg>
        </div>
      )}

      {/* Card body */}
      <div className="p-3 space-y-1">
        <h3 className="font-medium text-sm text-gray-900 truncate" title={name}>
          {name}
        </h3>

        <p className="text-blue-600 font-semibold">
          {price != null
            ? `${currency}${price.toFixed(2)}`
            : "\u0426\u0435\u043d\u0430 \u043d\u0435 \u0435 \u043d\u0430\u043b\u0438\u0447\u043d\u0430"}
        </p>

        {sourceDomain && (
          <p className="text-xs text-gray-500">{sourceDomain}</p>
        )}

        {dimensions && (
          <p className="text-xs text-gray-400">{dimensions}</p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 p-3 pt-0">
        {productUrl ? (
          <a
            href={productUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-blue-600 text-white text-sm py-1.5 px-3 rounded hover:bg-blue-700 text-center"
          >
            {"\u041a\u0443\u043f\u0438"}
          </a>
        ) : (
          <button
            type="button"
            disabled
            className="flex-1 bg-blue-600 text-white text-sm py-1.5 px-3 rounded opacity-50 cursor-not-allowed"
          >
            {"\u041a\u0443\u043f\u0438"}
          </button>
        )}

        {onSwap && slot && (
          <button
            type="button"
            onClick={() => onSwap(slot)}
            className="flex-1 border border-gray-300 text-gray-700 text-sm py-1.5 px-3 rounded hover:bg-gray-50"
          >
            {"\u0417\u0430\u043c\u0435\u043d\u0438"}
          </button>
        )}
      </div>
    </div>
  );
}

export default ProductCard;
