import React, { useState, useRef, useCallback } from "react";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SketchUploadProps {
  onFileSelected: (file: File) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

// Bulgarian labels (matching bg.ts keys)
const LABELS = {
  uploadSketch: "Качи скица",
  dragDrop: "Плъзнете скица тук",
  orClickToUpload: "или натиснете за качване",
  takePhoto: "Снимайте",
  supportedFormats: "JPEG, PNG, WebP (макс. 10MB)",
  invalidFormat: "Невалиден формат",
  fileTooLarge: "Файлът е прекалено голям",
} as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SketchUpload({ onFileSelected }: SketchUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // -----------------------------------------------------------------------
  // Validation & handling
  // -----------------------------------------------------------------------

  const processFile = useCallback(
    (file: File) => {
      setError(null);

      if (!ALLOWED_TYPES.includes(file.type)) {
        setError(LABELS.invalidFormat);
        return;
      }

      if (file.size > MAX_SIZE) {
        setError(LABELS.fileTooLarge);
        return;
      }

      // Revoke the previous object URL to avoid memory leaks
      setPreview((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(file);
      });

      onFileSelected(file);
    },
    [onFileSelected],
  );

  // -----------------------------------------------------------------------
  // File input handler
  // -----------------------------------------------------------------------

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  // -----------------------------------------------------------------------
  // Drag-and-drop handlers
  // -----------------------------------------------------------------------

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const file = e.dataTransfer.files?.[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  // -----------------------------------------------------------------------
  // Click handler — open the hidden file input
  // -----------------------------------------------------------------------

  const handleZoneClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleCameraClick = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation(); // don't bubble up to the drop-zone click
      cameraInputRef.current?.click();
    },
    [],
  );

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="w-full">
      {/* Label */}
      <h2 className="mb-3 text-lg font-semibold text-gray-800">
        {LABELS.uploadSketch}
      </h2>

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        onClick={handleZoneClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") handleZoneClick();
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
          transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400
          ${
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-gray-400"
          }
        `}
      >
        {preview ? (
          /* ----- Image preview ----- */
          <img
            src={preview}
            alt={LABELS.uploadSketch}
            className="max-h-64 mx-auto rounded-lg"
          />
        ) : (
          /* ----- Placeholder content ----- */
          <div className="flex flex-col items-center gap-2">
            {/* Upload icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5V18a2.25 2.25 0 002.25 2.25h13.5A2.25 2.25 0 0021 18v-1.5m-15-6l6-6m0 0l6 6m-6-6v12"
              />
            </svg>

            <p className="text-gray-700 font-medium">{LABELS.dragDrop}</p>
            <p className="text-gray-500 text-sm">{LABELS.orClickToUpload}</p>
            <p className="text-gray-400 text-xs mt-1">
              {LABELS.supportedFormats}
            </p>
          </div>
        )}
      </div>

      {/* Hidden file input (gallery / file picker) */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleInputChange}
      />

      {/* Hidden camera input (mobile only) */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleInputChange}
      />

      {/* Camera button — visible only on mobile */}
      <button
        type="button"
        onClick={handleCameraClick}
        className="
          sm:hidden mt-3 w-full flex items-center justify-center gap-2
          rounded-lg bg-gray-100 py-3 text-sm font-medium text-gray-700
          hover:bg-gray-200 transition-colors
        "
      >
        {/* Camera icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z"
          />
        </svg>
        {LABELS.takePhoto}
      </button>

      {/* Error message */}
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
    </div>
  );
}
