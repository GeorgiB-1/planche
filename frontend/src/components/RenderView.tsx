import React, { useState, useCallback } from "react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface RenderViewProps {
  renderUrl: string | null;
  isLoading?: boolean;
  error?: string | null;
}

// ---------------------------------------------------------------------------
// Bulgarian labels
// ---------------------------------------------------------------------------

const LABELS = {
  generating: "Генериране на дизайн...",
  generatingHint: "Това може да отнеме 30-60 секунди",
  download: "Изтегли",
  closeLightbox: "Затвори",
} as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RenderView({
  renderUrl,
  isLoading = false,
  error = null,
}: RenderViewProps) {
  const [isLightboxOpen, setIsLightboxOpen] = useState(false);

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  const openLightbox = useCallback(() => {
    setIsLightboxOpen(true);
  }, []);

  const closeLightbox = useCallback(() => {
    setIsLightboxOpen(false);
  }, []);

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      // Close only when clicking the backdrop itself, not the image
      if (e.target === e.currentTarget) {
        closeLightbox();
      }
    },
    [closeLightbox],
  );

  const handleOverlayKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Escape") {
        closeLightbox();
      }
    },
    [closeLightbox],
  );

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  if (isLoading) {
    return (
      <div className="relative bg-gray-100 rounded-xl overflow-hidden min-h-[300px] flex flex-col items-center justify-center gap-3">
        {/* Spinner */}
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

        <p className="text-gray-600 font-medium">{LABELS.generating}</p>
        <p className="text-gray-400 text-sm">{LABELS.generatingHint}</p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------

  if (error) {
    return (
      <div className="relative bg-gray-100 rounded-xl overflow-hidden min-h-[300px] flex items-center justify-center p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg w-full text-center">
          {error}
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Empty state — no URL yet and not loading
  // -------------------------------------------------------------------------

  if (!renderUrl) {
    return (
      <div className="relative bg-gray-100 rounded-xl overflow-hidden min-h-[300px] flex items-center justify-center">
        <p className="text-gray-400 text-sm">
          Тук ще се покаже генерираният дизайн
        </p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render result
  // -------------------------------------------------------------------------

  return (
    <>
      <div className="relative bg-gray-100 rounded-xl overflow-hidden min-h-[300px]">
        {/* Rendered image */}
        <img
          src={renderUrl}
          alt="Генериран дизайн"
          className="w-full h-auto rounded-xl cursor-pointer"
          onClick={openLightbox}
        />

        {/* Download button */}
        <a
          href={renderUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute bottom-4 right-4 bg-white/90 backdrop-blur text-gray-700 px-4 py-2 rounded-lg shadow hover:bg-white text-sm font-medium transition-colors"
        >
          {LABELS.download}
        </a>
      </div>

      {/* Lightbox overlay */}
      {isLightboxOpen && (
        <div
          role="dialog"
          aria-modal="true"
          tabIndex={-1}
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={handleOverlayClick}
          onKeyDown={handleOverlayKeyDown}
        >
          {/* Close button */}
          <button
            type="button"
            onClick={closeLightbox}
            className="absolute top-4 right-4 text-white/80 hover:text-white transition-colors z-10"
            aria-label={LABELS.closeLightbox}
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

          {/* Lightbox image */}
          <img
            src={renderUrl}
            alt="Генериран дизайн — увеличен"
            className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg"
          />
        </div>
      )}
    </>
  );
}
