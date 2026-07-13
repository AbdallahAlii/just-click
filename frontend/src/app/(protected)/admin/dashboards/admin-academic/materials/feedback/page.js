import MaterialFeedbackAdminMain from "@/components/layout/main/dashboards/academic/MaterialFeedbackAdminMain";
import DashboardContainer from "@/components/shared/containers/DashboardContainer";
import ThemeController from "@/components/shared/others/ThemeController";
import DsahboardWrapper from "@/components/shared/wrappers/DsahboardWrapper";

export const metadata = {
  title: "Material Feedback Inbox | Admin Dashboard",
  description: "Review and respond to student material feedback",
};

export default function MaterialFeedbackPage() {
  return (
    <main>
      <DsahboardWrapper>
        <DashboardContainer>
          <MaterialFeedbackAdminMain />
        </DashboardContainer>
      </DsahboardWrapper>
      <ThemeController />
    </main>
  );
}
