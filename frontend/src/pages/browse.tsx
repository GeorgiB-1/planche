import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import ProductCard from "@/components/ProductCard";
import { searchProducts, type ProductSummary, type SearchParams } from "@/services/api";

// ---------------------------------------------------------------------------
// Filter option definitions (Bulgarian labels)
// ---------------------------------------------------------------------------

const CATEGORY_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Всички категории" },
  { value: "sofa", label: "Дивани" },
  { value: "table", label: "Маси" },
  { value: "chair", label: "Столове" },
  { value: "bed", label: "Легла" },
  { value: "wardrobe", label: "Гардероби" },
  { value: "cabinet", label: "Шкафове" },
  { value: "desk", label: "Бюра" },
  { value: "shelf", label: "Рафтове" },
  { value: "lamp", label: "Осветление" },
  { value: "rug", label: "Килими" },
  { value: "mirror", label: "Огледала" },
];

const ROOM_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Всички стаи" },
  { value: "Хол", label: "Хол" },
  { value: "Спалня", label: "Спалня" },
  { value: "Кухня", label: "Кухня" },
  { value: "Баня", label: "Баня" },
  { value: "Офис", label: "Офис" },
  { value: "Детска стая", label: "Детска стая" },
  { value: "Трапезария", label: "Трапезария" },
];

const STYLE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Всички стилове" },
  { value: "Модерен", label: "Модерен" },
  { value: "Скандинавски", label: "Скандинавски" },
  { value: "Индустриален", label: "Индустриален" },
  { value: "Класически", label: "Класически" },
  { value: "Минималистичен", label: "Минималистичен" },
];

const SOURCE_OPTIONS: string[] = [
  "videnov.bg",
  "aiko-bg.com",
  "ikea.bg",
  "jysk.bg",
];

const PAGE_SIZE = 20;

// ---------------------------------------------------------------------------
// Browse / Search Page
// ---------------------------------------------------------------------------

export default function BrowsePage() {
  // ---- Filter state -------------------------------------------------------

  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [room, setRoom] = useState("");
  const [style, setStyle] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());

  // ---- Results state ------------------------------------------------------

  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  // ---- Mobile sidebar state -----------------------------------------------

  const [showFilters, setShowFilters] = useState(false);

  // ---- Debounce ref -------------------------------------------------------

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---- Build search params from current state -----------------------------

  const buildParams = useCallback(
    (currentLimit: number): SearchParams => {
      const params: SearchParams = { limit: currentLimit };
      if (query.trim()) params.q = query.trim();
      if (category) params.category = category;
      if (room) params.room = room;
      if (style) params.style = style;
      if (minPrice !== "" && !isNaN(Number(minPrice))) {
        params.min_price = Number(minPrice);
      }
      if (maxPrice !== "" && !isNaN(Number(maxPrice))) {
        params.max_price = Number(maxPrice);
      }
      if (selectedSources.size > 0) {
        params.source = Array.from(selectedSources).join(",");
      }
      return params;
    },
    [query, category, room, style, minPrice, maxPrice, selectedSources],
  );

  // ---- Execute search -----------------------------------------------------

  const executeSearch = useCallback(
    async (currentLimit: number) => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await searchProducts(buildParams(currentLimit));
        setProducts(result.products);
        setTotal(result.total);
        setHasSearched(true);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setError(`Грешка при търсенето: ${message}`);
      } finally {
        setIsLoading(false);
      }
    },
    [buildParams],
  );

  // ---- Auto-search with 300ms debounce when filters change ----------------

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    // Reset limit back to PAGE_SIZE when filters change
    setLimit(PAGE_SIZE);

    debounceRef.current = setTimeout(() => {
      executeSearch(PAGE_SIZE);
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, category, room, style, minPrice, maxPrice, selectedSources, executeSearch]);

  // ---- Source checkbox toggle ----------------------------------------------

  function toggleSource(source: string) {
    setSelectedSources((prev) => {
      const next = new Set(prev);
      if (next.has(source)) {
        next.delete(source);
      } else {
        next.add(source);
      }
      return next;
    });
  }

  // ---- Load more ----------------------------------------------------------

  function handleLoadMore() {
    const nextLimit = limit + PAGE_SIZE;
    setLimit(nextLimit);
    executeSearch(nextLimit);
  }

  // ---- Filter sidebar content (shared between desktop & mobile) -----------

  const filterContent = (
    <div className="space-y-4">
      {/* Category */}
      <div>
        <label htmlFor="filter-category" className="block text-sm font-medium text-gray-700 mb-1">
          Категория
        </label>
        <select
          id="filter-category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          {CATEGORY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Room type */}
      <div>
        <label htmlFor="filter-room" className="block text-sm font-medium text-gray-700 mb-1">
          Тип стая
        </label>
        <select
          id="filter-room"
          value={room}
          onChange={(e) => setRoom(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          {ROOM_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Style */}
      <div>
        <label htmlFor="filter-style" className="block text-sm font-medium text-gray-700 mb-1">
          Стил
        </label>
        <select
          id="filter-style"
          value={style}
          onChange={(e) => setStyle(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          {STYLE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Price range */}
      <div>
        <span className="block text-sm font-medium text-gray-700 mb-1">
          Цена (EUR)
        </span>
        <div className="flex gap-2">
          <input
            type="number"
            placeholder="Мин"
            min={0}
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            type="number"
            placeholder="Макс"
            min={0}
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      {/* Source checkboxes */}
      <div>
        <span className="block text-sm font-medium text-gray-700 mb-1">
          Източник
        </span>
        <div className="space-y-2">
          {SOURCE_OPTIONS.map((source) => (
            <label key={source} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedSources.has(source)}
                onChange={() => toggleSource(source)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              {source}
            </label>
          ))}
        </div>
      </div>
    </div>
  );

  // ---- Render -------------------------------------------------------------

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ------------------------------------------------------------------ */}
      {/* Top navigation bar                                                  */}
      {/* ------------------------------------------------------------------ */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-lg font-semibold text-gray-900 hover:text-blue-600 transition-colors">
            &larr; Planche.bg
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">
            Каталог мебели
          </h1>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Search bar                                                          */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-7xl mx-auto px-4 pt-6">
        <div className="relative">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 1010.5 18a7.5 7.5 0 006.15-3.35z"
            />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Търсене на мебели..."
            className="w-full border border-gray-300 rounded-lg pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Mobile filter toggle */}
        <button
          type="button"
          onClick={() => setShowFilters((prev) => !prev)}
          className="mt-3 lg:hidden flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          {showFilters ? "Скрий филтрите" : "Покажи филтрите"}
        </button>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Main content: sidebar + product grid                                */}
      {/* ------------------------------------------------------------------ */}
      <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* ---- Filter sidebar ---- */}
        {/* Desktop: always visible */}
        <aside className="lg:col-span-1 hidden lg:block">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">Филтри</h2>
            {filterContent}
          </div>
        </aside>

        {/* Mobile: collapsible */}
        {showFilters && (
          <aside className="lg:hidden col-span-1">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">Филтри</h2>
              {filterContent}
            </div>
          </aside>
        )}

        {/* ---- Product area ---- */}
        <main className="lg:col-span-3">
          {/* Results header */}
          {hasSearched && !error && (
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-gray-600">
                {total} продукта
              </p>
              {isLoading && (
                <svg
                  className="animate-spin h-5 w-5 text-blue-600"
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
              )}
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-4">
              <p className="text-sm">{error}</p>
            </div>
          )}

          {/* Loading state (initial) */}
          {isLoading && !hasSearched && (
            <div className="flex items-center justify-center py-20">
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
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
          )}

          {/* Empty state */}
          {hasSearched && !isLoading && !error && products.length === 0 && (
            <div className="text-center py-20">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="mx-auto h-12 w-12 text-gray-300 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 1010.5 18a7.5 7.5 0 006.15-3.35z"
                />
              </svg>
              <p className="text-gray-500 text-lg">Няма намерени продукти</p>
              <p className="text-gray-400 text-sm mt-1">
                Опитайте с различни филтри или ключови думи
              </p>
            </div>
          )}

          {/* Product grid */}
          {products.length > 0 && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {products.map((product) => (
                  <ProductCard
                    key={product.id}
                    name={product.name}
                    price={product.price}
                    currency={product.currency}
                    imageUrl={product.image_url}
                    sourceDomain={product.source_domain}
                    productUrl={product.product_url}
                    widthCm={product.width_cm}
                    heightCm={product.height_cm}
                    depthCm={product.depth_cm}
                  />
                ))}
              </div>

              {/* Load more button */}
              {products.length < total && (
                <div className="mt-8 text-center">
                  <button
                    type="button"
                    onClick={handleLoadMore}
                    disabled={isLoading}
                    className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm font-medium py-2.5 px-6 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? (
                      <>
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
                        Зареждане...
                      </>
                    ) : (
                      "Зареди още"
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
