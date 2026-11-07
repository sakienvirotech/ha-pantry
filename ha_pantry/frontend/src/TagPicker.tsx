import { useState } from "preact/hooks";
import type { Tag, TagKind } from "./api";

interface Props {
  tags: Tag[];
  selected: number[];
  onChange: (tagIds: number[]) => void;
  onCreate: (name: string, kind: TagKind) => Promise<Tag | null>;
}

const GROUPS: { kind: TagKind; title: string; label: string }[] = [
  { kind: "category", title: "Categories", label: "New category" },
  { kind: "location", title: "Locations", label: "New location" },
];

function TagGroup({
  kind,
  title,
  label,
  tags,
  selected,
  onChange,
  onCreate,
}: Props & (typeof GROUPS)[number]) {
  const [newName, setNewName] = useState("");
  const select = (tagId: number) => {
    if (!selected.includes(tagId)) onChange([...selected, tagId]);
  };

  async function add() {
    const name = newName.trim();
    if (!name) return;
    const lowerName = name.toLowerCase();
    const existing = tags.find((tag) => tag.name.toLowerCase() === lowerName);
    const tag = existing ?? (await onCreate(name, kind));
    if (!tag) return;
    select(tag.id);
    setNewName("");
  }

  return (
    <fieldset>
      <legend>{title}</legend>
      <div class="chips">
        {tags.map((tag) => {
          const pressed = selected.includes(tag.id);
          return (
            <button
              type="button"
              key={tag.id}
              aria-pressed={pressed}
              onClick={() =>
                pressed
                  ? onChange(selected.filter((id) => id !== tag.id))
                  : select(tag.id)
              }
            >
              {tag.name}
            </button>
          );
        })}
      </div>
      <div class="new-tag">
        <input
          aria-label={label}
          placeholder={label}
          maxLength={100}
          value={newName}
          onInput={(event) => setNewName(event.currentTarget.value)}
        />
        <button type="button" disabled={!newName.trim()} onClick={add}>
          Add
        </button>
      </div>
    </fieldset>
  );
}

export function TagPicker(props: Props) {
  return (
    <>
      {GROUPS.map((group) => (
        <TagGroup
          {...props}
          {...group}
          key={group.kind}
          tags={props.tags.filter((tag) => tag.kind === group.kind)}
        />
      ))}
    </>
  );
}
