import { useEffect, useMemo, useState } from "preact/hooks";
import type { LookupMatch, NewProduct, Setup } from "./api";
import { fallbackUnit, suggestedName, unitsMatchingSize } from "./units";

interface Props {
  setup: Setup;
  match: LookupMatch | null;
  onSubmit: (product: Omit<NewProduct, "barcode">) => void;
  onCancel: () => void;
}

/**
 * Enter never saves. A scan that lands in a text box ends in Enter, which
 * would otherwise save the digits, for example when a tablet's on-screen
 * keyboard is open. No autofocus either, as that would open the keyboard.
 */
export function NewProductForm({ setup, match, onSubmit, onCancel }: Props) {
  const [name, setName] = useState("");
  const [unitFilter, setUnitFilter] = useState("");
  const [unitId, setUnitId] = useState(fallbackUnit(setup.units)?.id ?? 0);
  const [locationId, setLocationId] = useState(
    setup.default_location_id ?? setup.locations[0]?.id ?? 0,
  );
  const [groupId, setGroupId] = useState<number | null>(null);

  // A late lookup only fills what the user hasn't already chosen.
  const [unitTouched, setUnitTouched] = useState(false);
  useEffect(() => {
    if (!match) return;
    setName((current) => current || suggestedName(match.name, match.brand));
    const sized = unitsMatchingSize(setup.units, match.quantity);
    if (sized.length > 0 && !unitTouched) setUnitId(sized[0].id);
  }, [match]);

  const sizedUnitIds = useMemo(
    () => new Set(unitsMatchingSize(setup.units, match?.quantity ?? null).map((u) => u.id)),
    [match, setup],
  );
  const filter = unitFilter.trim().toLowerCase();
  const shownUnits = setup.units.filter(
    (unit) => unit.id === unitId || unit.name.toLowerCase().includes(filter),
  );
  // Units matching the pack size go first, so the right one is easy to spot.
  shownUnits.sort((a, b) => Number(sizedUnitIds.has(b.id)) - Number(sizedUnitIds.has(a.id)));

  return (
    <form
      class="stacked"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit({
          name,
          unit_id: unitId,
          location_id: locationId,
          group_id: groupId,
        });
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" && event.target instanceof HTMLInputElement) {
          event.preventDefault();
        }
      }}
    >
      <label>
        Name
        <input
          required
          maxLength={200}
          value={name}
          onInput={(event) => setName(event.currentTarget.value)}
        />
      </label>
      <fieldset>
        <legend>Unit</legend>
        {match?.quantity && (
          <p>
            Pack size online: {match.quantity}
            {sizedUnitIds.size === 0 && ". No unit matches it, so check the choice below."}
          </p>
        )}
        <div class="stacked">
          <input
            type="search"
            aria-label="Filter units"
            placeholder="Filter units"
            value={unitFilter}
            onInput={(event) => setUnitFilter(event.currentTarget.value)}
          />
          <select
            aria-label="Unit"
            required
            value={unitId}
            onChange={(event) => {
              setUnitTouched(true);
              setUnitId(Number(event.currentTarget.value));
            }}
          >
            {shownUnits.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name}
                {sizedUnitIds.has(unit.id) ? " (matches pack size)" : ""}
              </option>
            ))}
          </select>
        </div>
      </fieldset>
      <label>
        Location
        <select
          required
          value={locationId}
          onChange={(event) => setLocationId(Number(event.currentTarget.value))}
        >
          {setup.locations.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Product group
        <select
          value={groupId ?? ""}
          onChange={(event) => {
            const { value } = event.currentTarget;
            setGroupId(value ? Number(value) : null);
          }}
        >
          <option value="">None</option>
          {setup.groups.map((group) => (
            <option key={group.id} value={group.id}>
              {group.name}
            </option>
          ))}
        </select>
      </label>
      <div class="actions">
        <button type="submit">Create in Grocy</button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
