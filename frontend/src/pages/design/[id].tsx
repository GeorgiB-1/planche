import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/router";

import RenderView from "@/components/RenderView";
import ProductList from "@/components/ProductList";
import BudgetBar from "@/components/BudgetBar";
import SwapModal from "@/components/SwapModal";
import type { DesignResult } from "@/services/api";
import { getAlternatives, swapProduct, type SwapAlternative } from "@/services/api";

// ---------------------------------------------------------------------------
// Bulgarian labels
// ---------------------------------------------------------------------------

const LABELS = {
  pageTitle: "Вашият дизайн",
  regenerate: "Ново поколение",
  backHome: "Начало",
  notFound: "Дизайнът не е намерен.",
  notFoundHint:
    "Не успяхме да заредим данните за този дизайн. Моля, опитайте отново.",
  goBack: "Обратно към началната страница",
  loading: "Зареждане на дизайна...",
  swapComingSoon: "Замяна — скоро!",
} as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DesignResultPage() {
  const router = useRouter();
  const id = router.query.id as string | undefined;

  const [designResult, setDesignResult] = useState<DesignResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Swap-flow state
  const [swapSlot, setSwapSlot] = useState<string | null>(null);
  const [alternatives, setAlternatives] = useState<SwapAlternative[]>([]);
  const [isSwapLoading, setIsSwapLoading] = useState(false);
  const [isSwapModalOpen, setIsSwapModalOpen] = useState(false);

  // -------------------------------------------------------------------------
  // Load design data from localStorage on mount
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (!id) {
      setIsLoading(false);
      return;
    }

    try {
      const raw = localStorage.getItem(`design_${id}`);
      if (raw) {
        const parsed: DesignResult = JSON.parse(raw);
        setDesignResult(parsed);
      }
    } catch {
      // JSON parse failed — leave designResult as null
    }

    setIsLoading(false);
  }, [id]);

  // -------------------------------------------------------------------------
  // Swap handler — open modal and fetch alternatives
  // -------------------------------------------------------------------------

  const handleSwap = useCallback(
    async (slot: string) => {
      if (!id) return;
      setSwapSlot(slot);
      setAlternatives([]);
      setIsSwapModalOpen(true);
      setIsSwapLoading(true);

      try {
        const data = await getAlternatives(id, slot);
        setAlternatives(data.alternatives);
      } catch (err) {
        console.error("Failed to load alternatives", err);
        alert("Грешка при зареждане на алтернативите. Моля, опитайте отново.");
      } finally {
        setIsSwapLoading(false);
      }
    },
    [id],
  );

  // -------------------------------------------------------------------------
  // Swap select handler — confirm a product swap
  // -------------------------------------------------------------------------

  const handleSwapSelect = useCallback(
    async (productId: string) => {
      if (!id || !swapSlot) return;
      setIsSwapLoading(true);

      try {
        const result = await swapProduct(id, swapSlot, productId);
        // Update the design result with the new render
        setDesignResult((prev) =>
          prev ? { ...prev, render_url: result.render_url } : prev,
        );
        // Also persist updated render_url to localStorage
        try {
          const raw = localStorage.getItem(`design_${id}`);
          if (raw) {
            const parsed: DesignResult = JSON.parse(raw);
            parsed.render_url = result.render_url;
            localStorage.setItem(`design_${id}`, JSON.stringify(parsed));
          }
        } catch {
          // localStorage update failed — non-critical
        }
        // Close modal and reset swap state
        setIsSwapModalOpen(false);
        setSwapSlot(null);
        setAlternatives([]);
      } catch (err) {
        console.error("Swap failed", err);
        alert("Грешка при замяната. Моля, опитайте отново.");
      } finally {
        setIsSwapLoading(false);
      }
    },
    [id, swapSlot],
  );

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500 text-lg">{LABELS.loading}</p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Error / not-found state
  // -------------------------------------------------------------------------

  if (!designResult) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            {LABELS.notFound}
          </h2>
          <p className="text-gray-500 mb-6">{LABELS.notFoundHint}</p>
          <Link href="/" className="text-blue-600 hover:text-blue-700 font-medium">
            {LABELS.goBack}
          </Link>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Compute budget total from spent + remaining
  // -------------------------------------------------------------------------

  const budgetTotal = designResult.budget_spent + designResult.budget_remaining;

  // -------------------------------------------------------------------------
  // Main layout
  // -------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="max-w-7xl mx-auto px-4 py-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {LABELS.pageTitle}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            ID: {designResult.design_id}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <Link href="/" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
            {LABELS.backHome}
          </Link>
          <Link
            href="/"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
          >
            {LABELS.regenerate}
          </Link>
        </div>
      </header>

      {/* Content grid */}
      <main className="max-w-7xl mx-auto px-4 grid grid-cols-1 lg:grid-cols-3 gap-6 pb-12">
        {/* Left column: Render + BudgetBar */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <RenderView renderUrl={designResult.render_url} />
          <BudgetBar
            budgetSpent={designResult.budget_spent}
            budgetTotal={budgetTotal}
          />
        </div>

        {/* Right column: Product sidebar */}
        <div className="lg:col-span-1">
          <ProductList
            products={designResult.products}
            onSwap={handleSwap}
          />
        </div>
      </main>

      {/* Swap modal */}
      <SwapModal
        isOpen={isSwapModalOpen}
        slot={swapSlot ?? ""}
        alternatives={alternatives}
        isLoading={isSwapLoading}
        onSelect={handleSwapSelect}
        onClose={() => {
          setIsSwapModalOpen(false);
          setSwapSlot(null);
          setAlternatives([]);
        }}
      />
    </div>
  );
}
