import MaterialAccessReportsMain from "@/components/layout/main/dashboards/academic/MaterialAccessReportsMain";
import DashboardContainer from "@/components/shared/containers/DashboardContainer";
import ThemeController from "@/components/shared/others/ThemeController";
import DsahboardWrapper from "@/components/shared/wrappers/DsahboardWrapper";

export const metadata = {
  title: "Material Access Reports | Admin Dashboard",
  description: "Material views, downloads, and engagement reports",
};

export default function MaterialReportsPage() {
  return (
    <main>
      <DsahboardWrapper>
        <DashboardContainer>
          <MaterialAccessReportsMain />
        </DashboardContainer>
      </DsahboardWrapper>
      <ThemeController />
    </main>
  );
}
