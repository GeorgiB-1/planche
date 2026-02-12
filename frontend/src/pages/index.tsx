import { useState } from "react";
import { useRouter } from "next/router";
import SketchUpload from "@/components/SketchUpload";
import ConfigPanel from "@/components/ConfigPanel";
import { furnishRoom, type DesignResult } from "@/services/api";

// ---------------------------------------------------------------------------
// Main landing / upload page for Planche.bg
// ---------------------------------------------------------------------------

export default function HomePage() {
  const router = useRouter();

  // ---- State --------------------------------------------------------------

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---- Handlers -----------------------------------------------------------

  function handleFileSelected(file: File) {
    setSelectedFile(file);
    setShowConfig(true);
    setError(null);
  }

  async function handleConfigSubmit(config: {
    budget: number;
    tier: string;
    style: string;
    roomType: string;
  }) {
    if (!selectedFile) return;

    setIsLoading(true);
    setError(null);

    try {
      const result: DesignResult = await furnishRoom(
        selectedFile,
        config.budget,
        config.tier,
        config.style,
        config.roomType,
      );

      // Persist the result in localStorage so the design page can read it
      localStorage.setItem(
        `design_${result.design_id}`,
        JSON.stringify(result),
      );

      router.push(`/design/${result.design_id}`);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : String(err);
      setError(
        `Възникна грешка при генерирането на дизайна. Моля, опитайте отново.\n${message}`,
      );
    } finally {
      setIsLoading(false);
    }
  }

  // ---- Render -------------------------------------------------------------

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* ------------------------------------------------------------------ */}
      {/* Loading overlay                                                     */}
      {/* ------------------------------------------------------------------ */}
      {isLoading && (
        <div className="fixed inset-0 z-50 bg-white/80 backdrop-blur flex flex-col items-center justify-center">
          {/* Spinner */}
          <svg
            className="animate-spin h-12 w-12 text-blue-600 mb-6"
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
          <p className="text-xl font-semibold text-gray-800">
            Генериране на дизайн...
          </p>
          <p className="text-gray-500 mt-2">
            Това може да отнеме 30-60 секунди
          </p>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Hero section                                                        */}
      {/* ------------------------------------------------------------------ */}
      <header className="text-center py-16 px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900">
          Planche.bg
        </h1>
        <p className="text-xl text-blue-600 mt-2">
          AI Интериорен Дизайн
        </p>
        <p className="text-gray-500 mt-4 max-w-xl mx-auto">
          Качете скица &rarr; Изберете стил &rarr; Получете фотореалистичен
          дизайн с истински мебели
        </p>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Content area                                                        */}
      {/* ------------------------------------------------------------------ */}
      <main className="max-w-2xl mx-auto px-4 pb-16">
        {/* ------ Step 1: Upload ------ */}
        <section>
          <SketchUpload onFileSelected={handleFileSelected} />
        </section>

        {/* ------ Step 2: Configure (shown after file selected) ------ */}
        <div
          className={`transition-all duration-500 ease-in-out overflow-hidden ${
            showConfig
              ? "max-h-[2000px] opacity-100 mt-8"
              : "max-h-0 opacity-0"
          }`}
        >
          {showConfig && (
            <section>
              <ConfigPanel
                onSubmit={handleConfigSubmit}
                isLoading={isLoading}
              />
            </section>
          )}
        </div>

        {/* ------ Error message ------ */}
        {error && (
          <div className="bg-red-50 text-red-700 p-4 rounded-lg mt-4">
            <p className="font-medium mb-1">Грешка</p>
            <p className="text-sm whitespace-pre-line">{error}</p>
          </div>
        )}
      </main>
    </div>
  );
}
