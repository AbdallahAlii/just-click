import MaterialCard from "./MaterialCard";

const CoursesGrid = ({
  materials,
  isNotSidebar,
  onToggleFavorite,
  onShareMaterial,
}) => {
  if (!materials?.length) {
    return (
      <p className="py-12 text-center text-sm text-ds-text-muted">
        No materials found.
      </p>
    );
  }

  return (
    <div
      className={`grid grid-cols-1 gap-3 sm:grid-cols-2 ${
        isNotSidebar ? "xl:grid-cols-3" : "lg:grid-cols-2 xl:grid-cols-3"
      }`}
    >
      {materials.map((material) => (
        <MaterialCard
          key={material.id}
          material={material}
          onToggleFavorite={onToggleFavorite}
          onShareMaterial={onShareMaterial}
        />
      ))}
    </div>
  );
};

export default CoursesGrid;
