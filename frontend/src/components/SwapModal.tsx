import React from "react";

interface SwapAlternative {
  id: string;
  name: string;
  price: number;
  image_url: string;
  visual_description: string | null;
}

interface SwapModalProps {
  isOpen: boolean;
  slot: string;
  alternatives: SwapAlternative[];
  isLoading?: boolean;
  onSelect: (productId: string) => void;
  onClose: () => void;
}

function SwapModal({
  isOpen,
  slot,
  alternatives,
  isLoading = false,
  onSelect,
  onClose,
}: SwapModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-lg font-semibold">
            {"Алтернативи за замяна"} &mdash; {slot}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Затвори"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <svg
              className="animate-spin h-8 w-8 text-blue-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            <span className="ml-3 text-gray-500 text-sm">
              {"Зареждане\u2026"}
            </span>
          </div>
        ) : alternatives.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <p className="text-gray-500">{"Няма налични алтернативи"}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 overflow-y-auto max-h-[calc(80vh-65px)]">
            {alternatives.map((alt) => (
              <div
                key={alt.id}
                className="border rounded-lg overflow-hidden hover:border-blue-300 transition-colors"
              >
                {/* Product image */}
                {alt.image_url ? (
                  <img
                    src={alt.image_url}
                    alt={alt.name}
                    className="w-full h-32 object-cover bg-gray-100"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-32 bg-gray-100 flex items-center justify-center">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-10 w-10 text-gray-300"
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
                  <h3
                    className="font-medium text-sm text-gray-900 truncate"
                    title={alt.name}
                  >
                    {alt.name}
                  </h3>

                  <p className="text-blue-600 font-semibold text-sm">
                    {`\u20ac${alt.price.toFixed(2)}`}
                  </p>

                  {alt.visual_description && (
                    <p
                      className="text-xs text-gray-500 line-clamp-2"
                      title={alt.visual_description}
                    >
                      {alt.visual_description}
                    </p>
                  )}
                </div>

                {/* Select button */}
                <button
                  type="button"
                  onClick={() => onSelect(alt.id)}
                  className="w-full bg-blue-600 text-white py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
                >
                  {"Избери"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default SwapModal;
