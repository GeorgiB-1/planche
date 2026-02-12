import React, { useState, useCallback } from "react";

interface SketchRenderComparisonProps {
  sketchUrl: string;
  renderUrl: string | null;
  renderVersion: number;
  isLoading: boolean;
}

export default function SketchRenderComparison({
  sketchUrl,
  renderUrl,
  renderVersion,
  isLoading,
}: SketchRenderComparisonProps) {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  const closeLightbox = useCallback(() => setLightboxUrl(null), []);

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) closeLightbox();
    },
    [closeLightbox],
  );

  const handleOverlayKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Escape") closeLightbox();
    },
    [closeLightbox],
  );

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Sketch side */}
        <div className="relative bg-gray-100 rounded-xl overflow-hidden min-h-[250px]">
          <span className="absolute top-3 left-3 z-10 bg-black/60 text-white text-xs font-medium px-2.5 py-1 rounded-full">
            {"Скица"}
          </span>
          <img
            src={sketchUrl}
            alt="Скица"
            className="w-full h-auto rounded-xl cursor-pointer"
            onClick={() => setLightboxUrl(sketchUrl)}
          />
        </div>

        {/* Render side */}
        <div className="relative bg-gray-100 rounded-xl overflow-hidden min-h-[250px]">
          <span className="absolute top-3 left-3 z-10 bg-black/60 text-white text-xs font-medium px-2.5 py-1 rounded-full">
            {`Резултат v${renderVersion}`}
          </span>

          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[250px] gap-3">
              <svg
                className="animate-spin h-10 w-10 text-blue-500"
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
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <p className="text-gray-600 font-medium">
                {"Промяна на дизайна..."}
              </p>
            </div>
          ) : renderUrl ? (
            <>
              <img
                src={renderUrl}
                alt={`Резултат v${renderVersion}`}
                className="w-full h-auto rounded-xl cursor-pointer"
                onClick={() => setLightboxUrl(renderUrl)}
              />
              <a
                href={renderUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute bottom-3 right-3 bg-white/90 backdrop-blur text-gray-700 px-3 py-1.5 rounded-lg shadow hover:bg-white text-xs font-medium transition-colors"
              >
                {"Изтегли"}
              </a>
            </>
          ) : (
            <div className="flex items-center justify-center h-full min-h-[250px]">
              <p className="text-gray-400 text-sm">
                {"Тук ще се покаже генерираният дизайн"}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          role="dialog"
          aria-modal="true"
          tabIndex={-1}
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={handleOverlayClick}
          onKeyDown={handleOverlayKeyDown}
        >
          <button
            type="button"
            onClick={closeLightbox}
            className="absolute top-4 right-4 text-white/80 hover:text-white transition-colors z-10"
            aria-label="Затвори"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-8 w-8"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
          <img
            src={lightboxUrl}
            alt="Увеличено изображение"
            className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg"
          />
        </div>
      )}
    </>
  );
}
