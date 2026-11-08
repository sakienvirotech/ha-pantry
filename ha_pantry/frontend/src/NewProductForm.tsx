import { useEffect, useMemo, useState } from "preact/hooks";
import { createUnit } from "./api";
import type { LookupMatch, Named, NewProduct, Setup, Userfield } from "./api";
import { fallbackUnit, formatSize, parseSize, suggestedName, unitsMatchingSize } from "./units";

interface Props {
  setup: Setup;
  match: LookupMatch | null;
  onSubmit: (product: Omit<NewProduct, "barcode">) => Promise<unknown>;
  onUnitCreated: (unit: Named) => void;
  onReload: () => Promise<void>;
  onCancel: () => void;
}

function initialValue(field: Userfield): string {
  return field.default ?? (field.type === "checkbox" ? "0" : "");
}

/**
 * Enter never saves. A scan that lands in a text box ends in Enter, which
 * would otherwise save the digits, for example when a tablet's on-screen
 * keyboard is open. No autofocus either, as that would open the keyboard.
 */
export function NewProductForm({
  setup,
  match,
  onSubmit,
  onUnitCreated,
  onReload,
  onCancel,
}: Props) {
  const [name, setName] = useState("");
  const [unitFilter, setUnitFilter] = useState("");
  const [unitId, setUnitId] = useState(fallbackUnit(setup.units)?.id ?? 0);
  const [locationId, setLocationId] = useState(
    setup.default_location_id ?? setup.locations[0]?.id ?? 0,
  );
  const [groupId, setGroupId] = useState<number | null>(null);
  const [savePicture, setSavePicture] = useState(true);
  const [userfields, setUserfields] = useState<Record<string, string>>(() =>
    Object.fromEntries(setup.userfields.map((field) => [field.name, initialValue(field)])),
  );
  // Undefined while the new-unit row is closed.
  const [newUnit, setNewUnit] = useState<string>();
  const [unitBusy, setUnitBusy] = useState(false);
  const [unitError, setUnitError] = useState("");
  const [reloading, setReloading] = useState(false);
  // Saving a picture can take several seconds, so stop a second tap creating twice.
  const [saving, setSaving] = useState(false);

  // A late lookup only fills what the user hasn't already chosen.
  const [unitTouched, setUnitTouched] = useState(false);
  useEffect(() => {
    if (match) setName((current) => current || suggestedName(match.name, match.brand));
  }, [match]);
  // Also when the units change, so one added in Grocy meanwhile can be picked.
  useEffect(() => {
    const sized = unitsMatchingSize(setup.units, match?.quantity ?? null);
    if (sized.length > 0 && !unitTouched) setUnitId(sized[0].id);
  }, [match, setup.units]);

  const onlineSize = match?.quantity ? parseSize(match.quantity) : null;

  async function addUnit() {
    const name = newUnit?.trim();
    if (!name || unitBusy) return;
    setUnitBusy(true);
    setUnitError("");
    try {
      const unit = await createUnit(name);
      onUnitCreated(unit);
      setUnitId(unit.id);
      setUnitTouched(true);
      setUnitFilter("");
      setNewUnit(undefined);
    } catch (e) {
      setUnitError((e as Error).message);
    } finally {
      setUnitBusy(false);
    }
  }

  async function reload() {
    setReloading(true);
    await onReload();
    setReloading(false);
  }

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
      onSubmit={async (event) => {
        event.preventDefault();
        if (saving) return;
        setSaving(true);
        await onSubmit({
          name,
          unit_id: unitId,
          location_id: locationId,
          group_id: groupId,
          image_url: savePicture ? (match?.image_url ?? null) : null,
          userfields: Object.fromEntries(
            setup.userfields
              .map((field) => [field.name, userfields[field.name] ?? initialValue(field)])
              .filter(([, value]) => value !== ""),
          ),
        });
        setSaving(false);
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
            {sizedUnitIds.size === 0 && (
              <>
                . No unit matches it, so check the choice below or{" "}
                <button type="button" class="link" onClick={() => setNewUnit(newUnit ?? "")}>
                  add a new unit
                </button>
                .
              </>
            )}
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
          {newUnit === undefined ? (
            <div class="actions tight">
              <button type="button" onClick={() => setNewUnit("")}>
                New unit…
              </button>
              <button type="button" disabled={reloading} onClick={reload}>
                {reloading ? "Reloading…" : "Reload units"}
              </button>
            </div>
          ) : (
            <div class="stacked">
              <label>
                New unit in Grocy
                <input
                  maxLength={100}
                  placeholder={`e.g. Can - ${onlineSize ? formatSize(onlineSize) : "440g"}`}
                  value={newUnit}
                  onInput={(event) => setNewUnit(event.currentTarget.value)}
                />
              </label>
              {unitError && <p role="alert">{unitError}</p>}
              <div class="actions tight">
                <button
                  type="button"
                  disabled={unitBusy || !newUnit.trim()}
                  onClick={addUnit}
                >
                  {unitBusy ? "Adding…" : "Add to Grocy"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNewUnit(undefined);
                    setUnitError("");
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
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
      {setup.userfields.map((field) => (
        <UserfieldInput
          key={field.name}
          field={field}
          value={userfields[field.name] ?? initialValue(field)}
          onChange={(value) => setUserfields((current) => ({ ...current, [field.name]: value }))}
        />
      ))}
      {match?.image_url && (
        <label class="checkbox">
          <input
            type="checkbox"
            checked={savePicture}
            onChange={(event) => setSavePicture(event.currentTarget.checked)}
          />
          Save the picture above to Grocy
        </label>
      )}
      <div class="actions">
        <button type="submit" disabled={saving}>
          {saving ? "Creating…" : "Create in Grocy"}
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

interface UserfieldInputProps {
  field: Userfield;
  value: string;
  onChange: (value: string) => void;
}

/** One Grocy userfield, as the closest plain form control. */
function UserfieldInput({ field, value, onChange }: UserfieldInputProps) {
  const { caption, required } = field;
  switch (field.type) {
    case "preset-list":
    case "preset-checklist":
      // One choice even for a checklist; ticking several is done in Grocy.
      return (
        <label>
          {caption}
          <select
            required={required}
            value={value}
            onChange={(event) => onChange(event.currentTarget.value)}
          >
            <option value="">{required ? "Choose…" : "None"}</option>
            {field.options.map((option) => (
              <option key={option} value={option}>
                {option.trim()}
              </option>
            ))}
          </select>
        </label>
      );
    case "checkbox":
      return (
        <label class="checkbox">
          <input
            type="checkbox"
            checked={value === "1"}
            onChange={(event) => onChange(event.currentTarget.checked ? "1" : "0")}
          />
          {caption}
        </label>
      );
    case "date":
      return (
        <label>
          {caption}
          <input
            type="date"
            required={required}
            value={value}
            onInput={(event) => onChange(event.currentTarget.value)}
          />
        </label>
      );
    case "number-integral":
    case "number-decimal":
      return (
        <label>
          {caption}
          <input
            type="number"
            step={field.type === "number-decimal" ? "any" : "1"}
            required={required}
            value={value}
            onInput={(event) => onChange(event.currentTarget.value)}
          />
        </label>
      );
    default:
      return (
        <label>
          {caption}
          <input
            maxLength={1000}
            required={required}
            value={value}
            onInput={(event) => onChange(event.currentTarget.value)}
          />
        </label>
      );
  }
}
