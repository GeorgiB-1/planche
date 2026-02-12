import { useState, useCallback } from "react";
import SketchUpload from "@/components/SketchUpload";
import ConfigPanel from "@/components/ConfigPanel";
import SketchRenderComparison from "@/components/SketchRenderComparison";
import RefinementBar from "@/components/RefinementBar";
import BudgetBar from "@/components/BudgetBar";
import ProductList from "@/components/ProductList";
import SwapModal from "@/components/SwapModal";
import {
  furnishRoom,
  getAlternatives,
  swapProduct,
  type DesignResult,
  type RefineResult,
  type BuyLink,
} from "@/services/api";

// ---------------------------------------------------------------------------
// Single-page design workspace for Planche.bg
// ---------------------------------------------------------------------------

type AppPhase = "upload" | "generating" | "result";

export default function HomePage() {
  // ---- Core state ----------------------------------------------------------

  const [phase, setPhase] = useState<AppPhase>("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sketchPreviewUrl, setSketchPreviewUrl] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ---- Design result state -------------------------------------------------

  const [designId, setDesignId] = useState<string | null>(null);
  const [sketchUrl, setSketchUrl] = useState<string | null>(null);
  const [renderUrl, setRenderUrl] = useState<string | null>(null);
  const [renderVersion, setRenderVersion] = useState(1);
  const [products, setProducts] = useState<BuyLink[]>([]);
  const [budgetSpent, setBudgetSpent] = useState(0);
  const [budgetTotal, setBudgetTotal] = useState(0);

  // ---- Refinement state ----------------------------------------------------

  const [isRefining, setIsRefining] = useState(false);

  // ---- Swap modal state ----------------------------------------------------

  const [swapSlot, setSwapSlot] = useState<string | null>(null);
  const [swapAlternatives, setSwapAlternatives] = useState<any[]>([]);
  const [isSwapLoading, setIsSwapLoading] = useState(false);

  // ---- Handlers: Upload & Config -------------------------------------------

  const handleFileSelected = useCallback((file: File) => {
    setSelectedFile(file);
    setSketchPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(file);
    });
    setShowConfig(true);
    setError(null);
  }, []);

  const handleConfigSubmit = useCallback(
    async (config: {
      budget: number;
      tier: string;
      style: string;
      roomType: string;
    }) => {
      if (!selectedFile) return;

      setPhase("generating");
      setError(null);

      try {
        const result: DesignResult = await furnishRoom(
          selectedFile,
          config.budget,
          config.tier,
          config.style,
          config.roomType,
        );

        setDesignId(result.design_id);
        setSketchUrl(result.sketch_url);
        setRenderUrl(result.render_url);
        setRenderVersion(1);
        setProducts(result.products);
        setBudgetSpent(result.budget_spent);
        setBudgetTotal(result.budget_spent + result.budget_remaining);
        setPhase("result");
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(
          `Възникна грешка при генерирането на дизайна.\n${message}`,
        );
        setPhase("upload");
      }
    },
    [selectedFile],
  );

  // ---- Handlers: Refinement ------------------------------------------------

  const handleRefineStart = useCallback(() => {
    setIsRefining(true);
    setError(null);
  }, []);

  const handleRefineComplete = useCallback((result: RefineResult) => {
    setRenderUrl(result.render_url);
    setRenderVersion(result.version);
    setIsRefining(false);
  }, []);

  const handleRefineError = useCallback((message: string) => {
    setError(message);
    setIsRefining(false);
  }, []);

  // ---- Handlers: Swap ------------------------------------------------------

  const handleSwapRequest = useCallback(
    async (slot: string) => {
      if (!designId) return;
      setSwapSlot(slot);
      setIsSwapLoading(true);

      try {
        const result = await getAlternatives(designId, slot);
        setSwapAlternatives(result.alternatives);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(`Грешка при зареждане на алтернативи: ${message}`);
        setSwapSlot(null);
      } finally {
        setIsSwapLoading(false);
      }
    },
    [designId],
  );

  const handleSwapSelect = useCallback(
    async (productId: string) => {
      if (!designId || !swapSlot) return;
      setIsSwapLoading(true);

      try {
        const result = await swapProduct(designId, swapSlot, productId);
        setRenderUrl(result.render_url);
        setRenderVersion((v) => v + 1);
        setSwapSlot(null);
        setSwapAlternatives([]);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(`Грешка при замяна: ${message}`);
      } finally {
        setIsSwapLoading(false);
      }
    },
    [designId, swapSlot],
  );

  const handleSwapClose = useCallback(() => {
    setSwapSlot(null);
    setSwapAlternatives([]);
  }, []);

  // ---- Handler: New design (reset) -----------------------------------------

  const handleNewDesign = useCallback(() => {
    setPhase("upload");
    setSelectedFile(null);
    if (sketchPreviewUrl) URL.revokeObjectURL(sketchPreviewUrl);
    setSketchPreviewUrl(null);
    setShowConfig(false);
    setError(null);
    setDesignId(null);
    setSketchUrl(null);
    setRenderUrl(null);
    setRenderVersion(1);
    setProducts([]);
    setBudgetSpent(0);
    setBudgetTotal(0);
  }, [sketchPreviewUrl]);

  // ---- Render --------------------------------------------------------------

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* ---------------------------------------------------------------- */}
      {/* Header                                                           */}
      {/* ---------------------------------------------------------------- */}
      <header className="border-b border-gray-200 bg-white/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900">Planche.bg</h1>
            <span className="text-sm text-blue-600 hidden sm:inline">
              AI Интериорен Дизайн
            </span>
          </div>
          {phase === "result" && (
            <button
              type="button"
              onClick={handleNewDesign}
              className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
            >
              Нов дизайн
            </button>
          )}
        </div>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* Loading overlay (during initial generation)                       */}
      {/* ---------------------------------------------------------------- */}
      {phase === "generating" && (
        <div className="fixed inset-0 z-50 bg-white/80 backdrop-blur flex flex-col items-center justify-center">
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

      {/* ---------------------------------------------------------------- */}
      {/* Main content                                                      */}
      {/* ---------------------------------------------------------------- */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* ============================================================== */}
        {/* UPLOAD PHASE                                                    */}
        {/* ============================================================== */}
        {phase === "upload" && (
          <div className="max-w-2xl mx-auto">
            {/* Hero text */}
            <div className="text-center py-8">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900">
                AI Интериорен Дизайн
              </h2>
              <p className="text-gray-500 mt-3 max-w-xl mx-auto">
                Качете скица &rarr; Изберете стил &rarr; Получете
                фотореалистичен дизайн с истински мебели
              </p>
            </div>

            {/* Step 1: Upload */}
            <section>
              <SketchUpload onFileSelected={handleFileSelected} />
            </section>

            {/* Step 2: Configure (shown after file selected) */}
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
                    isLoading={false}
                  />
                </section>
              )}
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* RESULT PHASE                                                    */}
        {/* ============================================================== */}
        {phase === "result" && designId && (
          <div className="space-y-6">
            {/* Side-by-side comparison */}
            <SketchRenderComparison
              sketchUrl={sketchUrl || sketchPreviewUrl || ""}
              renderUrl={renderUrl}
              renderVersion={renderVersion}
              isLoading={isRefining}
            />

            {/* Refinement bar */}
            <RefinementBar
              designId={designId}
              isRefining={isRefining}
              onRefineStart={handleRefineStart}
              onRefineComplete={handleRefineComplete}
              onError={handleRefineError}
            />

            {/* Budget + Products row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Budget bar (left 2/3) */}
              <div className="lg:col-span-2">
                <BudgetBar
                  budgetSpent={budgetSpent}
                  budgetTotal={budgetTotal}
                />
              </div>

              {/* Product list (right 1/3) */}
              <div className="lg:col-span-1">
                <ProductList
                  products={products}
                  onSwap={handleSwapRequest}
                />
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Error banner                                                     */}
        {/* ---------------------------------------------------------------- */}
        {error && (
          <div className="max-w-2xl mx-auto mt-4 bg-red-50 text-red-700 p-4 rounded-lg">
            <p className="font-medium mb-1">Грешка</p>
            <p className="text-sm whitespace-pre-line">{error}</p>
            <button
              type="button"
              onClick={() => setError(null)}
              className="mt-2 text-red-600 underline text-sm hover:text-red-800"
            >
              Затвори
            </button>
          </div>
        )}
      </main>

      {/* ---------------------------------------------------------------- */}
      {/* Swap Modal                                                        */}
      {/* ---------------------------------------------------------------- */}
      <SwapModal
        isOpen={swapSlot !== null}
        slot={swapSlot || ""}
        alternatives={swapAlternatives}
        isLoading={isSwapLoading}
        onSelect={handleSwapSelect}
        onClose={handleSwapClose}
      />
    </div>
  );
}
