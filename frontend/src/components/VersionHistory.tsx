import React, { useState, useEffect, useCallback } from "react";
import {
  getDesignVersions,
  revertDesignVersion,
  type RenderVersion,
} from "@/services/api";

interface VersionHistoryProps {
  designId: string;
  currentVersion: number;
  onRevert: (renderUrl: string, version: number) => void;
}

export default function VersionHistory({
  designId,
  currentVersion,
  onRevert,
}: VersionHistoryProps) {
  const [versions, setVersions] = useState<RenderVersion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isReverting, setIsReverting] = useState(false);
  const [previewVersion, setPreviewVersion] = useState<number | null>(null);

  // Fetch versions when designId or currentVersion changes
  useEffect(() => {
    if (!designId) return;

    let cancelled = false;
    setIsLoading(true);

    getDesignVersions(designId)
      .then((result) => {
        if (!cancelled) {
          setVersions(result.versions);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch versions:", err);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [designId, currentVersion]);

  const handleRevert = useCallback(
    async (version: number) => {
      if (version === currentVersion || isReverting) return;
      setIsReverting(true);

      try {
        const result = await revertDesignVersion(designId, version);
        onRevert(result.render_url, result.version);
      } catch (err) {
        console.error("Failed to revert:", err);
      } finally {
        setIsReverting(false);
      }
    },
    [designId, currentVersion, isReverting, onRevert],
  );

  // Don't show if only 1 version
  if (versions.length <= 1 && !isLoading) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-700">
          {"История на версиите"}
        </h3>
        <span className="text-xs text-gray-400">
          {versions.length} {versions.length === 1 ? "версия" : "версии"}
        </span>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
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
          Зареждане...
        </div>
      ) : (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {versions.map((v) => {
            const isActive = v.version === currentVersion;
            const isPreviewing = v.version === previewVersion;

            return (
              <button
                key={v.version}
                type="button"
                disabled={isReverting}
                onClick={() => handleRevert(v.version)}
                onMouseEnter={() => setPreviewVersion(v.version)}
                onMouseLeave={() => setPreviewVersion(null)}
                className={`
                  relative flex-shrink-0 rounded-lg overflow-hidden border-2
                  transition-all duration-150 group
                  ${isActive
                    ? "border-blue-500 ring-1 ring-blue-200"
                    : isPreviewing
                      ? "border-gray-400"
                      : "border-gray-200 hover:border-gray-300"
                  }
                  ${isReverting ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
                `}
                title={
                  isActive
                    ? `v${v.version} (текуща)`
                    : `Възстанови v${v.version}`
                }
              >
                <img
                  src={v.url}
                  alt={`Версия ${v.version}`}
                  className="w-20 h-12 object-cover"
                  loading="lazy"
                />

                {/* Version badge */}
                <span
                  className={`
                    absolute bottom-0.5 left-0.5 text-[10px] font-medium
                    px-1.5 py-0.5 rounded
                    ${isActive
                      ? "bg-blue-600 text-white"
                      : "bg-black/50 text-white"
                    }
                  `}
                >
                  v{v.version}
                </span>

                {/* Revert overlay on hover (non-active only) */}
                {!isActive && (
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                    <span className="text-white text-[10px] font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                      {"Възстанови"}
                    </span>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
