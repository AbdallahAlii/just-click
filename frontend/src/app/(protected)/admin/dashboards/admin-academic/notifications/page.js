import NotificationsAdminMain from "@/components/layout/main/dashboards/academic/NotificationsAdminMain";
import DashboardContainer from "@/components/shared/containers/DashboardContainer";
import ThemeController from "@/components/shared/others/ThemeController";
import DsahboardWrapper from "@/components/shared/wrappers/DsahboardWrapper";

export const metadata = {
  title: "Notifications | Admin Dashboard",
  description: "Send and manage student notifications",
};

export default function NotificationsAdminPage() {
  return (
    <main>
      <DsahboardWrapper>
        <DashboardContainer>
          <NotificationsAdminMain />
        </DashboardContainer>
      </DsahboardWrapper>
      <ThemeController />
    </main>
  );
}
