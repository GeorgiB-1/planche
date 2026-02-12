import React, { useState, useRef, useCallback } from "react";
import { refineDesign, type RefineResult } from "@/services/api";

interface RefinementBarProps {
  designId: string;
  isRefining: boolean;
  onRefineStart: () => void;
  onRefineComplete: (result: RefineResult) => void;
  onError: (message: string) => void;
}

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function RefinementBar({
  designId,
  isRefining,
  onRefineStart,
  onRefineComplete,
  onError,
}: RefinementBarProps) {
  const [instruction, setInstruction] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedPreview, setAttachedPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAttach = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (!ALLOWED_TYPES.includes(file.type)) {
        onError("Невалиден формат на изображение.");
        return;
      }

      setAttachedFile(file);
      setAttachedPreview((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(file);
      });

      // Reset the input so re-selecting the same file triggers onChange
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [onError],
  );

  const removeAttachment = useCallback(() => {
    if (attachedPreview) URL.revokeObjectURL(attachedPreview);
    setAttachedFile(null);
    setAttachedPreview(null);
  }, [attachedPreview]);

  const handleSubmit = useCallback(async () => {
    const hasText = instruction.trim().length > 0;
    const hasImage = attachedFile !== null;

    if (!hasText && !hasImage) {
      onError("Моля, въведете инструкция или прикачете изображение.");
      return;
    }

    onRefineStart();

    try {
      const result = await refineDesign(
        designId,
        instruction,
        attachedFile ?? undefined,
      );
      onRefineComplete(result);
      setInstruction("");
      removeAttachment();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      onError(`Грешка при промяна: ${message}`);
    }
  }, [designId, instruction, attachedFile, onRefineStart, onRefineComplete, onError, removeAttachment]);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <label className="text-sm font-medium text-gray-700 mb-2 block">
        {"Промяна на дизайна"}
      </label>

      <div className="flex gap-2">
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="Опишете промяната..."
          disabled={isRefining}
          rows={2}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:bg-gray-50"
        />

        <div className="flex flex-col gap-2">
          {/* Attach button */}
          <button
            type="button"
            onClick={handleAttach}
            disabled={isRefining}
            className="border border-gray-300 rounded-lg px-3 py-2 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Прикачи изображение"
          >
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
                d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"
              />
            </svg>
          </button>

          {/* Submit button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isRefining}
            className="bg-blue-600 text-white rounded-lg px-3 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-1"
          >
            {isRefining ? (
              <svg
                className="animate-spin h-4 w-4"
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
            ) : (
              "Промени"
            )}
          </button>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Attached image preview */}
      {attachedPreview && (
        <div className="mt-2 flex items-center gap-2">
          <img
            src={attachedPreview}
            alt="Прикачено"
            className="h-12 w-12 object-cover rounded border border-gray-200"
          />
          <span className="text-xs text-gray-500 truncate max-w-[200px]">
            {attachedFile?.name}
          </span>
          <button
            type="button"
            onClick={removeAttachment}
            disabled={isRefining}
            className="text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
            aria-label="Премахни"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
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
        </div>
      )}
    </div>
  );
}
