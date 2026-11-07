import { useState } from "preact/hooks";
import type { TagKind, TagSummary } from "./api";

interface Props {
  tags: TagSummary[];
  onRename: (id: number, name: string) => void;
  onDelete: (id: number) => void;
  onBack: () => void;
}

const GROUPS: { kind: TagKind; title: string }[] = [
  { kind: "category", title: "Categories" },
  { kind: "location", title: "Locations" },
];

function TagRow({
  tag,
  onRename,
  onDelete,
}: {
  tag: TagSummary;
  onRename: (name: string) => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(tag.name);
  const [confirming, setConfirming] = useState(false);
  const trimmed = name.trim();

  return (
    <div class="tag-row">
      <input
        aria-label={`Name of ${tag.name}`}
        maxLength={100}
        value={name}
        onInput={(event) => setName(event.currentTarget.value)}
      />
      <span>{tag.product_count}</span>
      <button
        type="button"
        disabled={!trimmed || trimmed === tag.name}
        onClick={() => onRename(trimmed)}
      >
        Rename
      </button>
      {confirming ? (
        <button type="button" class="danger" onClick={onDelete}>
          Really delete?
        </button>
      ) : (
        <button type="button" onClick={() => setConfirming(true)}>
          Delete
        </button>
      )}
    </div>
  );
}

export function TagManager({ tags, onRename, onDelete, onBack }: Props) {
  return (
    <article>
      <h2>Tags</h2>
      {tags.length === 0 && <p>No tags yet. Add them when editing a product.</p>}
      {GROUPS.map(({ kind, title }) => {
        const group = tags.filter((tag) => tag.kind === kind);
        if (group.length === 0) return null;
        return (
          <section key={kind}>
            <h3>{title}</h3>
            {group.map((tag) => (
              <TagRow
                key={tag.id}
                tag={tag}
                onRename={(name) => onRename(tag.id, name)}
                onDelete={() => onDelete(tag.id)}
              />
            ))}
          </section>
        );
      })}
      <div class="actions">
        <button type="button" onClick={onBack}>
          Back
        </button>
      </div>
    </article>
  );
}
