import ErrorMain from "@/components/layout/main/ErrorMain";
import ThemeController from "@/components/shared/others/ThemeController";

const NotFound = () => {
  return (
    <>
      <main className="bg-ds-page">
        <ErrorMain />
      </main>
      <ThemeController />
    </>
  );
};

export default NotFound;
