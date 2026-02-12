import { useState, useEffect } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ConfigPanelProps {
  detectedRoomType?: string;
  onSubmit: (config: {
    budget: number;
    tier: string;
    style: string;
    roomType: string;
  }) => void;
  isLoading?: boolean;
}

interface RoomOption {
  value: string;
  label: string;
}

interface StyleOption {
  value: string;
  label: string;
}

interface TierOption {
  value: string;
  label: string;
  range: string;
  perSqmMin: number;
  perSqmMax: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ROOM_OPTIONS: RoomOption[] = [
  { value: "living_room", label: "Хол" },
  { value: "bedroom", label: "Спалня" },
  { value: "kitchen", label: "Кухня" },
  { value: "bathroom", label: "Баня" },
  { value: "office", label: "Офис" },
  { value: "kids_room", label: "Детска стая" },
  { value: "dining_room", label: "Трапезария" },
];

const STYLE_OPTIONS: StyleOption[] = [
  { value: "modern", label: "Модерен" },
  { value: "scandinavian", label: "Скандинавски" },
  { value: "industrial", label: "Индустриален" },
  { value: "classic", label: "Класически" },
  { value: "minimalist", label: "Минималистичен" },
];

const TIER_OPTIONS: TierOption[] = [
  {
    value: "budget",
    label: "Бюджетен",
    range: "€40-80/m\u00B2",
    perSqmMin: 40,
    perSqmMax: 80,
  },
  {
    value: "standard",
    label: "Стандартен",
    range: "€80-150/m\u00B2",
    perSqmMin: 80,
    perSqmMax: 150,
  },
  {
    value: "premium",
    label: "Премиум",
    range: "€150-300/m\u00B2",
    perSqmMin: 150,
    perSqmMax: 300,
  },
  {
    value: "luxury",
    label: "Луксозен",
    range: "€300-600/m\u00B2",
    perSqmMin: 300,
    perSqmMax: 600,
  },
];

const DEFAULT_ROOM_SQM = 20;

/**
 * Compute the default budget for a tier based on the midpoint of its
 * per-square-metre range multiplied by the room area.
 */
function tierMidpointBudget(tier: TierOption, areaSqm: number): number {
  const midpoint = (tier.perSqmMin + tier.perSqmMax) / 2;
  return Math.round(midpoint * areaSqm);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ConfigPanel({
  detectedRoomType,
  onSubmit,
  isLoading = false,
}: ConfigPanelProps) {
  // ---- State ---------------------------------------------------------------

  const [selectedRoom, setSelectedRoom] = useState<string>(
    detectedRoomType ?? "living_room"
  );
  const [selectedStyle, setSelectedStyle] = useState<string>("modern");
  const [selectedTier, setSelectedTier] = useState<string>("standard");
  const [roomAreaSqm, setRoomAreaSqm] = useState<number>(DEFAULT_ROOM_SQM);
  const [customBudget, setCustomBudget] = useState<number>(2000);

  // Sync room type when the parent passes a new detection result
  useEffect(() => {
    if (detectedRoomType) {
      setSelectedRoom(detectedRoomType);
    }
  }, [detectedRoomType]);

  // Recalculate budget when tier or room area changes
  useEffect(() => {
    const tier = TIER_OPTIONS.find((t) => t.value === selectedTier);
    if (tier) {
      setCustomBudget(tierMidpointBudget(tier, roomAreaSqm));
    }
  }, [selectedTier, roomAreaSqm]);

  // ---- Handlers ------------------------------------------------------------

  function handleBudgetChange(raw: string) {
    const parsed = parseInt(raw, 10);
    if (Number.isNaN(parsed)) {
      setCustomBudget(0);
      return;
    }
    setCustomBudget(parsed);
  }

  function handleSubmit() {
    // Clamp budget into the allowed range on submit
    const clampedBudget = Math.min(Math.max(customBudget, 100), 50000);

    onSubmit({
      budget: clampedBudget,
      tier: selectedTier,
      style: selectedStyle,
      roomType: selectedRoom,
    });
  }

  // ---- Render --------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Room Type                                                           */}
      {/* ------------------------------------------------------------------ */}
      <section>
        <label
          htmlFor="room-type"
          className="text-sm font-medium text-gray-700 mb-2 block"
        >
          Тип стая
          {detectedRoomType && (
            <span className="ml-2 text-xs text-gray-400 font-normal">
              (автоматично разпознат)
            </span>
          )}
        </label>
        <select
          id="room-type"
          value={selectedRoom}
          onChange={(e) => setSelectedRoom(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {ROOM_OPTIONS.map((room) => (
            <option key={room.value} value={room.value}>
              {room.label}
            </option>
          ))}
        </select>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Room Area                                                            */}
      {/* ------------------------------------------------------------------ */}
      <section>
        <label
          htmlFor="room-area"
          className="text-sm font-medium text-gray-700 mb-2 block"
        >
          Площ на стаята
        </label>
        <div className="relative">
          <input
            id="room-area"
            type="number"
            min={5}
            max={200}
            value={roomAreaSqm}
            onChange={(e) => {
              const parsed = parseInt(e.target.value, 10);
              setRoomAreaSqm(Number.isNaN(parsed) ? 0 : parsed);
            }}
            className="w-full border border-gray-300 rounded-lg px-3 pr-12 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm pointer-events-none">
            m&sup2;
          </span>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Приблизителна площ: 5 &ndash; 200 m&sup2;
        </p>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Style                                                               */}
      {/* ------------------------------------------------------------------ */}
      <section>
        <p className="text-sm font-medium text-gray-700 mb-2">Стил</p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {STYLE_OPTIONS.map((style) => {
            const isSelected = selectedStyle === style.value;
            return (
              <button
                key={style.value}
                type="button"
                onClick={() => setSelectedStyle(style.value)}
                className={
                  "border rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors text-center " +
                  (isSelected
                    ? "border-blue-500 bg-blue-50 text-blue-700 font-medium"
                    : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50")
                }
              >
                {style.label}
              </button>
            );
          })}
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Budget Tier                                                         */}
      {/* ------------------------------------------------------------------ */}
      <section>
        <p className="text-sm font-medium text-gray-700 mb-2">
          Ценови клас
        </p>
        <div className="grid grid-cols-2 gap-2">
          {TIER_OPTIONS.map((tier) => {
            const isSelected = selectedTier === tier.value;
            return (
              <button
                key={tier.value}
                type="button"
                onClick={() => setSelectedTier(tier.value)}
                className={
                  "border rounded-lg p-3 cursor-pointer transition-colors text-left " +
                  (isSelected
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50")
                }
              >
                <span
                  className={
                    "block text-sm font-medium " +
                    (isSelected ? "text-blue-700" : "text-gray-800")
                  }
                >
                  {tier.label}
                </span>
                <span
                  className={
                    "block text-xs mt-0.5 " +
                    (isSelected ? "text-blue-500" : "text-gray-500")
                  }
                >
                  {tier.range}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Custom Budget                                                       */}
      {/* ------------------------------------------------------------------ */}
      <section>
        <label
          htmlFor="custom-budget"
          className="text-sm font-medium text-gray-700 mb-2 block"
        >
          Бюджет
          <span className="ml-2 text-xs text-gray-400 font-normal">
            (изчислен за {roomAreaSqm} m&sup2;)
          </span>
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm pointer-events-none">
            &euro;
          </span>
          <input
            id="custom-budget"
            type="number"
            min={100}
            max={50000}
            value={customBudget}
            onChange={(e) => handleBudgetChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Допустим диапазон: €100 &ndash; €50 000
        </p>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Submit                                                              */}
      {/* ------------------------------------------------------------------ */}
      <button
        type="button"
        disabled={isLoading}
        onClick={handleSubmit}
        className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            {/* Spinner */}
            <svg
              className="animate-spin h-5 w-5 text-white"
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
            <span>Генериране...</span>
          </>
        ) : (
          <span>Генерирай дизайн</span>
        )}
      </button>
    </div>
  );
}
