import MaterialListItem from "./MaterialListItem";

const CoursesList = ({ materials, onToggleFavorite, onShareMaterial }) => {
  if (!materials?.length) {
    return (
      <div className="rounded-xl border border-ds-border bg-ds-surface px-6 py-14 text-center text-sm text-ds-text-muted">
        No materials available.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-ds-border bg-ds-surface">
      <div className="hidden border-b border-ds-border px-4 py-2 sm:grid sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-3">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-ds-text-muted">
          Document
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-ds-text-muted sm:text-right">
          Activity & actions
        </span>
      </div>

      <ul className="divide-y divide-ds-border">
        {materials.map((material) => (
          <li key={material.id}>
            <MaterialListItem
              material={material}
              onToggleFavorite={onToggleFavorite}
              onShareMaterial={onShareMaterial}
            />
          </li>
        ))}
      </ul>
    </div>
  );
};

export default CoursesList;
